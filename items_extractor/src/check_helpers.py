import logging
from pathlib import Path
import re
from typing import Dict, Iterable, List, Sequence, Tuple, Union

log = logging.getLogger(__name__)

SqlValue = Union[int, float, str, None]

INSERT_LINE = re.compile(r"^INSERT INTO (\w+)\s*(?:\(([^)]*)\))?\s*VALUES\s*\((.*)\);\s*$", re.IGNORECASE)
SQL_TOKEN = re.compile(r"\s*('(?:[^']|'')*'|-?\d*\.\d+|-?\d+|NULL)\s*(,|$)", re.IGNORECASE)


class Problems:
    # Problems found by the checks, each logged as it is found
    def __init__(self) -> None:
        self.count = 0

    def add(self, source: str, message: str) -> None:
        self.count += 1
        log.error(f"{source}: {message}")


def parse_values(text: str, path: Path, line_number: int) -> List[SqlValue]:
    values: List[SqlValue] = []
    pos = 0
    while pos < len(text):
        match = SQL_TOKEN.match(text, pos)
        if not match or match.end() == pos:
            raise ValueError(f"{path}:{line_number} has a value that cannot be read: {text[pos:]}")
        token = match.group(1)
        if token.startswith("'"):
            values.append(token[1:-1].replace("''", "'"))
        elif token.upper() == "NULL":
            values.append(None)
        elif "." in token:
            values.append(float(token))
        else:
            values.append(int(token))
        pos = match.end()
    return values


def read_sql_rows(path: Path, table: str, columns: Sequence[str]) -> List[Tuple[int, Dict[str, SqlValue]]]:
    # Rows of one table's INSERT statements with their line numbers; rows without a column list use the given order
    rows: List[Tuple[int, Dict[str, SqlValue]]] = []
    with open(path, encoding="utf-8") as f:
        for line_number, line in enumerate(f, 1):
            if not line.upper().startswith("INSERT INTO"):
                continue
            match = INSERT_LINE.match(line.strip())
            if not match:
                raise ValueError(f"{path}:{line_number} is an INSERT that cannot be read")
            if match.group(1).lower() != table.lower():
                continue
            names = [c.strip() for c in match.group(2).split(",")] if match.group(2) else list(columns)
            values = parse_values(match.group(3), path, line_number)
            if len(values) != len(names):
                raise ValueError(f"{path}:{line_number} has {len(values)} values for {len(names)} columns")
            rows.append((line_number, dict(zip(names, values))))
    if not rows:
        raise ValueError(f"No {table} rows found in {path}")
    return rows


def check_duplicates(problems: Problems, path: Path, rows: List[Tuple[int, Dict[str, SqlValue]]], key: Iterable[str]) -> None:
    columns = list(key)
    first_lines: Dict[Tuple[SqlValue, ...], int] = {}
    for line_number, row in rows:
        value = tuple(row[c] for c in columns)
        if value in first_lines:
            problems.add(f"{path}:{line_number}", f"repeats line {first_lines[value]}: {dict(zip(columns, value))}")
        else:
            first_lines[value] = line_number
