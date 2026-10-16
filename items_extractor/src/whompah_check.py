from collections import defaultdict
from dataclasses import dataclass, field
import logging
import math
from pathlib import Path
import struct
from typing import Dict, List, Optional, Set, Tuple

from src.check_helpers import Problems, check_duplicates, read_sql_rows
from src.constants import IndexRecordType
from src.rdb_file import MultiChunkReader
from src.rdb_index import IndexRecord
from src.tower_sites import read_playfield_name, read_resource

log = logging.getLogger(__name__)

WHOMPAH_PREFIX = "Whom-Pah to "
NAME_MARKER = bytes.fromhex("0000001500000021")
TELEPORT_MARKER = bytes.fromhex("000007e20000cf43")
PLAYFIELD_IDENTITY_TYPE = 100001
CITY_RADIUS = 50.0


@dataclass
class Whompah:
    playfield_id: int
    label: str
    x_coord: float
    y_coord: float
    destination_id: int


@dataclass
class Cluster:
    # Whompahs standing together in one playfield
    playfield_id: int
    whompahs: List[Whompah] = field(default_factory=list)

    def describe(self, playfield_names: Dict[int, str]) -> str:
        x_coord = sum(w.x_coord for w in self.whompahs) / len(self.whompahs)
        y_coord = sum(w.y_coord for w in self.whompahs) / len(self.whompahs)
        return f"{playfield_names.get(self.playfield_id, self.playfield_id)} at {x_coord:.0f}x{y_coord:.0f}"


@dataclass
class City:
    city_id: int
    name: str
    zone: str


def read_whompah(blob: bytes, playfield_id: int, x_coord: float, y_coord: float) -> Optional[Whompah]:
    # Name and description lengths follow the name marker, then both strings; numbers in this data are big-endian
    i = blob.find(NAME_MARKER)
    if i < 0:
        raise ValueError(f"Placed object in playfield {playfield_id} mentions a whompah but has no name")
    name_length = struct.unpack_from(">H", blob, i + len(NAME_MARKER))[0]
    start = i + len(NAME_MARKER) + 4
    name = blob[start:start + name_length].decode("latin-1")
    if not name.startswith(WHOMPAH_PREFIX):
        return None

    # Teleport spell: seven arguments, then the target's identity (playfield type and instance) and the destination playfield
    count = blob.count(TELEPORT_MARKER)
    if count == 0:
        log.info(f"Skipping '{name}' in playfield {playfield_id}: it has no teleport to a playfield")
        return None
    if count > 1:
        raise ValueError(f"'{name}' in playfield {playfield_id} has {count} teleports")
    identity_type, identity_instance, destination_id = struct.unpack_from(">iii", blob, blob.find(TELEPORT_MARKER) + len(TELEPORT_MARKER) + 28)
    if identity_type != PLAYFIELD_IDENTITY_TYPE or identity_instance & 0xFFFF != destination_id:
        raise ValueError(f"'{name}' in playfield {playfield_id} has an unexpected teleport target {(identity_type, identity_instance, destination_id)}")
    return Whompah(playfield_id, name[len(WHOMPAH_PREFIX):], x_coord, y_coord, destination_id)


def read_whompahs(data: bytes, playfield_id: int) -> List[Whompah]:
    # Object count, then objects that each start with their size; a placement in game coordinates is x and z
    whompahs: List[Whompah] = []
    count = struct.unpack_from("<I", data, 12)[0]
    pos = 16
    for _ in range(count):
        size = struct.unpack_from("<I", data, pos)[0]
        x_coord, _, y_coord = struct.unpack_from("<3f", data, pos + 28)
        blob_length = struct.unpack_from("<I", data, pos + 64)[0]
        if blob_length + 64 != size:
            raise ValueError(f"Placed object at {pos} in playfield {playfield_id} has size {size} but data length {blob_length}")
        blob = data[pos + 68:pos + 68 + blob_length]
        if WHOMPAH_PREFIX.encode() in blob:
            whompah = read_whompah(blob, playfield_id, x_coord, y_coord)
            if whompah:
                whompahs.append(whompah)
        pos += size + 4
    if pos != len(data):
        raise ValueError(f"Placed objects in playfield {playfield_id} end at {pos}, but the record has {len(data)} bytes")
    return whompahs


