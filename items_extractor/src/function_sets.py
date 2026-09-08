import configparser
import re
from pathlib import Path
from typing import List, Tuple, Dict


class FunctionSets:
    def __init__(self, config_path: str):
        self.params_by_id: Dict[int, List[Tuple[int, str]]] = {}
        self._load(config_path)

    def _load(self, config_path: str):
        config = configparser.ConfigParser()
        # Read file with UTF-8 / latin1 fallback
        with open(config_path, "r", encoding="utf-8", errors="replace") as f:
            config.read_file(f)

        # Iterate sections sorted by key to let later version sections override earlier ones
        raw_map: Dict[int, str] = {}
        for section in sorted(config.sections()):
            for key, val in config.items(section):
                # clean key and val
                func_id = int(key.strip())
                val = val.strip().strip('"').strip("'")
                raw_map[func_id] = val

        regex = re.compile(r"(\d+)([nhsx])")
        for func_id, val in raw_map.items():
            parsed_params = []
            for part in val.split(","):
                part = part.strip()
                m = regex.search(part)
                if m:
                    parsed_params.append((int(m.group(1)), m.group(2)))
                else:
                    raise ValueError(f"'{part}' does not conform to expected format for function sets")
            self.params_by_id[func_id] = parsed_params

    def get_params_by_id(self, func_id: int) -> List[Tuple[int, str]]:
        return self.params_by_id.get(func_id, [])
