from dataclasses import dataclass
import logging
from pathlib import Path
import re
import struct
from typing import Dict, List, Set, Tuple

from src.constants import GENERATED_COMMENT, IndexRecordType
from src.rdb_extractor import BinaryReader
from src.rdb_file import MultiChunkReader
from src.rdb_index import IndexRecord

log = logging.getLogger(__name__)

ZONE_SIZE = 40
TILE_SIZE = 4
RECORD_HEADER_SIZE = 22
OBJECT_HEADER_SIZE = 12

TOWER_SITE_ROW = re.compile(
    r"^INSERT INTO tower_site \(playfield_id, site_number, min_ql, max_ql, x_coord, y_coord, close_time, site_name, enabled\) "
    r"VALUES \((\d+),(\d+),(\d+),(\d+),(\d+),(\d+),(?:\d+|NULL),'((?:[^']|'')*)',\d+\);$")

SiteKey = Tuple[int, int, int]


@dataclass
class TowerSite:
    playfield_id: int
    site_number: int
    min_ql: int
    max_ql: int
    x_coord: int
    y_coord: int
    site_name: str


@dataclass
class District:
    name: str
    x_coord: float
    y_coord: float
    min_ql: int
    max_ql: int
    min_npc_level: int
    max_npc_level: int


@dataclass
class DistrictInfo:
    districts: List[District]
    zone_to_district: bytes


@dataclass
class TowerSiteBounds:
    playfield_id: int
    site_number: int
    x_coord1: int
    y_coord1: int
    x_coord2: int
    y_coord2: int


def read_resource(reader: MultiChunkReader, record: IndexRecord) -> bytes:
    # Record header: magic, then type, instance and payload size at offset 10
    hdr = reader.read_item_bytes(record.offset, RECORD_HEADER_SIZE)
    if len(hdr) != RECORD_HEADER_SIZE or hdr[:2] != b"\xfa\xfa":
        raise ValueError(f"Invalid record header for resource {record.resource_type}:{record.resource_id}")
    res_type, res_id, size = struct.unpack_from("<iii", hdr, 10)
    if (res_type, res_id) != (record.resource_type, record.resource_id):
        raise ValueError(f"Index points resource {record.resource_type}:{record.resource_id} at record {res_type}:{res_id}")
    data = reader.read_item_bytes(record.offset + RECORD_HEADER_SIZE, size)
    if len(data) != size:
        raise EOFError(f"Resource {res_type}:{res_id} is truncated: {len(data)} of {size} bytes")
    return data


def read_3f1_count(r: BinaryReader) -> int:
    n = r.read_i32()
    if n < 1009 or n % 1009:
        raise ValueError(f"Invalid 3F1 count {n}")
    return n // 1009 - 1


def read_string(r: BinaryReader) -> str:
    n = r.read_u16()
    if n >= 0x8000:
        raise ValueError(f"Invalid string length {n:#x}")
    return r.read_bytes(n).decode("latin1")


def read_playfield_name(data: bytes, playfield_id: int) -> str:
    r = BinaryReader(data)
    r.read_bytes(OBJECT_HEADER_SIZE)
    r.read_i32()
    if r.read_i32() != playfield_id:
        raise ValueError(f"Playfield record {playfield_id} contains another playfield id")
    return r.read_bytes(32).split(b"\0")[0].decode("latin1").strip()


def read_zone_grid_width(data: bytes, playfield_id: int) -> int:
    r = BinaryReader(data)
    r.read_bytes(OBJECT_HEADER_SIZE)
    version = r.read_u16()
    if version != 1:
        raise ValueError(f"Unsupported land control map version {version} for playfield {playfield_id}")
    r.read_u16()
    width = r.read_u16() * TILE_SIZE
    if width % ZONE_SIZE:
        raise ValueError(f"Playfield {playfield_id} width {width} is not a whole number of zones")
    return width // ZONE_SIZE


def skip_hash_spawn_point(r: BinaryReader, version: int):
    # Spawn position, radius, facing, monster hash and level range
    r.read_bytes(28)
    r.read_u8()
    flags = r.read_u8()
    r.read_u16()
    if version > 6:
        r.read_i32()
    if flags & 1:
        r.read_bytes(4)
    if flags & 2:
        r.read_bytes(20 * r.read_u8())
    if flags & 4:
        for _ in range(r.read_u32()):
            list_type, list_id = r.read_i32(), r.read_i32()
            if (list_type, list_id) != (0x20, 0x37):
                raise ValueError(f"Unsupported spawn list type {list_type} id {list_id}")
            count = read_3f1_count(r)
            if r.read_i32() != 1:
                raise ValueError("Unsupported spawn list version")
            for _ in range(count):
                if r.read_i32() != 1:
                    raise ValueError("Unsupported spawn list entry version")
                read_string(r)
                r.read_i32()