def cluster_whompahs(whompahs: List[Whompah]) -> List[Cluster]:
    # Whompahs within CITY_RADIUS of another whompah in the same playfield form one cluster
    clusters: List[Cluster] = []
    for w in whompahs:
        near = [c for c in clusters if c.playfield_id == w.playfield_id
                and any(math.dist((o.x_coord, o.y_coord), (w.x_coord, w.y_coord)) <= CITY_RADIUS for o in c.whompahs)]
        merged = Cluster(w.playfield_id, [w] + [o for c in near for o in c.whompahs])
        clusters = [c for c in clusters if c not in near] + [merged]
    return clusters


Ambiguous = List[Tuple[int, Whompah, List[int]]]


def resolve_routes(clusters: List[Cluster], names: Optional[Dict[int, str]] = None,
                   routes: Optional[Set[Tuple[int, int]]] = None, pending: Optional[Ambiguous] = None) -> Tuple[Set[Tuple[int, int]], Ambiguous]:
    # A whompah leads to the destination playfield's cluster that has a whompah back; when there are several, to the one
    # named on it, by the labels of resolved whompahs leading there or by its city's name, else to the one whose whompah leads here
    routes = set(routes or set())
    if pending is None:
        pending = []
        for i, c in enumerate(clusters):
            for w in c.whompahs:
                candidates = [j for j, d in enumerate(clusters) if d.playfield_id == w.destination_id
                              and any(back.destination_id == c.playfield_id for back in d.whompahs)]
                pending.append((i, w, candidates))
    while pending:
        labels: Dict[int, Set[str]] = defaultdict(set)
        for source, w, candidates in pending:
            if len(candidates) == 1:
                labels[candidates[0]].add(w.label.lower())
        unresolved: Ambiguous = []
        for source, w, candidates in pending:
            if len(candidates) > 1:
                candidates = [i for i in candidates if w.label.lower() in labels[i] or (names and names.get(i, "").lower() == w.label.lower())] or \
                             [i for i in candidates if (i, source) in routes] or candidates
            if len(candidates) == 1:
                routes.add((source, candidates[0]))
            else:
                unresolved.append((source, w, candidates))
        if len(unresolved) == len(pending):
            break
        pending = unresolved
    return routes, pending


def read_game_routes(reader: MultiChunkReader, records: List[IndexRecord]) -> Tuple[List[Cluster], Set[Tuple[int, int]], Ambiguous, Dict[int, str]]:
    whompahs: List[Whompah] = []
    playfield_names: Dict[int, str] = {}
    for record in records:
        if record.resource_type == IndexRecordType.PLAYFIELD_TYPE:
            playfield_names[record.resource_id] = read_playfield_name(read_resource(reader, record), record.resource_id)
        elif record.resource_type == IndexRecordType.PLACED_OBJECTS_TYPE:
            data = read_resource(reader, record)
            if WHOMPAH_PREFIX.encode() in data:
                whompahs += read_whompahs(data, record.resource_id)
    if not whompahs:
        raise ValueError("No whompahs found in the game data")
    clusters = cluster_whompahs(whompahs)
    routes, ambiguous = resolve_routes(clusters)
    return clusters, routes, ambiguous, playfield_names


