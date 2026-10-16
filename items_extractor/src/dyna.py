import configparser
from dataclasses import dataclass
import logging
from pathlib import Path
import re
from typing import Dict, List, Tuple

from src.constants import GENERATED_COMMENT, IndexRecordType
from src.rdb_file import MultiChunkReader
from src.rdb_index import IndexRecord
from src.skills import sql_string
from src.tower_sites import District, read_district_info, read_resource

log = logging.getLogger(__name__)

DYNA_MARKER = b"dyna"
NUMBERED_CAMP = re.compile(r"^Dynacamp\s*(\d*)\b(.*)$")
NAMED_CAMP = re.compile(r"^(.*\S)\s+Dynacamp$")
LEVEL_RANGE = re.compile(r"\d+\s*-\s*\d+")
UNKNOWN_MOB = "Unknown"


@dataclass
class DynaCamp:
    playfield_id: int
    label: str
    mob: str
    min_level: int
    max_level: int
    x_coord: int
    y_coord: int


class CaseSensitiveConfigParser(configparser.ConfigParser):
    # Keeps the case of option names
    def optionxform(self, optionstr: str) -> str:
        return optionstr


def read_mob_aliases(path: Path) -> Dict[str, str]:
    parser = CaseSensitiveConfigParser(inline_comment_prefixes=(";",), allow_no_value=True)
    with open(path, encoding="utf-8") as f:
        parser.read_file(f)
    return dict(parser.items("dyna_mob_names"))


def whole_coord(value: float, what: str, district: District) -> int:
    if value != int(value):
        raise ValueError(f"Dynacamp district '{district.name}' has a fractional {what} coordinate {value}")
    return int(value)


def read_camp(playfield_id: int, district: District) -> DynaCamp:
    # Label and mob from names like "Dynacamp4 70-75 Hammerbeasts", "Dynacamp 14 - Reets" or "Chriop Dynacamp"
    numbered = NUMBERED_CAMP.match(district.name)
    named = NAMED_CAMP.match(district.name)
    if numbered:
        label, rest = "Dynacamp" + numbered.group(1), numbered.group(2)
    elif named:
        label, rest = "Dynacamp", named.group(1)
    else:
        label, rest = district.name, ""
    mob = " ".join(LEVEL_RANGE.sub(" ", rest).replace(" - ", " ").split()).strip(" -") or UNKNOWN_MOB

    return DynaCamp(playfield_id, label, mob, district.min_npc_level, district.max_npc_level,
                    whole_coord(district.x_coord, "x", district), whole_coord(district.y_coord, "y", district))


def camp_order(camp: DynaCamp) -> Tuple[int, int, str]:
    number = camp.label[len("Dynacamp"):]
    return camp.playfield_id, int(number) if number.isdigit() else 0, camp.label


def write_dyna_sql(reader: MultiChunkReader, records: List[IndexRecord], config_path: Path, helpbot_dir: Path):
    aliases = read_mob_aliases(config_path)

    # Districts named after dynacamps; only playfields whose district data mentions one are read
    camps: List[DynaCamp] = []
    for record in records:
        if record.resource_type != IndexRecordType.DISTRICT_INFO_TYPE:
            continue
        data = read_resource(reader, record)
        if DYNA_MARKER not in data.lower():
            continue
        info = read_district_info(data, record.resource_id)
        camps += [read_camp(record.resource_id, d) for d in info.districts if "dyna" in d.name.lower()]

    if not camps:
        raise ValueError("No dynacamp districts found")
    unused = sorted(set(aliases) - {c.mob for c in camps})
    if unused:
        raise ValueError(f"{config_path} renames dynacamp mobs that no district has: {unused}")
    for c in camps:
        c.mob = aliases.get(c.mob, c.mob)
    camps.sort(key=camp_order)

    path = helpbot_dir / "dyna.sql"
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(GENERATED_COMMENT)
        f.write("DROP TABLE IF EXISTS dynadb;\n")
        f.write("CREATE TABLE dynadb (playfield_id SMALLINT NOT NULL, label VARCHAR(200), mob VARCHAR(200), minQl SMALLINT NOT NULL, "
                "maxQl SMALLINT NOT NULL, cX SMALLINT NOT NULL, cY SMALLINT NOT NULL);\n")
        for c in camps:
            f.write(f"INSERT INTO dynadb VALUES ({c.playfield_id},{sql_string(c.label)},{sql_string(c.mob)},"
                    f"{c.min_level},{c.max_level},{c.x_coord},{c.y_coord});\n")
    log.info(f"Wrote {len(camps)} dynacamps to {path}")
