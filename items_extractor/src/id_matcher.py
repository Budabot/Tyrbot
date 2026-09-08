from dataclasses import dataclass
import logging
from pathlib import Path
import re
import sqlite3
from typing import Dict, List, Tuple

from src.constants import (
    Attribute, ItemType, CanFlag, EventType,
    WEAPON_GROUPS, ARMOR_GROUPS
)
from src.rdb_extractor import RDBItem

log = logging.getLogger(__name__)


@dataclass
class Entry:
    id: int
    ql: int
    name: str
    icon_id: int
    item_type: str


def get_version(ao_path: str, build_number: int) -> str:
    version_file = Path(ao_path) / "version.id"
    with open(version_file, "r", encoding="utf-8", errors="replace") as f:
        version_str = f.read().strip()
    m = re.search(r"(\d+)\.(\d+)\.(\d+)", version_str)
    if m:
        p0, p1, p2 = int(m.group(1)), int(m.group(2)), int(m.group(3))
    else:
        clean_str = re.sub(r"_[^.]*", "", version_str)
        parts = [int(p) for p in clean_str.split(".")]
        p0, p1, p2 = parts[0], parts[1], parts[2]
    return f"{p0:02d}.{p1:02d}.{p2:02d}.{build_number:02d}"


def get_new_file_name(ao_path: str, filename_template: str, output_dir: str, build_number: int = 0) -> str:
    version = get_version(ao_path, build_number)
    filename = filename_template.replace("{version}", version)
    full_path = Path(output_dir) / filename
    if full_path.exists():
        return get_new_file_name(ao_path, filename_template, output_dir, build_number + 1)
    return str(full_path)


def read_entries_from_file(file_path: str) -> List[str]:
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        return [line.strip() for line in f if line.strip()]