def read_district(r: BinaryReader, version: int) -> District:
    x_coord, _, y_coord = r.read_f32(), r.read_f32(), r.read_f32()
    name = r.read_bytes(32).split(b"\0")[0].decode("latin1") if version < 6 else read_string(r)
    r.read_bytes(18)
    if version < 6:
        # Unused bytes, then a one-byte NPC level range; no land control levels
        r.read_bytes(4)
        min_npc_level, max_npc_level = r.read_u8(), r.read_u8()
        min_ql = max_ql = 0
    else:
        # NPC level range, then land control level range
        min_npc_level, max_npc_level = r.read_u16(), r.read_u16()
        min_ql, max_ql = r.read_u16(), r.read_u16()
    # Respawn chance, respawn time and fight mode
    r.read_bytes(6)
    spawn_info_count = r.read_u8()
    old_spawn_info_count = r.read_u8() if version < 6 else 0
    wildlife_count, spawn_point_count, hash_spawn_point_count = r.read_u8(), r.read_u8(), r.read_u8()
    r.read_bytes(6 * (spawn_info_count + old_spawn_info_count) + 4 * wildlife_count + 16 * spawn_point_count)
    for _ in range(hash_spawn_point_count):
        skip_hash_spawn_point(r, version)
    return District(name.strip(), x_coord, y_coord, min_ql, max_ql, min_npc_level, max_npc_level)


def read_district_info(data: bytes, playfield_id: int) -> DistrictInfo:
    r = BinaryReader(data)
    r.read_bytes(OBJECT_HEADER_SIZE)
    version = r.read_u16()
    if version not in (5, 6, 7):
        raise ValueError(f"Unsupported district info version {version} for playfield {playfield_id}")
    zone_count = r.read_u32()
    districts = [read_district(r, version) for _ in range(r.read_u8())]
    zone_to_district = r.read_bytes(zone_count)
    if r.remaining():
        raise ValueError(f"District info for playfield {playfield_id} has {r.remaining()} unread bytes")
    if zone_to_district and max(zone_to_district) >= len(districts):
        raise ValueError(f"District info for playfield {playfield_id} maps a zone to a missing district")
    return DistrictInfo(districts, zone_to_district)


