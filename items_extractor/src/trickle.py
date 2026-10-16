from dataclasses import dataclass
import logging
from pathlib import Path
import struct
from typing import Dict, List, Tuple

from src.constants import GENERATED_COMMENT, IndexRecordType
from src.dyna import CaseSensitiveConfigParser
from src.rdb_file import MultiChunkReader
from src.rdb_index import IndexRecord
from src.skills import SKILL_NAME_CATEGORY, read_text_category, sql_string
from src.tower_sites import read_resource

log = logging.getLogger(__name__)

SKILL_GROUP_CATEGORY = 10010
TRICKLE_RECORD_SIZE = 36
PERCENT_STEP = 10
# Ability order in a trickle record, and the trickle table's column order
RECORD_ABILITIES = ["strength", "agility", "stamina", "intelligence", "sense", "psychic"]
COLUMN_ABILITIES = ["agility", "intelligence", "psychic", "stamina", "strength", "sense"]


@dataclass
class TrickleSkill:
    group_name: str
    name: str
    percents: Dict[str, int]


def read_trickle_record(data: bytes, stat: int) -> Dict[str, int]:
    # Header (type, instance, revision), then the percentage each ability adds to the skill
    if len(data) != TRICKLE_RECORD_SIZE:
        raise ValueError(f"Trickle record {stat} has {len(data)} bytes, expected {TRICKLE_RECORD_SIZE}")
    return dict(zip(RECORD_ABILITIES, struct.unpack_from("<6i", data, 12)))


def read_trickle_groups(path: Path, group_names: Dict[int, str]) -> List[Tuple[str, List[int]]]:
    # Keys are game group ids, or group names for groups the game doesn't have
    parser = CaseSensitiveConfigParser(inline_comment_prefixes=(";",), allow_no_value=True)
    with open(path, encoding="utf-8") as f:
        parser.read_file(f)
    groups: List[Tuple[str, List[int]]] = []
    for key, value in parser.items("trickle_groups"):
        if key.isdigit():
            if int(key) not in group_names:
                raise ValueError(f"{path} trickle group {key} is not in text.mdb category {SKILL_GROUP_CATEGORY}")
            name = group_names[int(key)]
        else:
            name = key
        groups.append((name, [int(v) for v in (value or "").split(",")]))
    if not groups:
        raise ValueError(f"{path} lists no trickle groups")
    return groups


def format_amount(percent: int) -> str:
    value = percent / 100
    return str(int(value)) if value == int(value) else f"{value:.1f}".lstrip("0")


def write_trickle_sql(reader: MultiChunkReader, records: List[IndexRecord], text_mdb: Path, config_path: Path, trickle_dir: Path):
    skill_names = read_text_category(text_mdb, SKILL_NAME_CATEGORY)
    groups = read_trickle_groups(config_path, read_text_category(text_mdb, SKILL_GROUP_CATEGORY))
    trickles = {r.resource_id: read_trickle_record(read_resource(reader, r), r.resource_id)
                for r in records if r.resource_type == IndexRecordType.TRICKLE_TYPE}
    if not trickles:
        raise ValueError("No trickle records found")

    skills: List[TrickleSkill] = []
    listed: Dict[int, str] = {}
    for group_name, stats in groups:
        for stat in stats:
            if stat in listed:
                raise ValueError(f"{config_path} lists stat {stat} in both '{listed[stat]}' and '{group_name}'")
            listed[stat] = group_name
            if stat not in trickles:
                raise ValueError(f"{config_path} lists stat {stat}, which has no trickle record")
            if stat not in skill_names:
                raise ValueError(f"{config_path} lists stat {stat}, which has no skill name in category {SKILL_NAME_CATEGORY}")
            uneven = {a: p for a, p in trickles[stat].items() if p % PERCENT_STEP}
            if uneven:
                raise ValueError(f"Trickle record {stat} has percentages {uneven}, which the table's one decimal place cannot hold")
            skills.append(TrickleSkill(group_name, skill_names[stat], trickles[stat]))

    for stat in sorted(set(trickles) - set(listed)):
        log.info(f"Skipping trickle record {stat} ({skill_names.get(stat)}): not in any group in {config_path}")

    path = trickle_dir / "trickle.sql"
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(GENERATED_COMMENT)
        f.write("DROP TABLE IF EXISTS trickle;\n")
        f.write("CREATE TABLE trickle ( id INT NOT NULL PRIMARY KEY, group_name VARCHAR(20) NOT NULL, name VARCHAR(30) NOT NULL, "
                + ", ".join(f"amount_{a} DECIMAL(3,1) NOT NULL" for a in COLUMN_ABILITIES) + " );\n")
        current_group = ""
        for row_id, s in enumerate(skills, 1):
            if s.group_name != current_group:
                f.write("\n")
                current_group = s.group_name
            f.write(f"INSERT INTO trickle (id, group_name, name, {', '.join('amount_' + a for a in COLUMN_ABILITIES)}) VALUES ({row_id}, "
                    f"{sql_string(s.group_name)}, {sql_string(s.name)}, {', '.join(format_amount(s.percents[a]) for a in COLUMN_ABILITIES)});\n")
    log.info(f"Wrote {len(skills)} trickle skills in {len(groups)} groups to {path}")
