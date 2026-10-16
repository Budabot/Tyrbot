import configparser
import logging
from pathlib import Path
import struct
from typing import Dict, Set

from src.constants import GENERATED_COMMENT

log = logging.getLogger(__name__)

MMDB_MAGIC = b"MMDB"
SKILL_NAME_CATEGORY = 2003


def read_text_category(text_mdb: Path, category_id: int) -> Dict[int, str]:
    data = text_mdb.read_bytes()
    if data[:4] != MMDB_MAGIC:
        raise ValueError(f"{text_mdb} is not an MMDB file")

    # Category table: (category id, offset of its entry list); the next category's offset ends the list
    count = struct.unpack_from("<I", data, 4)[0]
    categories = [struct.unpack_from("<II", data, 8 + 8 * i) for i in range(count)]
    for index, (cid, start) in enumerate(categories):
        if cid == category_id:
            break
    else:
        raise ValueError(f"Category {category_id} not found in {text_mdb}")
    if index + 1 >= count:
        raise ValueError(f"Category {category_id} in {text_mdb} has no end offset")
    end = categories[index + 1][1]

    # Entries: (entry id, offset of a NUL-terminated string)
    entries: Dict[int, str] = {}
    for pos in range(start, end, 8):
        entry_id, text_offset = struct.unpack_from("<II", data, pos)
        text_end = data.index(b"\0", text_offset)
        entries[entry_id] = data[text_offset:text_end].decode("latin1")
    return entries


def read_common_names(path: Path) -> Dict[int, str]:
    parser = configparser.ConfigParser(inline_comment_prefixes=(";",), allow_no_value=True)
    with open(path, encoding="utf-8") as f:
        parser.read_file(f)
    return {int(key): value for key, value in parser.items("skill_common_names")}


def sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def write_skills_sql(buffed_stats: Set[int], text_mdb: Path, common_names_path: Path, file_path: str):
    names = read_text_category(text_mdb, SKILL_NAME_CATEGORY)
    common_names = read_common_names(common_names_path)

    # Buffed stats without a game skill name are left out
    for stat in sorted(buffed_stats - names.keys()):
        log.info(f"Skipping buffed stat {stat}: no skill name in category {SKILL_NAME_CATEGORY}")
    skill_ids = buffed_stats & names.keys()

    unused = sorted(common_names.keys() - skill_ids)
    if unused:
        raise ValueError(f"{common_names_path} names stats that are not in skills.sql: {unused}")

    log.debug(f"Writing skills to file: '{file_path}'")
    with open(file_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(GENERATED_COMMENT)
        f.write("DROP TABLE IF EXISTS skills;\n")
        f.write("CREATE TABLE skills (id INT NOT NULL PRIMARY KEY, name VARCHAR(50) NOT NULL, common_name VARCHAR(50) NOT NULL);\n")
        for stat in sorted(skill_ids, key=lambda s: (names[s].lower(), s)):
            f.write(f"INSERT INTO skills (id, name, common_name) VALUES ({stat}, {sql_string(names[stat])}, {sql_string(common_names.get(stat, ''))});\n")
    log.info(f"Wrote {len(skill_ids)} skills to {file_path}")