def read_tower_sites(path: Path) -> Dict[SiteKey, TowerSite]:
    sites: Dict[SiteKey, TowerSite] = {}
    with open(path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line.startswith("INSERT"):
                continue
            m = TOWER_SITE_ROW.match(line)
            if not m:
                raise ValueError(f"Unrecognized tower_site row on line {line_num} of {path}")
            site = TowerSite(int(m[1]), int(m[2]), int(m[3]), int(m[4]), int(m[5]), int(m[6]), m[7].replace("''", "'"))
            key = (site.playfield_id, site.x_coord, site.y_coord)
            if key in sites:
                raise ValueError(f"Tower sites {sites[key].site_number} and {site.site_number} in playfield {site.playfield_id} share centre {site.x_coord}x{site.y_coord}")
            sites[key] = site
    return sites


def match_sites(playfield_id: int, info: DistrictInfo, sites: Dict[SiteKey, TowerSite], matched: Set[SiteKey]) -> Dict[int, int]:
    # Maps district index to site number; land control districts missing from tower_site.sql are skipped
    site_numbers: Dict[int, int] = {}
    for index, district in enumerate(info.districts):
        if not district.max_ql:
            continue
        key = (playfield_id, round(district.x_coord), round(district.y_coord))
        site = sites.get(key)
        if not site:
            log.warning(f"Skipping land control district '{district.name}' at {key[1]}x{key[2]} in playfield {playfield_id}: not in tower_site.sql")
            continue
        if site.site_name != district.name or (site.min_ql, site.max_ql) != (district.min_ql, district.max_ql):
            raise ValueError(f"Tower site {playfield_id}:{site.site_number} '{site.site_name}' QL {site.min_ql}-{site.max_ql} does not match "
                             f"district '{district.name}' QL {district.min_ql}-{district.max_ql} at the same centre")
        site_numbers[index] = site.site_number
        matched.add(key)
    return site_numbers


def build_bounds(playfield_id: int, width: int, zone_to_district: bytes, site_numbers: Dict[int, int]) -> List[TowerSiteBounds]:
    # Runs of zones in each row, merged with identical runs in the rows above
    if len(zone_to_district) % width:
        raise ValueError(f"Playfield {playfield_id} has {len(zone_to_district)} zones, not a multiple of its width {width}")
    height = len(zone_to_district) // width
    bounds: List[TowerSiteBounds] = []
    open_runs: Dict[Tuple[int, int, int], int] = {}
    for row in range(height + 1):
        runs = set()
        column = 0
        while row < height and column < width:
            start = column
            site_number = site_numbers.get(zone_to_district[row * width + column])
            while column < width and site_numbers.get(zone_to_district[row * width + column]) == site_number:
                column += 1
            if site_number is not None:
                runs.add((start, column, site_number))
        for start, end, site_number in set(open_runs) - runs:
            first_row = open_runs[(start, end, site_number)]
            bounds.append(TowerSiteBounds(playfield_id, site_number, start * ZONE_SIZE, row * ZONE_SIZE - 1, end * ZONE_SIZE - 1, first_row * ZONE_SIZE))
        open_runs = {run: open_runs.get(run, row) for run in runs}
    return bounds


def write_tower_site_bounds(reader: MultiChunkReader, records: List[IndexRecord], tower_dir: Path):
    sites = read_tower_sites(tower_dir / "tower_site.sql")
    log.info(f"Loaded {len(sites)} tower sites from {tower_dir / 'tower_site.sql'}")
    by_key = {(r.resource_type, r.resource_id): r for r in records}

    # Only playfields with a land control map can hold towers
    playfield_ids = sorted(r.resource_id for r in records if r.resource_type == IndexRecordType.LAND_CONTROL_MAP_TYPE)
    matched: Set[SiteKey] = set()
    bounds: List[TowerSiteBounds] = []
    names: Dict[int, str] = {}
    for playfield_id in playfield_ids:
        for res_type in (IndexRecordType.DISTRICT_INFO_TYPE, IndexRecordType.PLAYFIELD_TYPE):
            if (res_type, playfield_id) not in by_key:
                raise ValueError(f"Playfield {playfield_id} has a land control map but no resource {res_type}")
        info = read_district_info(read_resource(reader, by_key[(IndexRecordType.DISTRICT_INFO_TYPE, playfield_id)]), playfield_id)
        site_numbers = match_sites(playfield_id, info, sites, matched)
        if not site_numbers:
            continue
        width = read_zone_grid_width(read_resource(reader, by_key[(IndexRecordType.LAND_CONTROL_MAP_TYPE, playfield_id)]), playfield_id)
        names[playfield_id] = read_playfield_name(read_resource(reader, by_key[(IndexRecordType.PLAYFIELD_TYPE, playfield_id)]), playfield_id)
        bounds += build_bounds(playfield_id, width, info.zone_to_district, site_numbers)

    missing = sorted(set(sites) - matched)
    if missing:
        raise ValueError("Tower sites with no matching land control district: " +
                         ", ".join(f"{sites[k].playfield_id}:{sites[k].site_number} '{sites[k].site_name}'" for k in missing))

    out_path = tower_dir / "tower_site_bounds.sql"
    with open(out_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(GENERATED_COMMENT)
        f.write("DROP TABLE IF EXISTS tower_site_bounds;\n")
        f.write("CREATE TABLE tower_site_bounds (playfield_id INT NOT NULL, site_number SMALLINT NOT NULL, x_coord1 SMALLINT NOT NULL, "
                "y_coord1 SMALLINT NOT NULL, x_coord2 SMALLINT NOT NULL, y_coord2 SMALLINT NOT NULL);\n")
        for playfield_id in sorted(names):
            f.write(f"\n-- {names[playfield_id]}\n")
            rows = sorted((b for b in bounds if b.playfield_id == playfield_id), key=lambda b: (b.site_number, -b.y_coord1, b.x_coord1))
            for b in rows:
                f.write("INSERT INTO tower_site_bounds (playfield_id, site_number, x_coord1, y_coord1, x_coord2, y_coord2) "
                        f"VALUES ({b.playfield_id}, {b.site_number}, {b.x_coord1}, {b.y_coord1}, {b.x_coord2}, {b.y_coord2});\n")
    log.info(f"Wrote {len(bounds)} tower site bounds for {len(matched)} sites in {len(names)} playfields to {out_path}")
