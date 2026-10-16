import configparser
from collections import defaultdict
from dataclasses import dataclass
from fractions import Fraction
import logging
import math
from pathlib import Path
import re
from typing import Dict, Iterable, List, Set, Tuple

from src.rdb_extractor import RDBItem

log = logging.getLogger(__name__)

QL_STAT = 54
ITEM_CLASS_STAT = 76
SLOT_STAT = 88
TREATMENT_STAT = 124
PROFESSION_STAT = 60
IMPLANT_ITEM_CLASS = 3
OP_EQUAL = 0
OP_GREATER_THAN = 2
WEAR_EVENT = 14
MODIFY_FUNCTION = 53045
SKILL_STATS = range(100, 169)
IMPLANT_QLS = (1, 200, 201, 300)
QL_RANGES = ((1, 200), (201, 300))

# Cluster grades in the order an implant's modifiers list them
GRADE_ORDER = ("Faded", "Bright", "Shining")
CLUSTER_TYPE_IDS = {"Faded": 1, "Bright": 2, "Shining": 3}

GRADE_LINE = re.compile(r"^(Faded|Bright|Shining) NanoCluster: ([^\r\n]*)", re.MULTILINE)
SYMBIANT_NAME = re.compile(r"^.+ Symbiant, \w+ Unit Aban$")
ROW_ID = re.compile(r"^INSERT INTO \w+ \([^)]*\) VALUES \((-?\d+),")


@dataclass
class ImplantConfig:
    slots: Set[int]
    abilities: Set[int]
    professions: Set[int]
    clusters: Set[int]
    excluded_items: Set[int]


@dataclass
class Implant:
    item_id: int
    ql: int
    slot_id: int
    cluster_ids: Dict[str, int]
    modifiers: Dict[str, Tuple[int, int]]
    ability_id: int
    treatment: int
    ability: int


@dataclass
class Symbiant:
    item_id: int
    name: str
    ql: int
    slot_id: int
    treatment: int
    level: int
    abilities: Dict[int, int]
    profession_ids: List[int]
    clusters: Dict[int, int]


def read_table_ids(path: Path) -> Set[int]:
    # First column of each row in one of the implant module's SQL files
    ids: Set[int] = set()
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.startswith("INSERT INTO"):
                match = ROW_ID.match(line)
                if not match:
                    raise ValueError(f"Cannot read the id of a row in {path}: {line.strip()}")
                ids.add(int(match.group(1)))
    if not ids:
        raise ValueError(f"No rows found in {path}")
    return ids


def read_implant_config(path: Path, implant_dir: Path) -> ImplantConfig:
    # Excluded items from the extractor config; valid game ids from the module's slot, ability, profession and cluster tables
    parser = configparser.ConfigParser(inline_comment_prefixes=(";",), allow_no_value=True)
    with open(path, encoding="utf-8") as f:
        parser.read_file(f)

    return ImplantConfig(
        slots=read_table_ids(implant_dir / "ImplantType.sql"),
        abilities=read_table_ids(implant_dir / "Ability.sql"),
        professions=read_table_ids(implant_dir / "Profession.sql"),
        clusters=read_table_ids(implant_dir / "Cluster.sql"),
        excluded_items={int(key) for key, _ in parser.items("implant_excluded_items")},
    )


def check_id(ids: Set[int], value: int, what: str, item: RDBItem) -> int:
    if value not in ids:
        raise ValueError(f"Item {item.id} '{item.name}' has {what} {value}, which is not in the implant module's tables")
    return value


def get_stat(item: RDBItem, stat: int) -> int:
    if stat not in item.attributes:
        raise ValueError(f"Item {item.id} '{item.name}' has no stat {stat}")
    return item.attributes[stat]


def get_modifiers(item: RDBItem) -> List[Tuple[int, int]]:
    return [(int(f.params[0]), int(f.params[1]))
            for event in item.events if event.event_type == WEAR_EVENT
            for f in event.functions if f.function_num == MODIFY_FUNCTION]


def get_requirements(item: RDBItem, stats: Iterable[int]) -> Dict[int, int]:
    # Minimum stat values, from "greater than" wear criteria
    wanted = set(stats)
    reqs: Dict[int, int] = {}
    for c in item.criteria_list:
        if c.criteria3 == OP_GREATER_THAN and c.criteria1 in wanted:
            if c.criteria1 in reqs:
                raise ValueError(f"Item {item.id} '{item.name}' requires stat {c.criteria1} more than once")
            reqs[c.criteria1] = c.criteria2 + 1
    return reqs