class IdMatcher:
    def __init__(self, config_dir: str):
        self.config_dir = Path(config_dir)

    def write_sql_file(self, rdb_items: List[RDBItem], rdb_nanos: List[RDBItem], ao_path: str, output_dir: str):
        conn = sqlite3.connect(":memory:")
        cur = conn.cursor()

        cur.execute("DROP TABLE IF EXISTS entries;")
        cur.execute("DROP TABLE IF EXISTS aodb;")
        cur.execute("CREATE TABLE entries (aoid INT, ql INT, name VARCHAR(255), icon INT, itemtype TEXT, hash TEXT);")
        cur.execute("CREATE TABLE aodb (lowid INT, highid INT, lowql INT, highql INT, name VARCHAR(150), icon INT);")

        # Convert RDBItems to entries
        entry_tuples = []
        for item in rdb_items:
            icon_id = item.attributes.get(Attribute.Icon, 0)
            ql = item.attributes.get(Attribute.Level, 0)
            item_type_attr = item.attributes.get(Attribute.ItemClass, 0)
            item_type = ItemType.get_name(item_type_attr) or "Armor"
            entry_tuples.append((item.id, ql, item.name.strip(), icon_id, item_type))

        log.debug(f"Writing {len(entry_tuples)} entries to in-memory database...")
        cur.executemany("INSERT INTO entries (aoid, ql, name, icon, itemtype) VALUES (?, ?, ?, ?, ?);", entry_tuples)
        cur.execute("CREATE INDEX idx_name ON entries (name);")
        cur.execute("CREATE INDEX idx_aoid ON entries (aoid);")

        # Process lists
        static_list = read_entries_from_file(str(self.config_dir / "static_list.txt"))
        delete_list = read_entries_from_file(str(self.config_dir / "delete_list.txt"))
        name_separation_list = read_entries_from_file(str(self.config_dir / "nameseparation_list.txt"))

        log.info(f"Processing static list ({len(static_list)} rules)...")
        self.process_static_list(conn, static_list)
        log.info(f"Processing delete list ({len(delete_list)} rules)...")
        self.process_delete_list(conn, delete_list)
        log.info(f"Processing name separations ({len(name_separation_list)} rules)...")
        self.process_name_separations(conn, name_separation_list)
        self.process_remaining_entries(conn)

        # Output aodb SQL file
        items_db_filename = get_new_file_name(ao_path, "aodb{version}.sql", output_dir)
        self.output_sql_file(conn, items_db_filename)

        items_map = {item.id: item for item in rdb_items}
        nanos_map = {nano.id: nano for nano in rdb_nanos}

        # Output weapon attributes SQL file
        weapon_attr_filename = get_new_file_name(ao_path, "weapon_attributes{version}.sql", output_dir)
        self.output_weapon_attributes(items_map, conn, weapon_attr_filename)

        # Output buffs and item types SQL files
        buffs_filename = get_new_file_name(ao_path, "item_buffs{version}.sql", output_dir)
        item_types_filename = get_new_file_name(ao_path, "item_types{version}.sql", output_dir)
        self.output_buff_info(items_map, nanos_map, conn, buffs_filename, item_types_filename)

        conn.close()

    def process_static_list(self, conn: sqlite3.Connection, static_list: List[str]):
        cur = conn.cursor()
        parsed_entries = []
        for line in static_list:
            line_str = line.strip()
            if not line_str or line_str.startswith("#"):
                continue
            parms = [p.strip() for p in line_str.split(",")]
            if len(parms) < 4:
                log.warning(f"static_list: '{line_str}' -> invalid format (expected >= 4 comma-separated values)")
                continue
            try:
                low_id, high_id = int(parms[0]), int(parms[1])
                low_ql, high_ql = int(parms[2]), int(parms[3])
            except ValueError as e:
                log.warning(f"static_list: '{line_str}' -> error parsing integers: {e}")
                continue
            parsed_entries.append((line_str, parms, low_id, high_id, low_ql, high_ql))

        for line_str, parms, low_id, high_id, low_ql, high_ql in parsed_entries:
            cur.execute("SELECT aoid, ql, name, icon, itemtype FROM entries WHERE aoid = ?;", (low_id,))
            row = cur.fetchone()
            if row:
                res_aoid, res_ql, res_name, res_icon, res_type = row
                name = parms[5] if len(parms) >= 6 else res_name
                icon = int(parms[4]) if len(parms) >= 5 else res_icon
                low = Entry(low_id, low_ql, name, icon, res_type)
                high = Entry(high_id, high_ql, "", 0, "")
                self.add_item(conn, low, high)
                log.debug(f"static_list: '{line_str}' -> added item '{name}' (lowid={low_id}, highid={high_id}, ql={low_ql}-{high_ql})")
            else:
                log.debug(f"static_list: '{line_str}' -> low item id {low_id} (ql {low_ql}) not found in entries")

        deleted_count = 0
        for line_str, parms, low_id, high_id, low_ql, high_ql in parsed_entries:
            cur.execute("DELETE FROM entries WHERE aoid IN (?, ?);", (low_id, high_id))
            deleted_count += cur.rowcount
        log.debug(f"static_list cleanup: removed {deleted_count} staged entries matching static list IDs")

    def process_delete_list(self, conn: sqlite3.Connection, delete_list: List[str]):
        cur = conn.cursor()
        total_deleted = 0
        for line in delete_list:
            clause = line.strip()
            if not clause or clause.startswith("#"):
                continue
            try:
                cur.execute(f"SELECT aoid, ql, name FROM entries WHERE {clause};")
                items_to_delete = cur.fetchall()
                if items_to_delete:
                    cur.execute(f"DELETE FROM entries WHERE {clause};")
                    deleted = cur.rowcount
                    total_deleted += deleted
                    for aoid, ql, name in items_to_delete:
                        clean_name = str(name).replace("\r", "").replace("\n", " ")
                        log.debug(f"delete_list: '{clause}' -> deleted item '{clean_name}' (id: {aoid}, ql: {ql})")
                    log.debug(f"delete_list: '{clause}' -> total deleted: {deleted}")
                else:
                    log.debug(f"delete_list: '{clause}' -> deleted 0 entries")
            except sqlite3.OperationalError as e:
                log.error(f"delete_list: '{clause}' -> SQL error: {e}")
        log.debug(f"delete_list: total deleted entries = {total_deleted}")

    def process_name_separations(self, conn: sqlite3.Connection, name_separation_list: List[str]):
        cur = conn.cursor()
        for line in name_separation_list:
            line_str = line.strip()
            if not line_str or line_str.startswith("#"):
                continue
            parms = [p.strip() for p in line_str.split(",")]
            if len(parms) < 3:
                log.warning(f"nameseparation_list: '{line_str}' -> invalid format (expected 3 comma-separated values)")
                continue
            p0, p1, p2 = parms[0], parms[1], parms[2]
            p0_clean = p0.replace("%", "")
            p1_clean = p1.replace("%", "")

            cur.execute(
                """
                SELECT DISTINCT replace(replace(name, ?, ''), ?, '') AS common_name
                FROM entries WHERE (name LIKE ? OR name LIKE ?)
                AND itemtype = ? ORDER BY common_name;
                """,
                (p1_clean, p0_clean, p0, p1, p2)
            )
            common_names = [row[0] for row in cur.fetchall()]

            cur.execute("SELECT MAX(rowid) FROM aodb;")
            max_rowid_before = cur.fetchone()[0] or 0

            total_entries_matched = 0
            for common_name in common_names:
                cur.execute(
                    """
                    SELECT aoid, ql, name, icon, itemtype FROM (
                        SELECT aoid, ql, name, icon, itemtype, replace(replace(name, ?, ''), ?, '') AS common_name
                        FROM entries
                    ) t WHERE (name LIKE ? OR name LIKE ?)
                    AND common_name = ? AND itemtype = ?
                    ORDER BY ql ASC;
                    """,
                    (p1_clean, p0_clean, p0, p1, common_name, p2)
                )
                entries = [Entry(r[0], r[1], r[2], r[3], r[4]) for r in cur.fetchall()]
                if entries:
                    total_entries_matched += len(entries)
                    for entry in entries:
                        clean_name = str(entry.name).replace("\r", "").replace("\n", " ")
                        log.debug(f"nameseparation_list: '{line_str}' -> processed item '{clean_name}' (id: {entry.id}, ql: {entry.ql})")
                    self.pair_entries(conn, entries)

            cur.execute("SELECT lowid, highid, lowql, highql, name FROM aodb WHERE rowid > ?;", (max_rowid_before,))
            new_paired = cur.fetchall()
            for lowid, highid, lowql, highql, pair_name in new_paired:
                clean_pair_name = str(pair_name).replace("\r", "").replace("\n", " ")
                log.debug(f"nameseparation_list: '{line_str}' -> paired item '{clean_pair_name}' (low: {lowid} ql {lowql}, high: {highid} ql {highql})")

            items_created = len(new_paired)

            if common_names:
                log.debug(
                    f"nameseparation_list: '{line_str}' -> "
                    f"matched {len(common_names)} group(s) ({total_entries_matched} entries), "
                    f"created {items_created} items"
                )
            else:
                log.debug(f"nameseparation_list: '{line_str}' -> no matching entries found")

        for line in name_separation_list:
            line_str = line.strip()
            if not line_str or line_str.startswith("#"):
                continue
            parms = [p.strip() for p in line_str.split(",")]
            if len(parms) < 3:
                continue
            cur.execute(
                "DELETE FROM entries WHERE (name LIKE ? OR name LIKE ?) AND itemtype = ?;",
                (parms[0], parms[1], parms[2])
            )
            log.debug(f"nameseparation_list cleanup: '{line_str}' -> removed {cur.rowcount} entries from staging")

    def process_remaining_entries(self, conn: sqlite3.Connection):
        cur = conn.cursor()
        cur.execute("SELECT DISTINCT name, itemtype FROM entries ORDER BY name;")
        distinct_names = cur.fetchall()

        for name, item_type in distinct_names:
            cur.execute(
                "SELECT aoid, ql, name, icon, itemtype FROM entries WHERE name = ? AND itemtype = ? ORDER BY ql ASC;",
                (name, item_type)
            )
            entries = [Entry(r[0], r[1], r[2], r[3], r[4]) for r in cur.fetchall()]

            sequential = not any(entries[i].ql >= entries[i + 1].ql for i in range(len(entries) - 1))

            if sequential:
                self.pair_entries(conn, entries)
            else:
                cur.execute(
                    "SELECT aoid, ql, name, icon, itemtype FROM entries WHERE name = ? AND itemtype = ? ORDER BY aoid ASC;",
                    (name, item_type)
                )
                entries2 = [Entry(r[0], r[1], r[2], r[3], r[4]) for r in cur.fetchall()]

                current_ql = 0
                temp_entries: List[Entry] = []
                for entry in entries2:
                    if current_ql >= entry.ql:
                        self.pair_entries(conn, temp_entries)
                        temp_entries = []
                    temp_entries.append(entry)
                    current_ql = entry.ql
                self.pair_entries(conn, temp_entries)

    def pair_entries(self, conn: sqlite3.Connection, entries: List[Entry]):
        if not entries:
            return
        if len(entries) == 1:
            self.add_item(conn, entries[0], entries[0])
            return

        temp = [entries[0]]
        i = 1
        while i < len(entries) - 1:
            if entries[i].ql == entries[i + 1].ql - 1:
                temp.append(entries[i])
                temp.append(entries[i + 1])
                i += 2
            else:
                entry = Entry(entries[i].id, entries[i].ql - 1, entries[i].name, entries[i].icon_id, entries[i].item_type)
                temp.append(entry)
                temp.append(entries[i])
                i += 1
        if i < len(entries):
            temp.append(entries[-1])

        self.add_entry_items(conn, temp)

    def add_entry_items(self, conn: sqlite3.Connection, entries: List[Entry]):
        for idx in range(0, len(entries), 2):
            pair = entries[idx:idx + 2]
            if len(pair) == 1:
                self.add_item(conn, pair[0], pair[0])
            elif pair[0].ql == pair[1].ql - 1:
                self.add_item(conn, pair[0], pair[0])
                self.add_item(conn, pair[1], pair[1])
            elif pair[0].name != pair[1].name:
                self.add_item(conn, pair[0], Entry(pair[1].id, pair[1].ql - 1, pair[0].name, pair[0].icon_id, pair[0].item_type))
                self.add_item(conn, pair[1], pair[1])
            else:
                self.add_item(conn, pair[0], pair[1])

    def add_item(self, conn: sqlite3.Connection, low: Entry, high: Entry):
        if low.ql > high.ql:
            log.error(f"Invalid item! low ql is greater than high ql: {low} {high}")
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO aodb (lowid, highid, lowql, highql, name, icon) VALUES (?, ?, ?, ?, ?, ?);",
            (low.id, high.id, low.ql, high.ql, low.name, low.icon_id)
        )

    def output_sql_file(self, conn: sqlite3.Connection, file_path: str):
        log.debug(f"Writing results to file: '{file_path}'")
        cur = conn.cursor()
        with open(file_path, "w", encoding="utf-8", newline="\n") as f:
            f.write("DROP TABLE IF EXISTS aodb;\n")
            f.write("CREATE TABLE aodb (lowid INT, highid INT, lowql INT, highql INT, name VARCHAR(150), icon INT);\n")

            cur.execute("SELECT lowid, highid, lowql, highql, name, icon FROM aodb ORDER BY name, lowql, lowid;")
            for lowid, highid, lowql, highql, name, icon in cur.fetchall():
                escaped_name = name.replace("'", "''")
                f.write(f"INSERT INTO aodb VALUES ({lowid}, {highid}, {lowql}, {highql}, '{escaped_name}', {icon});\n")

            f.write("CREATE INDEX idx_highid ON aodb(highid);\n")

    def output_weapon_attributes(self, items_map: Dict[int, RDBItem], conn: sqlite3.Connection, file_path: str):
        log.debug(f"Writing weapon attributes to file: '{file_path}'")
        cur = conn.cursor()
        cur.execute("SELECT lowid AS id FROM aodb UNION SELECT highid AS id FROM aodb ORDER BY id;")
        ids = [r[0] for r in cur.fetchall()]

        with open(file_path, "w", encoding="utf-8", newline="\n") as f:
            f.write("DROP TABLE IF EXISTS weapon_attributes;\n")
            f.write("CREATE TABLE weapon_attributes (id INT PRIMARY KEY, attack_time INT NOT NULL, recharge_time INT NOT NULL, full_auto INT, burst INT, fling_shot TINYINT NOT NULL, fast_attack TINYINT NOT NULL, aimed_shot TINYINT NOT NULL);\n")

            for item_id in ids:
                item = items_map.get(item_id)
                if not item:
                    continue
                if Attribute.ItemDelay not in item.attributes or Attribute.RechargeDelay not in item.attributes:
                    continue

                flags = item.attributes.get(Attribute.Can, 0)
                attack_time = item.attributes[Attribute.ItemDelay]
                recharge_time = item.attributes[Attribute.RechargeDelay]

                full_auto_val = item.attributes.get(
                    Attribute.FullAutoRecharge,
                    "1" if (flags & CanFlag.FullAuto == CanFlag.FullAuto) else "NULL"
                )
                burst_val = item.attributes.get(
                    Attribute.BurstRecharge,
                    "1" if (flags & CanFlag.Burst == CanFlag.Burst) else "NULL"
                )
                fling_shot = "1" if (flags & CanFlag.FlingShot == CanFlag.FlingShot) else "0"
                fast_attack = "1" if (flags & CanFlag.FastAttack == CanFlag.FastAttack) else "0"
                aimed_shot = "1" if (flags & CanFlag.AimedShot == CanFlag.AimedShot) else "0"

                f.write(f"INSERT INTO weapon_attributes VALUES ({item.id}, {attack_time}, {recharge_time}, {full_auto_val}, {burst_val}, {fling_shot}, {fast_attack}, {aimed_shot});\n")

    def output_buff_info(self, items_map: Dict[int, RDBItem], nanos_map: Dict[int, RDBItem], conn: sqlite3.Connection, buffs_file: str, item_types_file: str):
        log.debug(f"Writing buff attributes to file: '{buffs_file}'")
        log.debug(f"Writing itemTypes to file: '{item_types_file}'")
        cur = conn.cursor()
        cur.execute("SELECT lowid AS itemid FROM aodb WHERE lowid != 206704 UNION SELECT highid AS itemid FROM aodb WHERE highid != 206704 ORDER BY itemid;")
        item_ids = [r[0] for r in cur.fetchall()]

        with open(item_types_file, "w", encoding="utf-8", newline="\n") as types_f, \
             open(buffs_file, "w", encoding="utf-8", newline="\n") as buffs_f:

            types_f.write("DROP TABLE IF EXISTS item_types;\n")
            types_f.write("CREATE TABLE item_types (item_id INT, item_type VARCHAR(50));\n")

            buffs_f.write("DROP TABLE IF EXISTS item_buffs;\n")
            buffs_f.write("CREATE TABLE item_buffs (item_id INT, attribute_id INT, amount INT);\n")

            for item_id in item_ids:
                rdb_item = items_map.get(item_id)
                if not rdb_item:
                    continue

                item_type = self.get_item_type(rdb_item)
                if item_type not in ("Spirit", "Implant", "Misc", "Unknown"):
                    if self.write_buffs(rdb_item, rdb_item.id, EventType.OnWear, buffs_f):
                        if item_type == "Armor":
                            sub_types = self.get_slots(ARMOR_GROUPS, rdb_item)
                        elif item_type == "Weapon":
                            sub_types = self.get_slots(WEAPON_GROUPS, rdb_item)
                        else:
                            sub_types = ["Unknown"]
                        for st in sub_types:
                            types_f.write(f"INSERT INTO item_types (item_id, item_type) VALUES ({rdb_item.id}, '{st}');\n")

                # Nano buffs
                nano_buffs: List[RDBItem] = []
                for ev in rdb_item.events:
                    if ev.event_type == EventType.OnUse:
                        for func in ev.functions:
                            if func.function_num == 53019 and func.params:
                                try:
                                    nano_id = int(func.params[0])
                                    if nano_id in nanos_map:
                                        nano_buffs.append(nanos_map[nano_id])
                                except (ValueError, IndexError):
                                    pass

                has_buffs = False
                for nano_item in nano_buffs:
                    if self.write_buffs(nano_item, rdb_item.id, EventType.OnUse, buffs_f):
                        log.debug(f"Item {rdb_item.name} uploads nano {nano_item.name}")
                        has_buffs = True

                if has_buffs:
                    types_f.write(f"INSERT INTO item_types (item_id, item_type) VALUES ({rdb_item.id}, 'Nanoprogram');\n")

            buffs_f.write("CREATE INDEX idx_item_id ON item_buffs(item_id);\n")
            types_f.write("CREATE INDEX idx_item_type ON item_types(item_type);\n")

    def write_buffs(self, rdb_item: RDBItem, item_id: int, event_type: int, writer) -> bool:
        buffs = self.get_buffs(rdb_item, event_type)
        for attr_id, amount in buffs:
            writer.write(f"INSERT INTO item_buffs (item_id, attribute_id, amount) VALUES ({item_id}, {attr_id}, {amount});\n")
        return len(buffs) > 0

    def get_buffs(self, item: RDBItem, event_type: int) -> List[Tuple[int, int]]:
        buffs = []
        for ev in item.events:
            if ev.event_type == event_type:
                for func in ev.functions:
                    if func.function_num == 53045 and len(func.params) >= 2:
                        try:
                            buffs.append((int(func.params[0]), int(func.params[1])))
                        except ValueError:
                            pass
        return buffs

    def get_item_type(self, item: RDBItem) -> str:
        class_id = item.attributes.get(Attribute.ItemClass)
        if class_id is None:
            return "Unknown"
        return ItemType.get_name(class_id) or "Armor"

    def get_slots(self, groups: List[Tuple[List[int], str]], item: RDBItem) -> List[str]:
        placement = item.attributes.get(Attribute.Placement)
        if placement is None:
            return ["Unknown"]
        results = []
        for bitmasks, label in groups:
            if any((mask & placement) == mask for mask in bitmasks):
                results.append(label)
        return results if results else ["Unknown"]
