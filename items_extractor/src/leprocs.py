from collections import Counter, OrderedDict
from dataclasses import dataclass
import logging
from pathlib import Path
import re
from typing import Dict, List, Optional, Set, Tuple

from src.constants import GENERATED_COMMENT
from src.dyna import CaseSensitiveConfigParser
from src.perks import PROFESSION_NAME_CATEGORY, read_perk_chains
from src.rdb_extractor import Function, RDBItem
from src.rdb_file import MultiChunkReader
from src.rdb_index import IndexRecord
from src.research import RESEARCH_CATEGORY
from src.skills import SKILL_NAME_CATEGORY, read_text_category, sql_string

log = logging.getLogger(__name__)

NANO_STRAIN_CATEGORY = 2009
USE_EVENT = 0
WEAR_EVENT = 14
GRANT_ACTION_FUNCTION = 53182
CAST_NANO_FUNCTION = 53051
TEAM_CAST_NANO_FUNCTION = 53066
AREA_CAST_NANO_FUNCTION = 53087
OFFENSIVE_PROC_FUNCTION = 53227
DEFENSIVE_PROC_FUNCTION = 53224
MODIFY_FUNCTIONS = (53045, 53012, 53110)
HIT_FUNCTION = 53002
RESTRICT_ACTION_FUNCTION = 53068
TAUNT_FUNCTION = 53117
RESIST_STRAIN_FUNCTION = 53162
REMOVE_STRAIN_FUNCTION = 53236
REDUCE_STRAIN_FUNCTION = 53177
# Visual effects, chat messages and a function with no parameters
SILENT_FUNCTIONS = (53057, 53044, 53153)
RESTRICT_MOVEMENT = 4
DURATION_STAT = 8
# Chance to break on hit, on nano damage and on debuff
BREAK_STATS = (422, 385, 386)
SELF_TARGETS = (1, 2)
OTHER_TARGETS = (3, 14)
MAX_CAST_DEPTH = 3
PROC_TYPE = re.compile(r"\bType (\d+) action\b")
DAMAGE_WORD = re.compile(r"(Imp/Proj|Projectile|Proj\.?|Melee/ma|Melee|Energy|Chemical|Chem\.?|Radiation|Rad\.?|Cold|Fire|Poison|Disease|Nano)")


@dataclass
class LeProcConfig:
    stat_groups: List[Tuple[str, Set[int]]]


@dataclass
class LeProc:
    profession: str
    name: str
    research_name: str
    research_level: int
    proc_type: str
    chance: str
    modifiers: str
    duration: str
    trigger: str


def read_leproc_config(path: Path) -> LeProcConfig:
    parser = CaseSensitiveConfigParser(inline_comment_prefixes=(";",), allow_no_value=True)
    with open(path, encoding="utf-8") as f:
        parser.read_file(f)
    groups = [(label, {int(s) for s in value.split(",")}) for label, value in parser.items("leproc_stat_groups")]
    return LeProcConfig(groups)


def seconds(centiseconds: int) -> str:
    return "%gs" % (centiseconds / 100)


