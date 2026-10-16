from collections import defaultdict
from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Dict, List, Set, Tuple

from src.check_helpers import Problems, check_duplicates, read_sql_rows
from src.constants import Attribute, IndexRecordType
from src.function_sets import FunctionSets
from src.perks import PROFESSION_NAME_CATEGORY
from src.rdb_extractor import RDBExtractor, RDBItem
from src.rdb_file import MultiChunkReader
from src.rdb_index import IndexRecord
from src.skills import read_text_category

log = logging.getLogger(__name__)

UPLOAD_NANO_FUNCTION = 53019
PROFESSION_STATS = (60, 368)
OP_EQUAL = 0
GENERAL_PROFESSION = "General"


@dataclass
class Upload:
    nano_id: int
    profession_ids: Set[int]


def profession_ids(criteria: List[Tuple[int, int, int]]) -> Set[int]:
    # Every profession the criteria allow
    return {value for stat, value, op in criteria if stat in PROFESSION_STATS and op == OP_EQUAL}


def read_uploads(crystal: RDBItem) -> List[Upload]:
    # Nanos the crystal uploads, each with the professions its upload allows, otherwise the crystal's
    crystal_professions = profession_ids([(c.criteria1, c.criteria2, c.criteria3) for c in crystal.criteria_list])
    uploads = []
    for event in crystal.events:
        for function in event.functions:
            if function.function_num == UPLOAD_NANO_FUNCTION and function.params:
                reqs = [(q.required_attribute_number, q.required_attribute_value, q.required_attribute_operator) for q in function.requirements]
                required = profession_ids(reqs)
                uploads.append(Upload(int(function.params[0]), required or crystal_professions))
    return uploads


def profession_names_of(upload: Upload, profession_names: Dict[int, str], crystal: RDBItem) -> Set[str]:
    if not upload.profession_ids:
        return {GENERAL_PROFESSION}
    unknown = upload.profession_ids - profession_names.keys()
    if unknown:
        raise ValueError(f"Item {crystal.id} '{crystal.name}' requires unknown professions {sorted(unknown)}")
    return {profession_names[p] for p in upload.profession_ids}


def read_row_professions(problems: Problems, path: Path, nano_ids: Set[int]) -> Dict[int, Set[str]]:
    # Each nano's professions; every row must name a nano and every nano needs a profession
    rows = read_sql_rows(path, "nanos_professions", [])
    check_duplicates(problems, path, rows, ["nano_id", "profession"])
    professions: Dict[int, Set[str]] = defaultdict(set)
    for line_number, r in rows:
        nano_id = int(r["nano_id"])  # type: ignore[arg-type]
        if nano_id not in nano_ids:
            problems.add(f"{path}:{line_number}", f"nano id {nano_id} is not in nanos.sql")
        professions[nano_id].add(str(r["profession"]))
    return professions


def check_nanos(problems: Problems, reader: MultiChunkReader, records: List[IndexRecord], function_sets: FunctionSets,
                text_mdb: Path, modules_dir: Path) -> None:
    # Each row needs a game crystal that uploads a nano, with the row's QL, name and professions
    path = modules_dir / "nano" / "nanos.sql"
    rows = read_sql_rows(path, "nanos", [])
    check_duplicates(problems, path, rows, ["id"])
    check_duplicates(problems, path, rows, ["lowid", "name"])
    row_professions = read_row_professions(problems, modules_dir / "nano" / "nanos_professions.sql", {int(r["id"]) for _, r in rows})  # type: ignore[arg-type]

    profession_names = read_text_category(text_mdb, PROFESSION_NAME_CATEGORY)
    extractor = RDBExtractor(function_sets)
    item_records = {r.resource_id: r for r in records if r.resource_type == IndexRecordType.AODB_ITEM_TYPE}
    nano_records = {r.resource_id: r for r in records if r.resource_type == IndexRecordType.AODB_NANO_TYPE}

    for line_number, r in rows:
        source = f"{path}:{line_number}"
        low_id, low_ql, name = int(r["lowid"]), r["lowql"], r["name"]  # type: ignore[arg-type]
        professions = row_professions.get(int(r["id"]), set())  # type: ignore[arg-type]
        if not professions:
            problems.add(source, f"'{name}' has no professions in nanos_professions.sql")
        if low_id not in item_records:
            problems.add(source, f"'{name}' has id {low_id}, which is not an item in the game")
            continue
        crystal = extractor.read_item(reader, item_records[low_id], extract_functions=True)
        crystal_name = crystal.name.strip()

        ql = crystal.attributes.get(Attribute.Level)
        if ql != low_ql:
            problems.add(source, f"'{name}' has QL {low_ql}, but item {low_id} is QL {ql}")

        uploads = read_uploads(crystal)
        if not uploads:
            problems.add(source, f"'{name}' has id {low_id}, which uploads no nano")
            continue
        missing = [u.nano_id for u in uploads if u.nano_id not in nano_records]
        if missing:
            problems.add(source, f"'{name}' has id {low_id}, which uploads nanos {missing} that are not in the game")
            continue
        nano_names = [extractor.read_item(reader, nano_records[u.nano_id], extract_functions=False).name.strip() for u in uploads]

        # A crystal is listed by its own name; a box uploading several nanos is listed once per nano, as "box [nano]"
        if len(uploads) == 1:
            upload = uploads[0]
            if name != crystal_name:
                problems.add(source, f"'{name}' has id {low_id}, which is named '{crystal_name}'")
        else:
            listed = {f"{crystal_name} [{n}]": u for n, u in zip(nano_names, uploads)}
            if name not in listed:
                problems.add(source, f"'{name}' is not '{crystal_name} [<nano>]' for any nano that box {low_id} uploads")
                continue
            upload = listed[name]  # type: ignore[index]

        required = profession_names_of(upload, profession_names, crystal)
        if professions and professions != required:
            problems.add(source, f"'{name}' has professions {', '.join(sorted(professions))}, but item {low_id} allows {', '.join(sorted(required))}")
