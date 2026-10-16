import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple

from src.constants import GENERATED_COMMENT
from src.perks import MONSTER_PROFESSION, PROFESSION_NAME_CATEGORY, read_perk_chains, read_perk_level
from src.rdb_extractor import RDBItem
from src.rdb_file import MultiChunkReader
from src.rdb_index import IndexRecord
from src.skills import read_text_category

log = logging.getLogger(__name__)

RESEARCH_CATEGORY = 64
XP_PER_SK = 1000


def write_research_sql(reader: MultiChunkReader, records: List[IndexRecord], items: List[RDBItem], text_mdb: Path, helpbot_dir: Path):
    all_professions = set(read_text_category(text_mdb, PROFESSION_NAME_CATEGORY)) - {MONSTER_PROFESSION}
    items_map = {item.id: item for item in items}

    # Cost and character level requirement of each research level, which every profession research line must share
    levels: Dict[int, Set[Tuple[int, int]]] = {}
    line_count = 0
    for chain in read_perk_chains(reader, records, RESEARCH_CATEGORY):
        missing = [p.item_id for p in chain if p.item_id not in items_map]
        if missing:
            raise ValueError(f"Research {chain[0].perk_id} uses items {missing}, which were not read")
        name = items_map[chain[0].item_id].name.strip()
        if not chain[0].profession_mask:
            log.info(f"Skipping research line '{name}': not a profession research line")
            continue
        line_count += 1
        for number, p in enumerate(chain, 1):
            min_level = read_perk_level(p, items_map[p.item_id], number, all_professions).min_level
            levels.setdefault(number, set()).add((p.cost, min_level))

    if sorted(levels) != list(range(1, len(levels) + 1)):
        raise ValueError(f"Research levels {sorted(levels)} are not consecutive from 1")
    rows: List[Tuple[int, int, int]] = [(0, 0, 0)]
    for number in sorted(levels):
        if len(levels[number]) != 1:
            raise ValueError(f"Research lines differ at level {number}: (cost, level) {sorted(levels[number])}")
        cost, min_level = next(iter(levels[number]))
        if cost % XP_PER_SK:
            raise ValueError(f"Research level {number} costs {cost} XP, not a whole number of SK")
        rows.append((number, cost // XP_PER_SK, min_level))

    path = helpbot_dir / "research.sql"
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(GENERATED_COMMENT)
        f.write("DROP TABLE IF EXISTS research;\n")
        f.write("CREATE TABLE research (level SMALLINT NOT NULL, sk INT NOT NULL, levelcap SMALLINT NOT NULL);\n")
        for number, sk, min_level in rows:
            f.write(f"INSERT INTO research VALUES ({number},{sk},{min_level});\n")
    log.info(f"Wrote {len(rows)} research levels from {line_count} research lines to {path}")
