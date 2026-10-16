from dataclasses import dataclass
import logging
from pathlib import Path
import struct
from typing import Dict, List, Set, Tuple

from src.constants import GENERATED_COMMENT, IndexRecordType
from src.rdb_extractor import RDBItem
from src.rdb_file import MultiChunkReader
from src.rdb_index import IndexRecord
from src.skills import SKILL_NAME_CATEGORY, read_text_category, sql_string
from src.tower_sites import read_resource

log = logging.getLogger(__name__)

PROFESSION_NAME_CATEGORY = 2004
MONSTER_PROFESSION = 13
SL_PERK_CATEGORY = 0
PERK_RECORD_SIZE = 36
LEVEL_STAT = 54
PROFESSION_STAT = 60
OP_EQUAL = 0
OP_GREATER_THAN = 2
OP_OR = 3
OP_AND = 4
OP_HAS_PERK = 93
WEAR_EVENT = 14
MODIFY_FUNCTION = 53045


@dataclass
class PerkRecord:
    perk_id: int
    item_id: int
    previous_id: int
    category: int


@dataclass
class PerkLevel:
    level_id: int
    number: int
    min_level: int
    professions: Set[int]
    buffs: List[Tuple[int, int]]


@dataclass
class Perk:
    perk_id: int
    name: str
    levels: List[PerkLevel]


def read_perk_record(data: bytes, perk_id: int) -> PerkRecord:
    # Header (type, instance, revision), then item id, previous level's perk id and category
    if len(data) != PERK_RECORD_SIZE:
        raise ValueError(f"Perk record {perk_id} has {len(data)} bytes, expected {PERK_RECORD_SIZE}")
    item_id, previous_id, category = struct.unpack_from("<iii", data, 12)
    return PerkRecord(perk_id, item_id, previous_id, category)


def read_perk_chains(reader: MultiChunkReader, records: List[IndexRecord]) -> List[List[PerkRecord]]:
    # SL perks, each as its levels in order, linked by the previous level's perk id
    perks = [read_perk_record(read_resource(reader, r), r.resource_id)
             for r in records if r.resource_type == IndexRecordType.PERK_TYPE]
    sl_perks = {p.perk_id: p for p in perks if p.category == SL_PERK_CATEGORY}
    if not sl_perks:
        raise ValueError("No SL perk records found")

    next_level: Dict[int, PerkRecord] = {}
    for p in sl_perks.values():
        if not p.previous_id:
            continue
        if p.previous_id not in sl_perks:
            raise ValueError(f"Perk {p.perk_id} follows perk {p.previous_id}, which is not an SL perk")
        if p.previous_id in next_level:
            raise ValueError(f"Perks {next_level[p.previous_id].perk_id} and {p.perk_id} both follow perk {p.previous_id}")
        next_level[p.previous_id] = p

    chains: List[List[PerkRecord]] = []
    for p in sl_perks.values():
        if p.previous_id:
            continue
        chain = [p]
        while chain[-1].perk_id in next_level:
            chain.append(next_level[chain[-1].perk_id])
        chains.append(chain)

    if sum(len(c) for c in chains) != len(sl_perks):
        raise ValueError("Some SL perk levels are not linked to a first level")
    return chains


def read_perk_level(record: PerkRecord, item: RDBItem, number: int, all_professions: Set[int]) -> PerkLevel:
    # Requirements: profession checks joined by OR, a level check and the previous level, all joined by AND
    professions: Set[int] = set()
    levels: List[int] = []
    previous: List[int] = []
    for c in item.criteria_list:
        if c.criteria1 == PROFESSION_STAT and c.criteria3 == OP_EQUAL:
            if c.criteria2 not in all_professions:
                raise ValueError(f"Perk {record.perk_id} item {item.id} requires unknown profession {c.criteria2}")
            professions.add(c.criteria2)
        elif c.criteria1 == LEVEL_STAT and c.criteria3 == OP_GREATER_THAN:
            levels.append(c.criteria2 + 1)
        elif c.criteria1 == 0 and c.criteria3 == OP_HAS_PERK:
            previous.append(c.criteria2)
        elif (c.criteria1, c.criteria2) != (0, 0) or c.criteria3 not in (OP_OR, OP_AND):
            raise ValueError(f"Perk {record.perk_id} item {item.id} has unexpected requirement {(c.criteria1, c.criteria2, c.criteria3)}")

    if len(levels) != 1:
        raise ValueError(f"Perk {record.perk_id} item {item.id} has {len(levels)} level requirements")
    expected_previous = [record.previous_id] if record.previous_id else []
    if previous != expected_previous:
        raise ValueError(f"Perk {record.perk_id} item {item.id} requires perks {previous}, expected {expected_previous}")

    # Stat buffs while worn; zero amounts change nothing
    buffs = [(int(f.params[0]), int(f.params[1]))
             for event in item.events if event.event_type == WEAR_EVENT
             for f in event.functions if f.function_num == MODIFY_FUNCTION and int(f.params[1]) != 0]

    return PerkLevel(record.perk_id, number, levels[0], professions or set(all_professions), buffs)