def best_assignment(cities: List[City], clusters: List[Cluster], playfield_names: Dict[int, str], sql_routes: Set[Tuple[int, int]],
                    game_routes: Set[Tuple[int, int]], ambiguous: Ambiguous) -> Tuple[Dict[int, int], float]:
    # Cities whose zone names a playfield go to that playfield's clusters; the assignment with the fewest route differences wins,
    # counting a route that an unresolved whompah could make as a match
    by_name = {name.lower(): pf for pf, name in playfield_names.items()}
    domains: Dict[int, List[int]] = {}
    for city in cities:
        playfield = by_name.get(city.zone.lower())
        anchored = [i for i, c in enumerate(clusters) if c.playfield_id == playfield]
        domains[city.city_id] = anchored or list(range(len(clusters)))
    order = sorted(cities, key=lambda c: len(domains[c.city_id]))
    possible = game_routes | {(source, i) for source, _, candidates in ambiguous for i in candidates}

    best: Tuple[Dict[int, int], float] = ({}, math.inf)
    assigned: Dict[int, int] = {}

    def cost_of(city_id: int, cluster: int) -> int:
        cost = 0
        for other, other_cluster in assigned.items():
            cost += ((city_id, other) in sql_routes) != ((cluster, other_cluster) in possible)
            cost += ((other, city_id) in sql_routes) != ((other_cluster, cluster) in possible)
        return cost

    def search(index: int, cost: int) -> None:
        nonlocal best
        if cost >= best[1]:
            return
        if index == len(order):
            best = (dict(assigned), cost)
            return
        city_id = order[index].city_id
        used = set(assigned.values())
        for cluster in domains[city_id]:
            if cluster not in used:
                extra = cost_of(city_id, cluster)
                assigned[city_id] = cluster
                search(index + 1, cost + extra)
                del assigned[city_id]

    search(0, 0)
    return best


def check_whompah_routes(problems: Problems, reader: MultiChunkReader, records: List[IndexRecord], modules_dir: Path) -> None:
    # The routes in whompah_cities_rel must be the routes the game's whompahs make between their cities
    path = modules_dir / "whompah" / "whompah_cities.sql"
    city_rows = read_sql_rows(path, "whompah_cities", [])
    cities = [City(int(r["id"]), str(r["city_name"]), str(r["zone"])) for _, r in city_rows]  # type: ignore[arg-type]
    names = {c.city_id: c.name for c in cities}
    check_duplicates(problems, path, city_rows, ["id"])
    rel_rows = read_sql_rows(path, "whompah_cities_rel", [])
    check_duplicates(problems, path, rel_rows, ["city1_id", "city2_id"])
    sql_routes: Set[Tuple[int, int]] = set()
    for line_number, r in rel_rows:
        unknown = [r[c] for c in ("city1_id", "city2_id") if r[c] not in names]
        if unknown:
            problems.add(f"{path}:{line_number}", f"route uses city ids {unknown}, which are not in whompah_cities")
        else:
            sql_routes.add((int(r["city1_id"]), int(r["city2_id"])))  # type: ignore[arg-type]

    clusters, game_routes, ambiguous, playfield_names = read_game_routes(reader, records)
    if len(clusters) != len(cities):
        problems.add(str(path), f"lists {len(cities)} cities, but the game has whompahs in {len(clusters)} places: "
                     + "; ".join(c.describe(playfield_names) for c in clusters))
        if len(clusters) < len(cities):
            return

    # Match cities to whompah places, then settle the whompahs only a city's name tells apart
    assignment, _ = best_assignment(cities, clusters, playfield_names, sql_routes, game_routes, ambiguous)
    if not assignment:
        problems.add(str(path), "cities cannot be matched to the game's whompah places; more cities name a playfield than it has whompah places")
        return
    city_of = {i: city_id for city_id, i in assignment.items()}
    game_routes, ambiguous = resolve_routes(clusters, {i: names[c] for i, c in city_of.items()}, game_routes, ambiguous)
    for source, w, candidates in ambiguous:
        problems.add("game data", f"cannot tell where the whompah to '{w.label}' in {clusters[source].describe(playfield_names)} leads; "
                     f"it could be {[names.get(city_of.get(i, -1), clusters[i].describe(playfield_names)) for i in candidates]}")

    differences = [f"route {names[a]} -> {names[b]} has no whompah in the game"
                   for a, b in sorted(sql_routes) if (assignment[a], assignment[b]) not in game_routes]
    differences += [f"the game's whompah from {names[city_of[a]]} to {names[city_of[b]]} is not a route"
                    for a, b in sorted(game_routes) if a in city_of and b in city_of and (city_of[a], city_of[b]) not in sql_routes]
    if differences:
        matches = "; ".join(f"{names[c]} = {clusters[i].describe(playfield_names)}" for c, i in sorted(assignment.items()))
        log.info(f"Closest match of cities to whompah places: {matches}")
    for message in differences:
        problems.add(str(path), message)