class ModifierText:
    # Describes a proc's effect nano and the nanos it casts
    def __init__(self, nanos: Dict[int, RDBItem], stat_names: Dict[int, str], strain_names: Dict[int, str], config: LeProcConfig):
        self.nanos = nanos
        self.stat_names = stat_names
        self.strain_names = strain_names
        self.config = config
        families: Dict[str, Set[int]] = {}
        for stat in stat_names:
            family = self.family(stat)
            if family:
                families.setdefault(family, set()).add(stat)
        self.families = {f: members for f, members in families.items() if len(members) >= 3}

    def stat(self, stat: int) -> str:
        if stat not in self.stat_names:
            raise ValueError(f"Stat {stat} has no name in category {SKILL_NAME_CATEGORY}")
        return self.stat_names[stat]

    def family(self, stat: int) -> Optional[str]:
        # Stat name without its damage-type word; None if it has none
        name = self.stat_names[stat]
        key = DAMAGE_WORD.sub("", name, count=1)
        return None if key == name else re.sub(r"\s+", " ", key).strip()

    def nano(self, nano_id: int) -> RDBItem:
        if nano_id not in self.nanos:
            raise ValueError(f"Nano {nano_id} was not read")
        return self.nanos[nano_id]

    def collapse(self, mods: Dict[int, int]) -> List[str]:
        # Named stat groups and damage-type families sharing one amount are shown once
        out: List[str] = []
        left = dict(mods)
        for label, members in self.config.stat_groups:
            amounts = {left.get(s) for s in members}
            if len(amounts) == 1 and None not in amounts:
                out.append("%s %+d" % (label, mods[next(iter(members))]))
                for s in members:
                    del left[s]

        by_family: Dict[str, List[int]] = {}
        for s in left:
            family = self.family(s) if s in self.stat_names else None
            if family in self.families:
                by_family.setdefault(family, []).append(s)
        for family, family_stats in by_family.items():
            amount, count = Counter(left[s] for s in family_stats).most_common(1)[0]
            if count < 3:
                continue
            same = [s for s in family_stats if left[s] == amount]
            out.append("%s %+d" % (family if len(same) == len(family_stats) else "other " + family, amount))
            for s in same:
                del left[s]

        out += ["%s %+d" % (self.stat(s), a) for s, a in left.items()]
        return out

    def target(self, f: Function, nano: RDBItem) -> str:
        if f.target in SELF_TARGETS:
            return "Self"
        if f.target in OTHER_TARGETS:
            return "Target"
        raise ValueError(f"Nano {nano.id} function {f.function_num} has unknown target {f.target}")

    def strain(self, value: str) -> str:
        strain = int(value)
        if strain not in self.strain_names:
            raise ValueError(f"Nano strain {strain} has no name in category {NANO_STRAIN_CATEGORY}")
        return self.strain_names[strain]

    def describe(self, nano_id: int, depth: int = 0, scope: Optional[str] = None) -> str:
        nano = self.nano(nano_id)
        duration = nano.attributes.get(DURATION_STAT, 0)
        parts: List[str] = []
        mods: Dict[int, int] = OrderedDict()
        mods_target = ""
        for f in (f for e in nano.events for f in e.functions):
            n, p = f.function_num, f.params
            who = scope or self.target(f, nano)
            # Hits beyond the nano's duration never land
            hits = f.hits if not (duration and f.delay) or f.hits <= duration // f.delay + 1 else duration // f.delay
            ticks = ", %d hits %s apart" % (hits, seconds(f.delay)) if hits > 1 else ""
            if n in MODIFY_FUNCTIONS:
                mods[int(p[0])] = int(p[1])
                mods_target = who
            elif n == HIT_FUNCTION:
                low, high = sorted((abs(int(p[1])), abs(int(p[2]))))
                amount = "%d" % low if low == high else "%d-%d" % (low, high)
                if int(p[1]) < 0:
                    kind = self.stat(int(p[3])).replace(" AC", "") + " damage" if int(p[3]) else "damage"
                else:
                    kind = "heal"
                total = ""
                if hits > 1:
                    total = " (total %s)" % ("%d" % (low * hits) if low == high else "%d-%d" % (low * hits, high * hits))
                parts.append("%s %s %s %s%s%s" % (who, self.stat(int(p[0])), amount, kind, ticks, total))
            elif n == RESTRICT_ACTION_FUNCTION:
                text = "%s root" % who if int(p[0]) == RESTRICT_MOVEMENT else "%s restrict action %s" % (who, p[0])
                parts.append(text + (" for %s" % seconds(duration) if duration else ""))
            elif n == TAUNT_FUNCTION:
                parts.append("%s taunt %s" % (who, p[0]))
            elif n == RESIST_STRAIN_FUNCTION:
                parts.append("%s resist %s %s%%" % (who, self.strain(p[0]), p[1]))
            elif n == REMOVE_STRAIN_FUNCTION:
                parts.append("%s remove %s" % (who, self.strain(p[0])))
            elif n == REDUCE_STRAIN_FUNCTION:
                parts.append("%s reduce %s duration by %ss" % (who, self.strain(p[0]), p[1]))
            elif n in (CAST_NANO_FUNCTION, TEAM_CAST_NANO_FUNCTION, AREA_CAST_NANO_FUNCTION):
                cast = int(p[0])
                if cast == nano_id:
                    continue
                if depth >= MAX_CAST_DEPTH:
                    raise ValueError(f"Nano {nano_id} casts nanos more than {MAX_CAST_DEPTH} deep")
                cast_scope = "Team" if n == TEAM_CAST_NANO_FUNCTION else "Area %sm" % p[1] if n == AREA_CAST_NANO_FUNCTION else who
                parts.append(self.describe(cast, depth + 1, cast_scope))
            elif n not in SILENT_FUNCTIONS:
                raise ValueError(f"Nano {nano_id} uses function {n}, which has no description")

        if mods:
            parts.insert(0, "%s %s" % (mods_target, ", ".join(self.collapse(mods))))
        # Instant nanos that only cast another nano never last long enough to break
        breaks = [nano.attributes.get(s, 0) for s in BREAK_STATS]
        if any(breaks) and duration > 1:
            parts.append("Break chance %d%% on hit, %d%% on nano damage, %d%% on debuff" % tuple(breaks))
        text = "; ".join(x for x in parts if x)
        return text + (" for %s" % seconds(duration) if duration and mods else "")

    def duration(self, nano_id: int, depth: int = 0) -> int:
        # Longest duration in the cast chain; one-centisecond nanos that only cast another don't count
        nano = self.nano(nano_id)
        own = nano.attributes.get(DURATION_STAT, 0)
        best = own if own > 1 else 0
        for f in (f for e in nano.events for f in e.functions):
            if f.function_num in (CAST_NANO_FUNCTION, TEAM_CAST_NANO_FUNCTION, AREA_CAST_NANO_FUNCTION) and int(f.params[0]) != nano_id:
                if depth >= MAX_CAST_DEPTH:
                    raise ValueError(f"Nano {nano_id} casts nanos more than {MAX_CAST_DEPTH} deep")
                best = max(best, self.duration(int(f.params[0]), depth + 1))
        return best


