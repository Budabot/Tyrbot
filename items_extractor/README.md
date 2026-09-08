# Anarchy Online ItemsExtractor (Python)

A Python port of the Budabot ItemsExtractor for Anarchy Online resource databases (`ResourceDatabase.idx`, `ResourceDatabase.dat*`).

## Features
- Pure Python 3 using standard library modules (`sqlite3`, `struct`, `configparser`, `argparse`, `logging`).
- High throughput in-memory buffered index reader and item extraction.
- In-memory SQLite matching and pairing engine.
- Generates 4 SQL dump files:
  - `aodb{version}.sql`
  - `weapon_attributes{version}.sql`
  - `item_buffs{version}.sql`
  - `item_types{version}.sql`
- Dual console and file logging (`extractor.log`) enabled by default at `DEBUG` level for post-run analysis.

## Requirements
- Python 3.8+ (no third-party pip dependencies required)

## Usage

### Local Python
```cmd
python extract.py -d "C:\Funcom\Anarchy Online"
```

### Docker
```cmd
docker run --rm -v "C:\Funcom\Anarchy Online:/ao:ro" -v "%cd%":/app -w /app python:3 python extract.py -d /ao
```

### Logging Options
- Default log file is `<output_dir>/extractor.log`.
- `-l`, `--log-file <path>`: Custom log file path.
- `--no-log-file`: Disable writing log to disk.
- `--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}`: Set logging level (default: `DEBUG`).
- `-q`, `--quiet`: Set logging level to `INFO`.
- `-v`, `--verbose`: Enable debug logging (default).
