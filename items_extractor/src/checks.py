from collections import defaultdict
from dataclasses import dataclass
import json
import logging
from pathlib import Path
import re
from typing import Dict, List, Set

from src.check_helpers import Problems, check_duplicates, read_sql_rows
from src.constants import IndexRecordType
from src.function_sets import FunctionSets
from src.nano_check import check_nanos
from src.rdb_file import MultiChunkReader
from src.rdb_index import IndexRecord
from src.whompah_check import check_whompah_routes

log = logging.getLogger(__name__)

RECIPE_ITEM = re.compile(r"#L \"([^\"]+)\" \"([\d+]+)\"")
RECIPE_FILE = re.compile(r"^\d+\.json$")


@dataclass
class AodbItem:
    low_id: int
    high_id: int
    low_ql: int
    high_ql: int
    name: str


def read_aodb(path: Path) -> List[AodbItem]:
    rows = read_sql_rows(path, "aodb", ["lowid", "highid", "lowql", "highql", "name", "icon"])
    return [AodbItem(int(r["lowid"]), int(r["highid"]), int(r["lowql"]), int(r["highql"]), str(r["name"])) for _, r in rows]  # type: ignore[arg-type]


class ItemLookup:
    # The item lookups the bot's modules make against aodb, and the item ids the game has
    def __init__(self, items: List[AodbItem], game_ids: Set[int]):
        self.game_ids = game_ids
        self.by_high_id: Dict[int, List[AodbItem]] = defaultdict(list)
        self.names: Set[str] = set()
        for item in items:
            self.by_high_id[item.high_id].append(item)
            self.names.add(item.name)


def check_raid_loot(problems: Problems, modules_dir: Path, lookup: ItemLookup) -> None:
    # Each row needs an item with its high id whose QL range holds the row's QL and whose name matches
    path = modules_dir / "raid" / "raid_loot.sql"
    rows = read_sql_rows(path, "raid_loot", [])
    for line_number, r in rows:
        ql, high_id, name = r["ql"], r["high_id"], r["name"]
        items = lookup.by_high_id.get(int(high_id), [])  # type: ignore[arg-type]
        if not items:
            problems.add(f"{path}:{line_number}", f"'{name}' has high id {high_id}, which is not a high id in aodb")
            continue
        in_range = [i for i in items if i.low_ql <= int(ql) <= i.high_ql]  # type: ignore[arg-type]
        if not in_range:
            ranges = [(i.low_ql, i.high_ql) for i in items]
            problems.add(f"{path}:{line_number}", f"'{name}' has QL {ql}, outside the QL ranges {ranges} of item {high_id}")
        elif all(i.name != name for i in in_range):
            problems.add(f"{path}:{line_number}", f"'{name}' has high id {high_id}, which is named '{in_range[0].name}'")
    check_duplicates(problems, path, rows, ["raid", "category", "ql", "high_id", "name"])


def check_boss_loot(problems: Problems, modules_dir: Path, lookup: ItemLookup) -> None:
    # Each row needs a known boss and an item with its name
    boss_path = modules_dir / "bossloot" / "boss.sql"
    bosses = read_sql_rows(boss_path, "boss", ["id", "name"])
    check_duplicates(problems, boss_path, bosses, ["id"])
    boss_ids = {r["id"] for _, r in bosses}

    path = modules_dir / "bossloot" / "boss_loot.sql"
    rows = read_sql_rows(path, "boss_loot", ["boss_id", "item_name"])
    for line_number, r in rows:
        if r["boss_id"] not in boss_ids:
            problems.add(f"{path}:{line_number}", f"boss id {r['boss_id']} is not in {boss_path.name}")
        if r["item_name"] not in lookup.names:
            problems.add(f"{path}:{line_number}", f"no item in aodb is named '{r['item_name']}'")
    check_duplicates(problems, path, rows, ["boss_id", "item_name"])


def check_recipe(problems: Problems, path: Path, lookup: ItemLookup) -> None:
    with open(path, encoding="utf-8") as f:
        recipe = json.load(f)

    # Items the recipe text links, lists or details must exist in the game
    for name, item_id in RECIPE_ITEM.findall(recipe.get("raw", "")):
        if int(item_id) not in lookup.game_ids:
            problems.add(str(path), f"links '{name}' to item {item_id}, which is not in the game")

    # Listed items, which are the only items steps may use; placeholders for unknown items have no id
    aliases = set()
    for i in recipe.get("items", []):
        aliases.add(i["alias"])
        if "item_id" in i and i["item_id"] not in lookup.game_ids:
            problems.add(str(path), f"lists '{i['alias']}' as item {i['item_id']}, which is not in the game")
    for step in recipe.get("steps", []):
        # Text steps only label the steps around them
        if "text" in step:
            continue
        for part in ("source", "target", "result"):
            if step[part] not in aliases:
                problems.add(str(path), f"has a step {part} '{step[part]}' that is not in its items")
    for detail in recipe.get("details", []):
        if "item" in detail:
            i = detail["item"]
            if i["id"] not in lookup.game_ids:
                problems.add(str(path), f"details item {i['id']}, which is not in the game")


def check_recipes(problems: Problems, modules_dir: Path, lookup: ItemLookup) -> None:
    recipe_dir = modules_dir / "recipe" / "recipes"
    # Only files named by recipe id are loaded by the bot
    paths = sorted(p for p in recipe_dir.glob("*.json") if RECIPE_FILE.match(p.name))
    if not paths:
        raise ValueError(f"No recipes found in {recipe_dir}")
    for path in paths:
        check_recipe(problems, path, lookup)


def run_checks(reader: MultiChunkReader, records: List[IndexRecord], function_sets: FunctionSets, text_mdb: Path,
               modules_dir: Path) -> int:
    problems = Problems()
    game_ids = {r.resource_id for r in records if r.resource_type == IndexRecordType.AODB_ITEM_TYPE}
    lookup = ItemLookup(read_aodb(modules_dir / "items" / "sql" / "aodb.sql"), game_ids)
    for name, check in (("raid loot", check_raid_loot), ("boss loot", check_boss_loot), ("recipes", check_recipes)):
        log.info(f"Checking {name}...")
        check(problems, modules_dir, lookup)
    log.info("Checking whompah routes...")
    check_whompah_routes(problems, reader, records, modules_dir)
    log.info("Checking nanos...")
    check_nanos(problems, reader, records, function_sets, text_mdb, modules_dir)
    return problems.count