def functions(item: RDBItem, event_type: int, function_nums: Tuple[int, ...]) -> List[Function]:
    return [f for e in item.events if e.event_type == event_type for f in e.functions if f.function_num in function_nums]


def single(found: List, what: str):
    if len(found) != 1:
        raise ValueError(f"Expected one {what}, found {len(found)}")
    return found[0]


def read_leprocs(reader: MultiChunkReader, records: List[IndexRecord], items: List[RDBItem], nanos: List[RDBItem],
                 text_mdb: Path, config: LeProcConfig) -> List[LeProc]:
    profession_names = read_text_category(text_mdb, PROFESSION_NAME_CATEGORY)
    text = ModifierText({n.id: n for n in nanos}, read_text_category(text_mdb, SKILL_NAME_CATEGORY),
                        read_text_category(text_mdb, NANO_STRAIN_CATEGORY), config)
    items_map = {item.id: item for item in items}

    procs: List[LeProc] = []
    for chain in read_perk_chains(reader, records, RESEARCH_CATEGORY):
        missing = [p.item_id for p in chain if p.item_id not in items_map]
        if missing:
            raise ValueError(f"Research {chain[0].perk_id} uses items {missing}, which were not read")
        research_name = items_map[chain[0].item_id].name.strip()
        mask = chain[0].profession_mask
        if not mask:
            log.info(f"Skipping research line '{research_name}': not a profession research line")
            continue
        professions = [prof for prof in profession_names if mask & (1 << prof)]
        profession = single(professions, f"profession for research line '{research_name}' (mask {mask})")

        # Research levels grant an action item that casts the proc nano
        for level, p in enumerate(chain, 1):
            for grant in functions(items_map[p.item_id], WEAR_EVENT, (GRANT_ACTION_FUNCTION,)):
                action_id = int(grant.params[3])
                if action_id not in items_map:
                    raise ValueError(f"Research '{research_name}' level {level} grants item {action_id}, which was not read")
                action = items_map[action_id]
                cast = single(functions(action, USE_EVENT, (CAST_NANO_FUNCTION,)), f"nano cast by action {action_id}")
                proc_nano = text.nano(int(cast.params[0]))
                proc = single(functions(proc_nano, USE_EVENT, (OFFENSIVE_PROC_FUNCTION, DEFENSIVE_PROC_FUNCTION)),
                              f"proc in nano {proc_nano.id}")
                proc_type = PROC_TYPE.search(proc_nano.description)
                if not proc_type:
                    raise ValueError(f"Nano {proc_nano.id} description doesn't name its action type")
                effect_id = int(proc.params[1])
                duration = text.duration(effect_id)
                procs.append(LeProc(
                    profession=profession_names[profession],
                    name=action.name.strip(),
                    research_name=research_name,
                    research_level=level,
                    proc_type="Type " + proc_type.group(1),
                    chance=proc.params[0] + "%",
                    modifiers=text.describe(effect_id),
                    duration=seconds(duration) if duration else "",
                    trigger="Offensive" if proc.function_num == OFFENSIVE_PROC_FUNCTION else "Defensive",
                ))

    procs.sort(key=lambda r: (r.profession, r.research_name, r.research_level, r.name))
    return procs


def write_leprocs_sql(reader: MultiChunkReader, records: List[IndexRecord], items: List[RDBItem], nanos: List[RDBItem],
                      text_mdb: Path, config_path: Path, alien_dir: Path):
    procs = read_leprocs(reader, records, items, nanos, text_mdb, read_leproc_config(config_path))
    path = alien_dir / "leprocs.sql"
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(GENERATED_COMMENT)
        f.write("DROP TABLE IF EXISTS leprocs;\n")
        f.write("CREATE TABLE leprocs ( profession varchar(20) NOT NULL, name varchar(50) NOT NULL, research_name varchar(50) DEFAULT NULL, "
                "research_lvl INT NOT NULL, proc_type char(6) DEFAULT NULL, chance varchar(20) DEFAULT NULL, modifiers varchar(255) NOT NULL, "
                "duration varchar(20) NOT NULL, proc_trigger varchar(20) NOT NULL );\n")
        for r in procs:
            values = ", ".join([sql_string(r.profession), sql_string(r.name), sql_string(r.research_name), str(r.research_level),
                                sql_string(r.proc_type), sql_string(r.chance), sql_string(r.modifiers), sql_string(r.duration),
                                sql_string(r.trigger)])
            f.write("INSERT INTO leprocs (profession, name, research_name, research_lvl, proc_type, chance, modifiers, duration, proc_trigger) "
                    f"VALUES({values});\n")
    log.info(f"Wrote {len(procs)} LE procs to {path}")
