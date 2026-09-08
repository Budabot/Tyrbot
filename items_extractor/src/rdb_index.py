from dataclasses import dataclass
import logging
import struct
from typing import List

log = logging.getLogger(__name__)


@dataclass
class IndexRecord:
    resource_type: int
    resource_id: int
    offset: int


def read_index_file(index_file_path: str) -> List[IndexRecord]:
    log.info("Buffering index file into memory...")
    with open(index_file_path, "rb") as f:
        data = f.read()
    log.info(f"Buffered {len(data)} bytes into memory. Parsing index records...")

    data_start = struct.unpack_from("<I", data, 72)[0]
    records: List[IndexRecord] = []
    curr = data_start

    while curr != 0:
        pos = curr
        next_block, prev_block, count = struct.unpack_from("<IIH", data, pos)
        rec_pos = pos + 28
        for _ in range(count):
            high, low = struct.unpack_from("<II", data, rec_pos)
            offset = (high << 32) + low
            res_type, res_id = struct.unpack_from(">ii", data, rec_pos + 8)
            records.append(IndexRecord(res_type, res_id, offset))
            rec_pos += 16
        curr = next_block

    log.info(f"Successfully parsed {len(records)} index records.")
    return records
