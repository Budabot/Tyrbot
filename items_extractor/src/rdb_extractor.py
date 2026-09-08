from dataclasses import dataclass, field
import logging
import struct
from typing import Dict, List, Any, Optional

from src.function_sets import FunctionSets
from src.rdb_file import MultiChunkReader
from src.rdb_index import IndexRecord

log = logging.getLogger(__name__)


def int3f1(n: int) -> int:
    return (n // 1009) - 1


@dataclass
class FunctionRequirement:
    required_attribute_number: int
    required_attribute_value: int
    required_attribute_operator: int


@dataclass
class Function:
    function_num: int
    hits: int
    delay: int
    target: int
    requirements: List[FunctionRequirement]
    params: List[str]


@dataclass
class Event:
    event_type: int
    functions: List[Function]


@dataclass
class AttackDefense:
    key_type: int
    stat_number: int
    stat_value: int


@dataclass
class Criteria:
    criteria1: int
    criteria2: int
    criteria3: int


@dataclass
class RDBItem:
    id: int
    name: str
    description: str
    attributes: Dict[int, int]
    attack_defense_list: List[AttackDefense] = field(default_factory=list)
    events: List[Event] = field(default_factory=list)
    criteria_list: List[Criteria] = field(default_factory=list)


class BinaryReader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0
        self.length = len(data)

    def remaining(self) -> int:
        return self.length - self.pos

    def skip(self, n: int):
        self.pos = min(self.pos + n, self.length)

    def skip_all(self):
        self.pos = self.length

    def read_u32(self) -> int:
        if self.pos + 4 > self.length:
            raise EOFError(f"End of data reached: pos {self.pos} + 4 > {self.length}")
        v = struct.unpack_from("<I", self.data, self.pos)[0]
        self.pos += 4
        return v

    def read_i32(self) -> int:
        if self.pos + 4 > self.length:
            raise EOFError(f"End of data reached: pos {self.pos} + 4 > {self.length}")
        v = struct.unpack_from("<i", self.data, self.pos)[0]
        self.pos += 4
        return v

    def read_u16(self) -> int:
        if self.pos + 2 > self.length:
            raise EOFError(f"End of data reached: pos {self.pos} + 2 > {self.length}")
        v = struct.unpack_from("<H", self.data, self.pos)[0]
        self.pos += 2
        return v

    def read_bytes(self, n: int) -> bytes:
        if self.pos + n > self.length:
            raise EOFError(f"End of data reached: pos {self.pos} + {n} > {self.length}")
        v = self.data[self.pos:self.pos + n]
        self.pos += n
        return v


class RDBExtractor:
    def __init__(self, function_sets: FunctionSets):
        self.function_sets = function_sets

    def read_item(self, reader: MultiChunkReader, record: IndexRecord, extract_functions: bool = True) -> RDBItem:
        # Read header (magic: 2 bytes, length: 4 bytes)
        hdr = reader.read_item_bytes(record.offset, 6)
        if len(hdr) < 6:
            raise EOFError(f"Failed to read header at offset {record.offset}")
        total_len = struct.unpack_from("<I", hdr, 2)[0]
        remaining = total_len - 6
        payload = reader.read_item_bytes(record.offset + 6, remaining)
        b_reader = BinaryReader(payload)

        # Skip 44 bytes fixed item header
        b_reader.skip(44)

        # Attributes
        num_attributes = int3f1(b_reader.read_u32())
        attributes: Dict[int, int] = {}
        for _ in range(num_attributes):
            attr_id = b_reader.read_u32()
            attr_val = b_reader.read_u32()
            attributes[attr_id] = attr_val

        # Skip 8 bytes
        b_reader.skip(8)

        # Strings
        name_len = b_reader.read_u16()
        desc_len = b_reader.read_u16()
        name = b_reader.read_bytes(name_len).decode("latin1", errors="replace")
        desc = b_reader.read_bytes(desc_len).decode("latin1", errors="replace")

        events: List[Event] = []
        attack_defense_list: List[AttackDefense] = []
        criteria_list: List[Criteria] = []
        old_set_type = -1

        if extract_functions:
            while b_reader.remaining() > 12:
                set_type = b_reader.read_u32()
                try:
                    if set_type == 2:
                        ev = self._process_event(b_reader)
                        events.append(ev)
                    elif set_type == 4:
                        self._parse_attack_defense(b_reader, attack_defense_list)
                    elif set_type == 5:
                        b_reader.skip(16)
                    elif set_type == 6:
                        header = b_reader.read_u32()
                        pairs = int3f1(b_reader.read_u32())
                        b_reader.skip(pairs * 8)
                    elif set_type == 14:
                        pass
                    elif set_type == 22:
                        self._parse_criteria(b_reader, criteria_list)
                    elif set_type == 23:
                        header = b_reader.read_u32()
                        count = int3f1(b_reader.read_u32())
                        b_reader.skip(count * 13)
                    elif set_type == 20:
                        b_reader.skip(4)
                        count = int3f1(b_reader.read_u32())
                        for _ in range(count):
                            b_reader.skip(4)
                            count2 = int3f1(b_reader.read_u32())
                            b_reader.skip(count2 * 4)
                    elif set_type == 19:
                        b_reader.skip(16)
                    elif set_type == 37:
                        count = int3f1(b_reader.read_u32())
                        b_reader.skip(4)
                        b_reader.skip(count * 16)
                    elif set_type == 136:
                        count = int3f1(b_reader.read_u32())
                        b_reader.skip(count * 12)
                    elif set_type == 1035:
                        b_reader.skip(8)
                    else:
                        log.debug(f"Record {record.resource_id}: breaking for unknown setType {set_type} (remaining {b_reader.remaining()})")
                        b_reader.skip_all()
                    old_set_type = set_type
                except Exception as e:
                    log.debug(f"Failed parsing setType {set_type} for record {record.resource_id} (last setType: {old_set_type}, remaining: {b_reader.remaining()}): {e}")
                    b_reader.skip_all()

        return RDBItem(record.resource_id, name, desc, attributes, attack_defense_list, events, criteria_list)

    def _process_event(self, reader: BinaryReader) -> Event:
        event_num = reader.read_u32()
        func_count = int3f1(reader.read_u32())
        functions: List[Function] = []

        for _ in range(func_count):
            func_num = reader.read_u32()
            reader.skip(8)
            req_count = reader.read_u32()
            reqs: List[FunctionRequirement] = []
            for _ in range(req_count):
                r_num = reader.read_u32()
                r_val = reader.read_u32()
                r_op = reader.read_u32()
                reqs.append(FunctionRequirement(r_num, r_val, r_op))

            hits = reader.read_u32()
            delay = reader.read_u32()
            target = reader.read_u32()
            reader.skip(4)

            params: List[str] = []
            for count, p_type in self.function_sets.get_params_by_id(func_num):
                if p_type == "n":
                    for _ in range(count):
                        params.append(str(reader.read_i32()))
                elif p_type == "h":
                    for _ in range(count):
                        params.append(reader.read_bytes(4).decode("latin1", errors="replace"))
                elif p_type == "s":
                    for _ in range(count):
                        s_size = reader.read_u32()
                        params.append(reader.read_bytes(s_size).decode("latin1", errors="replace").strip())
                elif p_type == "x":
                    reader.skip(count)

            functions.append(Function(func_num, hits, delay, target, reqs, params))

        return Event(event_num, functions)

    def _parse_attack_defense(self, reader: BinaryReader, out_list: List[AttackDefense]):
        header = reader.read_u32()
        max_sets = int3f1(reader.read_u32())
        for _ in range(max_sets):
            key_type = reader.read_u32()
            set_count = int3f1(reader.read_u32())
            for _ in range(set_count):
                stat_number = reader.read_u32()
                stat_val = reader.read_u32()
                out_list.append(AttackDefense(key_type, stat_number, stat_val))

    def _parse_criteria(self, reader: BinaryReader, out_list: List[Criteria]):
        header = reader.read_u32()
        reader.skip(8)
        criteria_count = int3f1(reader.read_u32())
        for _ in range(criteria_count):
            c1 = reader.read_u32()
            c2 = reader.read_u32()
            c3 = reader.read_u32()
            out_list.append(Criteria(c1, c2, c3))
