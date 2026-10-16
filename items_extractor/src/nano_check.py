from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

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
    profession_id: Optional[int]


def profession_id(criteria: List[Tuple[int, int, int]]) -> Optional[int]:
    # The first profession required, if any
    for stat, value, op in criteria:
        if stat in PROFESSION_STATS and op == OP_EQUAL:
            return value
    return None


def read_uploads(crystal: RDBItem) -> List[Upload]:
    # Nanos the crystal uploads, each with the profession its upload requires, otherwise the crystal's
    crystal_profession = profession_id([(c.criteria1, c.criteria2, c.criteria3) for c in crystal.criteria_list])
    uploads = []
    for event in crystal.events:
        for function in event.functions:
            if function.function_num == UPLOAD_NANO_FUNCTION and function.params:
                reqs = [(q.required_attribute_number, q.required_attribute_value, q.required_attribute_operator) for q in function.requirements]
                required = profession_id(reqs)
                uploads.append(Upload(int(function.params[0]), crystal_profession if required is None else required))
    return uploads


def profession_name(upload: Upload, profession_names: Dict[int, str], crystal: RDBItem) -> str:
    if upload.profession_id is None:
        return GENERAL_PROFESSION
    if upload.profession_id not in profession_names:
        raise ValueError(f"Item {crystal.id} '{crystal.name}' requires unknown profession {upload.profession_id}")
    return profession_names[upload.profession_id]


def check_nanos(problems: Problems, reader: MultiChunkReader, records: List[IndexRecord], function_sets: FunctionSets,
                text_mdb: Path, modules_dir: Path) -> None:
    # Each row needs a game crystal that uploads a nano, with the row's QL, name and profession
    path = modules_dir / "nano" / "nanos.sql"
    rows = read_sql_rows(path, "nanos", [])
    check_duplicates(problems, path, rows, ["lowid", "name"])

    profession_names = read_text_category(text_mdb, PROFESSION_NAME_CATEGORY)
    extractor = RDBExtractor(function_sets)
    item_records = {r.resource_id: r for r in records if r.resource_type == IndexRecordType.AODB_ITEM_TYPE}
    nano_records = {r.resource_id: r for r in records if r.resource_type == IndexRecordType.AODB_NANO_TYPE}

    for line_number, r in rows:
        source = f"{path}:{line_number}"
        low_id, low_ql, name, profession = int(r["lowid"]), r["lowql"], r["name"], r["profession"]  # type: ignore[arg-type]
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

        required = profession_name(upload, profession_names, crystal)
        if profession != required:
            problems.add(source, f"'{name}' has profession {profession}, but item {low_id} requires {required}")
