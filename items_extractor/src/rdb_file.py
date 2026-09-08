import os
from pathlib import Path
from typing import List, Tuple


class MultiChunkReader:
    def __init__(self, file_paths: List[str]):
        self.file_paths = file_paths
        self.files: List[Tuple[any, int]] = []
        for path in file_paths:
            f = open(path, "rb")
            f_len = os.path.getsize(path)
            self.files.append((f, f_len))

    def get_file_and_offset(self, pos: int):
        for f, f_len in self.files:
            if pos > f_len:
                pos = pos - f_len + 4096
            else:
                return f, pos
        raise EOFError(f"Offset {pos} exceeds total database size")

    def read_item_bytes(self, offset: int, length: int) -> bytes:
        f, local_offset = self.get_file_and_offset(offset)
        f.seek(local_offset)
        return f.read(length)

    def close(self):
        for f, _ in self.files:
            try:
                f.close()
            except Exception:
                pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


def find_database_files(ao_path: str) -> List[str]:
    db_dir = Path(ao_path) / "cd_image" / "data" / "db"
    if not db_dir.is_dir():
        return []
    files = [
        str(p.resolve())
        for p in db_dir.iterdir()
        if p.is_file() and p.name.startswith("ResourceDatabase.dat")
    ]
    return sorted(files)