def get_single_requirement(item: RDBItem, stats: Iterable[int], what: str) -> Tuple[int, int]:
    reqs = get_requirements(item, stats)
    if len(reqs) != 1:
        raise ValueError(f"Item {item.id} '{item.name}' has {len(reqs)} {what} requirements")
    return next(iter(reqs.items()))


def read_implant(item: RDBItem, config: ImplantConfig) -> Implant:
    grades = GRADE_LINE.findall(item.description)
    if sorted(g for g, _ in grades) != sorted(GRADE_ORDER):
        raise ValueError(f"Implant {item.id} '{item.name}' does not list each cluster grade once")
    filled = [g for g in GRADE_ORDER if any(grade == g and name.strip() != "Empty" for grade, name in grades)]

    modifiers = get_modifiers(item)
    if len(modifiers) != len(filled):
        raise ValueError(f"Implant {item.id} '{item.name}' has {len(modifiers)} modifiers for {len(filled)} clusters")

    cluster_ids = {g: 0 for g in GRADE_ORDER}
    for grade, (stat, _) in zip(filled, modifiers):
        cluster_ids[grade] = check_id(config.clusters, stat, "cluster stat", item)

    ability_stat, ability = get_single_requirement(item, config.abilities, "ability")
    _, treatment = get_single_requirement(item, [TREATMENT_STAT], "treatment")

    return Implant(
        item_id=item.id,
        ql=get_stat(item, QL_STAT),
        slot_id=check_id(config.slots, get_stat(item, SLOT_STAT), "slot", item),
        cluster_ids=cluster_ids,
        modifiers=dict(zip(filled, modifiers)),
        ability_id=ability_stat,
        treatment=treatment,
        ability=ability,
    )


def read_symbiant(item: RDBItem, config: ImplantConfig) -> Symbiant:
    clusters: Dict[int, int] = {}
    for stat, amount in get_modifiers(item):
        check_id(config.clusters, stat, "cluster stat", item)
        if stat in clusters:
            raise ValueError(f"Symbiant {item.id} '{item.name}' modifies cluster {stat} more than once")
        clusters[stat] = amount

    professions = sorted(check_id(config.professions, c.criteria2, "profession", item)
                         for c in item.criteria_list
                         if c.criteria1 == PROFESSION_STAT and c.criteria3 == OP_EQUAL)

    abilities = get_requirements(item, config.abilities)
    _, treatment = get_single_requirement(item, [TREATMENT_STAT], "treatment")
    _, level = get_single_requirement(item, [QL_STAT], "level")

    return Symbiant(
        item_id=item.id,
        name=item.name.strip(),
        ql=get_stat(item, QL_STAT),
        slot_id=check_id(config.slots, get_stat(item, SLOT_STAT), "slot", item),
        treatment=treatment,
        level=level,
        abilities=abilities,
        profession_ids=professions,
        clusters=clusters,
    )


def read_implants(items: List[RDBItem], config: ImplantConfig) -> Tuple[List[Implant], List[Symbiant]]:
    implants: List[Implant] = []
    symbiants: List[Symbiant] = []
    for item in items:
        if item.attributes.get(ITEM_CLASS_STAT) != IMPLANT_ITEM_CLASS or item.id in config.excluded_items:
            continue
        if GRADE_LINE.search(item.description):
            implants.append(read_implant(item, config))
        elif SYMBIANT_NAME.match(item.name.strip()):
            symbiants.append(read_symbiant(item, config))
    return implants, symbiants


def interpolate(ql: int, values: Dict[int, int]) -> int:
    # Linear interpolation within the QL range, rounded half up
    low, high = next(r for r in QL_RANGES if r[0] <= ql <= r[1])
    value = Fraction(values[high] - values[low]) * (ql - low) / (high - low) + values[low]
    return math.floor(value + Fraction(1, 2))


