# Anarchy Online ItemsExtractor (Python)

A Python port of the Budabot ItemsExtractor for Anarchy Online resource databases (`ResourceDatabase.idx`, `ResourceDatabase.dat*`).

## Features
- Pure Python 3 using standard library modules (`sqlite3`, `struct`, `configparser`, `argparse`, `logging`).
- High throughput in-memory buffered index reader and item extraction.
- In-memory SQLite matching and pairing engine.
- Generates 5 SQL dump files:
  - `aodb{version}.sql`
  - `weapon_attributes{version}.sql`
  - `item_buffs{version}.sql`
  - `item_types{version}.sql`
  - `skills{version}.sql`: every stat in `item_buffs` that has a skill name in the game's `text.mdb` (category 2003), with common names from the `[skill_common_names]` section of `config/extractor.cfg`.
    - Buffed stats with no skill name are left out and logged.
    - A stat in `[skill_common_names]` that is not in `skills.sql` stops extraction.
- Regenerates `modules/standard/tower/tower_site_bounds.sql` from the game's land control districts.
  - Each district is matched to a `tower_site.sql` row by playfield and centre (`x_coord`, `y_coord`); the row supplies the site number.
  - The district's name and QL range must equal the row's, and every `tower_site.sql` row must match a district, otherwise extraction stops.
  - Land control districts with no `tower_site.sql` row are skipped and logged as warnings.
- Regenerates the implant module's `ImplantMatrix.sql`, `ClusterImplantMap.sql`, `implant_requirements.sql`, `Symbiant.sql`, `SymbiantAbilityMatrix.sql`, `SymbiantClusterMatrix.sql` and `SymbiantProfessionMatrix.sql` from the game's implant and symbiant items.
  - The tables use the game's ids for slots, abilities, professions and clusters; `ImplantType.sql`, `Ability.sql`, `Profession.sql` and `Cluster.sql` list the valid ones.
  - The `[implant_excluded_items]` section of `config/extractor.cfg` lists implant items to leave out.
  - A slot, ability, profession or cluster stat missing from those tables, or an implant that doesn't fit the expected QL 1/200/201/300 set, stops extraction.
  - `Symbiant.ID` is the symbiant's item id.
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

### Tower Site Options
- `-t`, `--tower-dir <path>`: Directory containing `tower_site.sql`, where `tower_site_bounds.sql` is written (default: `../modules/standard/tower`).

### Implant Options
- `-i`, `--implant-dir <path>`: Directory where the implant SQL files are written (default: `../modules/standard/implant/sql`).

### Logging Options
- Default log file is `<output_dir>/extractor.log`.
- `-l`, `--log-file <path>`: Custom log file path.
- `--no-log-file`: Disable writing log to disk.
- `--log-level {DEBUG,INFO,WARNING,ERROR,CRITICAL}`: Set logging level (default: `DEBUG`).
- `-q`, `--quiet`: Set logging level to `INFO`.
- `-v`, `--verbose`: Enable debug logging (default).