def read_perks(reader: MultiChunkReader, records: List[IndexRecord], items: List[RDBItem], all_professions: Set[int]) -> List[Perk]:
    items_map = {item.id: item for item in items}
    perks: List[Perk] = []
    for chain in read_perk_chains(reader, records):
        missing = [p.item_id for p in chain if p.item_id not in items_map]
        if missing:
            raise ValueError(f"Perk {chain[0].perk_id} uses items {missing}, which were not read")
        name = items_map[chain[0].item_id].name.strip()
        for p in chain:
            if items_map[p.item_id].name.strip() != name:
                raise ValueError(f"Perk {p.perk_id} item {p.item_id} is named '{items_map[p.item_id].name.strip()}', expected '{name}'")

        levels = [read_perk_level(p, items_map[p.item_id], number, all_professions) for number, p in enumerate(chain, 1)]
        if len({frozenset(level.professions) for level in levels}) > 1:
            log.warning(f"Perk '{name}' allows different professions per level; perk_prof lists the professions of every level")
        perks.append(Perk(chain[0].perk_id, name, levels))

    perks.sort(key=lambda p: (p.name, p.perk_id))
    return perks


def write_perks_sql(reader: MultiChunkReader, records: List[IndexRecord], items: List[RDBItem], text_mdb: Path, perks_dir: Path):
    skill_names = read_text_category(text_mdb, SKILL_NAME_CATEGORY)
    profession_names = read_text_category(text_mdb, PROFESSION_NAME_CATEGORY)
    perks = read_perks(reader, records, items, set(profession_names) - {MONSTER_PROFESSION})

    unnamed = sorted({stat for p in perks for level in p.levels for stat, _ in level.buffs} - skill_names.keys())
    if unnamed:
        raise ValueError(f"Perks buff stats {unnamed}, which have no skill name in category {SKILL_NAME_CATEGORY}")

    path = perks_dir / "perks.sql"
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(GENERATED_COMMENT)
        f.write("DROP TABLE IF EXISTS perk;\n")
        f.write("CREATE TABLE perk (id INT NOT NULL PRIMARY KEY, name VARCHAR(25) NOT NULL);\n")
        f.write("DROP TABLE IF EXISTS perk_level;\n")
        f.write("CREATE TABLE perk_level (id INT NOT NULL PRIMARY KEY, perk_id INT NOT NULL, number INT NOT NULL, min_level INT NOT NULL);\n")
        f.write("DROP TABLE IF EXISTS perk_prof;\n")
        f.write("CREATE TABLE perk_prof (perk_id INT NOT NULL, profession VARCHAR(25) NOT NULL);\n")
        f.write("DROP TABLE IF EXISTS perk_level_buffs;\n")
        f.write("CREATE TABLE perk_level_buffs (perk_level_id INT NOT NULL, skill VARCHAR(50) NOT NULL, amount INT NOT NULL);\n")

        for p in perks:
            f.write(f"INSERT INTO perk (id, name) VALUES ({p.perk_id}, {sql_string(p.name)});\n")
        for p in perks:
            for level in p.levels:
                f.write(f"INSERT INTO perk_level (id, perk_id, number, min_level) VALUES ({level.level_id}, {p.perk_id}, {level.number}, {level.min_level});\n")
        for p in perks:
            professions = set().union(*(level.professions for level in p.levels))
            for name in sorted(profession_names[prof] for prof in professions):
                f.write(f"INSERT INTO perk_prof (perk_id, profession) VALUES ({p.perk_id}, {sql_string(name)});\n")
        for p in perks:
            for level in p.levels:
                for stat, amount in level.buffs:
                    f.write(f"INSERT INTO perk_level_buffs (perk_level_id, skill, amount) VALUES ({level.level_id}, {sql_string(skill_names[stat])}, {amount});\n")

    log.info(f"Wrote {len(perks)} perks with {sum(len(p.levels) for p in perks)} levels to {path}")