def group_implants(implants: List[Implant]) -> Dict[Tuple[int, int, int], Dict[int, Implant]]:
    # Implants by their shining, bright and faded cluster ids, then by QL
    combos: Dict[Tuple[int, int, int], Dict[int, Implant]] = defaultdict(dict)
    for implant in implants:
        if implant.ql not in IMPLANT_QLS:
            raise ValueError(f"Implant {implant.item_id} has QL {implant.ql}, not one of {IMPLANT_QLS}")
        key = (implant.cluster_ids["Shining"], implant.cluster_ids["Bright"], implant.cluster_ids["Faded"])
        by_ql = combos[key]
        if implant.ql in by_ql:
            raise ValueError(f"Implants {by_ql[implant.ql].item_id} and {implant.item_id} share clusters {key} at QL {implant.ql}")
        by_ql[implant.ql] = implant

    for key, by_ql in combos.items():
        if sorted(by_ql) != list(IMPLANT_QLS):
            raise ValueError(f"Implant clusters {key} exist only at QLs {sorted(by_ql)}")
        if len({(i.slot_id, i.ability_id) for i in by_ql.values()}) != 1:
            raise ValueError(f"Implants {[i.item_id for i in by_ql.values()]} differ in slot or ability")
    return combos


def build_requirements(implants: List[Implant], config: ImplantConfig) -> List[Tuple[int, ...]]:
    # Lowest wear requirements and the ability and skill cluster bonuses at each QL
    treatment: Dict[int, int] = {}
    ability: Dict[int, int] = {}
    bonuses: Dict[Tuple[str, str], Dict[int, Set[int]]] = defaultdict(lambda: defaultdict(set))
    for implant in implants:
        treatment[implant.ql] = min(implant.treatment, treatment.get(implant.ql, implant.treatment))
        ability[implant.ql] = min(implant.ability, ability.get(implant.ql, implant.ability))
        for grade, (stat, amount) in implant.modifiers.items():
            if stat in config.abilities:
                bonuses[("ability", grade)][implant.ql].add(amount)
            elif stat in SKILL_STATS:
                bonuses[("skill", grade)][implant.ql].add(amount)

    bonus_values: Dict[Tuple[str, str], Dict[int, int]] = {}
    for key, by_ql in bonuses.items():
        if sorted(by_ql) != list(IMPLANT_QLS) or any(len(amounts) != 1 for amounts in by_ql.values()):
            raise ValueError(f"Implant {key[0]} clusters at grade {key[1]} do not have one bonus per QL: {dict(by_ql)}")
        bonus_values[key] = {ql: next(iter(amounts)) for ql, amounts in by_ql.items()}

    columns = [treatment, ability] + [bonus_values[(kind, grade)]
                                      for kind in ("ability", "skill") for grade in ("Shining", "Bright", "Faded")]
    return [tuple([ql] + [interpolate(ql, values) for values in columns]) for ql in range(1, 301)]


def sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def write_sql(path: Path, header: List[str], table: str, columns: str, rows: Iterable[Tuple], separator: str = ","):
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        for line in header:
            f.write(line + "\n")
        count = 0
        for row in rows:
            values = separator.join(sql_string(v) if isinstance(v, str) else str(v) for v in row)
            f.write(f"INSERT INTO {table} ({columns}) VALUES ({values});\n")
            count += 1
    log.info(f"Wrote {count} rows to {path}")


def write_implant_sql(items: List[RDBItem], config_path: Path, implant_dir: Path):
    config = read_implant_config(config_path, implant_dir)
    implants, symbiants = read_implants(items, config)
    log.info(f"Read {len(implants)} implants and {len(symbiants)} symbiants")

    combos = group_implants(implants)
    matrix_rows = []
    for row_id, key in enumerate(sorted(combos), 1):
        by_ql = combos[key]
        reqs = [v for ql in IMPLANT_QLS for v in (by_ql[ql].treatment, by_ql[ql].ability)]
        matrix_rows.append((row_id, *key, by_ql[1].ability_id, *reqs))
    write_sql(implant_dir / "ImplantMatrix.sql", [
        "DROP TABLE IF EXISTS ImplantMatrix;",
        "CREATE TABLE ImplantMatrix (ID INT NOT NULL PRIMARY KEY, ShiningID INT NOT NULL, BrightID INT NOT NULL, FadedID INT NOT NULL, "
        "AbilityID INT NOT NULL, TreatQL1 INT NOT NULL, AbilityQL1 INT NOT NULL, TreatQL200 INT NOT NULL, AbilityQL200 INT NOT NULL, "
        "TreatQL201 INT NOT NULL, AbilityQL201 INT NOT NULL, TreatQL300 INT NOT NULL, AbilityQL300 INT NOT NULL);",
        "CREATE INDEX shining_idx ON ImplantMatrix(ShiningID);",
    ], "ImplantMatrix", "ID, ShiningID, BrightID, FadedID, AbilityID, TreatQL1, AbilityQL1, TreatQL200, AbilityQL200, "
       "TreatQL201, AbilityQL201, TreatQL300, AbilityQL300", matrix_rows)

    cluster_slots = sorted({(i.slot_id, cluster_id, CLUSTER_TYPE_IDS[grade])
                            for i in implants for grade, cluster_id in i.cluster_ids.items() if cluster_id})
    write_sql(implant_dir / "ClusterImplantMap.sql", [
        "DROP TABLE IF EXISTS ClusterImplantMap;",
        "CREATE TABLE ClusterImplantMap (ImplantTypeID INT NOT NULL, ClusterID INT NOT NULL, ClusterTypeID INT NOT NULL);",
    ], "ClusterImplantMap", "ImplantTypeID, ClusterID, ClusterTypeID", cluster_slots)

    write_sql(implant_dir / "implant_requirements.sql", [
        "DROP TABLE IF EXISTS implant_requirement;",
        "CREATE TABLE implant_requirement (ql INTEGER NOT NULL PRIMARY KEY, treatment INTEGER NOT NULL, ability INTEGER NOT NULL, "
        "ability_shiny INTEGER NOT NULL, ability_bright INTEGER NOT NULL, ability_faded INTEGER NOT NULL, "
        "skill_shiny INTEGER NOT NULL, skill_bright INTEGER NOT NULL, skill_faded INTEGER NOT NULL);",
    ], "implant_requirement", "ql, treatment, ability, ability_shiny, ability_bright, ability_faded, skill_shiny, skill_bright, skill_faded",
        build_requirements(implants, config), separator=", ")

    names: Dict[str, int] = {}
    for s in symbiants:
        if s.name in names:
            raise ValueError(f"Symbiants {names[s.name]} and {s.item_id} share the name '{s.name}'")
        names[s.name] = s.item_id
    symbiants.sort(key=lambda s: s.name)

    write_sql(implant_dir / "Symbiant.sql", [
        "DROP TABLE IF EXISTS Symbiant;",
        "CREATE TABLE Symbiant (ID INT NOT NULL PRIMARY KEY, Name VARCHAR(100) NOT NULL, QL INT NOT NULL, SlotID INT NOT NULL, "
        "TreatmentReq INT NOT NULL, LevelReq INT NOT NULL);",
    ], "Symbiant", "ID, Name, QL, SlotID, TreatmentReq, LevelReq",
        ((s.item_id, s.name, s.ql, s.slot_id, s.treatment, s.level) for s in symbiants))

    write_sql(implant_dir / "SymbiantAbilityMatrix.sql", [
        "DROP TABLE IF EXISTS SymbiantAbilityMatrix;",
        "CREATE TABLE SymbiantAbilityMatrix (SymbiantID INT NOT NULL, AbilityID INT NOT NULL, Amount INT NOT NULL);",
    ], "SymbiantAbilityMatrix", "SymbiantID, AbilityID, Amount",
        ((s.item_id, ability_id, amount) for s in symbiants for ability_id, amount in sorted(s.abilities.items())))

    write_sql(implant_dir / "SymbiantClusterMatrix.sql", [
        "DROP TABLE IF EXISTS SymbiantClusterMatrix;",
        "CREATE TABLE SymbiantClusterMatrix (SymbiantID INT NOT NULL, ClusterID INT NOT NULL, Amount INT NOT NULL);",
    ], "SymbiantClusterMatrix", "SymbiantID, ClusterID, Amount",
        ((s.item_id, cluster_id, amount) for s in symbiants for cluster_id, amount in sorted(s.clusters.items())))

    write_sql(implant_dir / "SymbiantProfessionMatrix.sql", [
        "DROP TABLE IF EXISTS SymbiantProfessionMatrix;",
        "CREATE TABLE SymbiantProfessionMatrix (SymbiantID INT NOT NULL, ProfessionID INT NOT NULL);",
    ], "SymbiantProfessionMatrix", "SymbiantID, ProfessionID",
        ((s.item_id, profession_id) for s in symbiants for profession_id in s.profession_ids))
