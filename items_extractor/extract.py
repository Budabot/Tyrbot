import argparse
import logging
import os
from pathlib import Path
import sys
import time

from typing import List, Optional, Union

from src.constants import IndexRecordType
from src.dyna import write_dyna_sql
from src.function_sets import FunctionSets
from src.id_matcher import IdMatcher
from src.implants import write_implant_sql
from src.perks import write_perks_sql
from src.rdb_extractor import RDBExtractor
from src.rdb_file import MultiChunkReader, find_database_files
from src.rdb_index import read_index_file
from src.research import write_research_sql
from src.tower_sites import write_tower_site_bounds
from src.trickle import write_trickle_sql

log = logging.getLogger("ItemsExtractor")


def setup_logging(
    log_file: Optional[Union[str, Path]] = "extractor.log",
    level: int = logging.DEBUG,
    console_level: Optional[int] = None,
):
    handlers: List[logging.Handler] = []

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level if console_level is None else console_level)
    console_handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s %(levelname)-5s [%(threadName)s] (%(filename)s:%(lineno)d) - %(message)s",
            datefmt="%H:%M:%S",
        )
    )
    handlers.append(console_handler)

    # File handler
    if log_file:
        log_path = Path(log_file).resolve()
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(str(log_path), mode="w", encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(
            logging.Formatter(
                fmt="%(asctime)s %(levelname)-5s [%(threadName)s] (%(filename)s:%(lineno)d) - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        handlers.append(file_handler)

    logging.basicConfig(level=level, handlers=handlers, force=True)


def main():
    parser = argparse.ArgumentParser(description="Anarchy Online ItemsExtractor in Python")
    parser.add_argument("-d", "--dir", dest="ao_path", required=True, help="Path to Anarchy Online directory")
    parser.add_argument("--items-dir", dest="items_dir", default=None,
                        help="Path to the items module's SQL directory (default: ../modules/standard/items/sql)")
    parser.add_argument("--specials-dir", dest="specials_dir", default=None,
                        help="Path to the specials module directory (default: ../modules/standard/specials)")
    parser.add_argument("-c", "--config", dest="config_dir", default=None, help="Path to config directory")
    parser.add_argument("-t", "--tower-dir", dest="tower_dir", default=None, help="Path to the tower module directory (default: ../modules/standard/tower)")
    parser.add_argument("-i", "--implant-dir", dest="implant_dir", default=None,
                        help="Path to the implant module's SQL directory (default: ../modules/standard/implant/sql)")
    parser.add_argument("-p", "--perks-dir", dest="perks_dir", default=None,
                        help="Path to the perks module directory (default: ../modules/standard/perks)")
    parser.add_argument("--helpbot-dir", dest="helpbot_dir", default=None,
                        help="Path to the helpbot module directory (default: ../modules/standard/helpbot)")
    parser.add_argument("--trickle-dir", dest="trickle_dir", default=None,
                        help="Path to the trickle module directory (default: ../modules/standard/trickle)")
    parser.add_argument("-l", "--log-file", dest="log_file", default=None, help="Path to output log file (default: ./extractor.log)")
    parser.add_argument("--no-log-file", dest="no_log_file", action="store_true", help="Disable logging to file")
    parser.add_argument(
        "--log-level",
        dest="log_level",
        default="DEBUG",
        type=str.upper,
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        help="Logging level (default: DEBUG)",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose debug logging (enabled by default)")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress debug output (sets log level to INFO)")
    args = parser.parse_args()

    # Determine log file and level
    if args.no_log_file:
        log_file = None
    elif args.log_file:
        log_file = Path(args.log_file).resolve()
    else:
        log_file = Path("extractor.log").resolve()

    if args.quiet:
        log_level = logging.INFO
    elif args.verbose:
        log_level = logging.DEBUG
    else:
        log_level = getattr(logging, args.log_level, logging.DEBUG)

    setup_logging(log_file=log_file, level=log_level)

    # Normalize AO path
    ao_path = str(Path(args.ao_path).resolve())
    if not ao_path.endswith(os.sep) and not ao_path.endswith("/"):
        ao_path += "/"

    # Config directory
    if args.config_dir:
        config_dir = Path(args.config_dir).resolve()
    else:
        config_dir = Path(__file__).resolve().parent / "config"

    # Tower module directory
    if args.tower_dir:
        tower_dir = Path(args.tower_dir).resolve()
    else:
        tower_dir = Path(__file__).resolve().parent.parent / "modules" / "standard" / "tower"

    # Implant module SQL directory
    if args.implant_dir:
        implant_dir = Path(args.implant_dir).resolve()
    else:
        implant_dir = Path(__file__).resolve().parent.parent / "modules" / "standard" / "implant" / "sql"

    # Perks module directory
    if args.perks_dir:
        perks_dir = Path(args.perks_dir).resolve()
    else:
        perks_dir = Path(__file__).resolve().parent.parent / "modules" / "standard" / "perks"

    # Helpbot module directory
    if args.helpbot_dir:
        helpbot_dir = Path(args.helpbot_dir).resolve()
    else:
        helpbot_dir = Path(__file__).resolve().parent.parent / "modules" / "standard" / "helpbot"

    # Trickle module directory
    if args.trickle_dir:
        trickle_dir = Path(args.trickle_dir).resolve()
    else:
        trickle_dir = Path(__file__).resolve().parent.parent / "modules" / "standard" / "trickle"

    # Items module SQL directory
    if args.items_dir:
        items_dir = Path(args.items_dir).resolve()
    else:
        items_dir = Path(__file__).resolve().parent.parent / "modules" / "standard" / "items" / "sql"

    # Specials module directory
    if args.specials_dir:
        specials_dir = Path(args.specials_dir).resolve()
    else:
        specials_dir = Path(__file__).resolve().parent.parent / "modules" / "standard" / "specials"

    if log_file:
        log.info(f"Logging to file: {log_file}")
    log.info(f"Starting ItemsExtractor with AO path: {ao_path}")
    db_files = find_database_files(ao_path)
    log.info(f"Found {len(db_files)} database file(s).")
    if not db_files:
        log.error(f"No ResourceDatabase.dat files found in {ao_path}cd_image/data/db/")
        sys.exit(1)

    idx_path = Path(ao_path) / "cd_image" / "data" / "db" / "ResourceDatabase.idx"
    if not idx_path.is_file():
        log.error(f"Index file not found: {idx_path}")
        sys.exit(1)

    function_sets_cfg = config_dir / "FunctionSets.cfg"
    if not function_sets_cfg.is_file():
        log.error(f"FunctionSets.cfg not found in {config_dir}")
        sys.exit(1)

    if not (tower_dir / "tower_site.sql").is_file():
        log.error(f"tower_site.sql not found in {tower_dir}")
        sys.exit(1)

    extractor_cfg = config_dir / "extractor.cfg"
    if not extractor_cfg.is_file():
        log.error(f"extractor.cfg not found in {config_dir}")
        sys.exit(1)

    if not implant_dir.is_dir():
        log.error(f"Implant SQL directory not found: {implant_dir}")
        sys.exit(1)

    if not perks_dir.is_dir():
        log.error(f"Perks module directory not found: {perks_dir}")
        sys.exit(1)

    if not helpbot_dir.is_dir():
        log.error(f"Helpbot module directory not found: {helpbot_dir}")
        sys.exit(1)

    if not trickle_dir.is_dir():
        log.error(f"Trickle module directory not found: {trickle_dir}")
        sys.exit(1)

    if not items_dir.is_dir():
        log.error(f"Items SQL directory not found: {items_dir}")
        sys.exit(1)

    if not specials_dir.is_dir():
        log.error(f"Specials module directory not found: {specials_dir}")
        sys.exit(1)

    text_mdb = Path(ao_path) / "cd_image" / "text" / "text.mdb"
    if not text_mdb.is_file():
        log.error(f"Text database not found: {text_mdb}")
        sys.exit(1)

    start_time = time.time()

    # Load function sets configuration
    function_sets = FunctionSets(str(function_sets_cfg))
    extractor = RDBExtractor(function_sets)

    with MultiChunkReader(db_files) as db_reader:
        records = read_index_file(str(idx_path))

        # Generate tower site bounds
        log.info("Generating tower site bounds...")
        write_tower_site_bounds(db_reader, records, tower_dir)

        # Generate dynacamps
        log.info("Generating dynacamp SQL file...")
        write_dyna_sql(db_reader, records, extractor_cfg, helpbot_dir)

        # Generate skill trickle amounts
        log.info("Generating trickle SQL file...")
        write_trickle_sql(db_reader, records, text_mdb, extractor_cfg, trickle_dir)

        # Extract items
        item_records = [r for r in records if r.resource_type == IndexRecordType.AODB_ITEM_TYPE]
        total_items = len(item_records)
        log.info(f"Extracting {total_items} entries for resource type {IndexRecordType.AODB_ITEM_TYPE}...")

        item_entries = []
        for count, rec in enumerate(item_records, 1):
            try:
                item = extractor.read_item(db_reader, rec, extract_functions=True)
                item_entries.append(item)
            except Exception as e:
                log.debug(f"Failed to read item record {rec.resource_id}", exc_info=True)
            if count % 10000 == 0 or count == total_items:
                log.info(f"Extracted {count} / {total_items} entries ({count * 100 // total_items}%)...")

        log.info(f"Extracted {len(item_entries)} entries for resource type {IndexRecordType.AODB_ITEM_TYPE}.")

        # Generate implant and symbiant tables
        log.info("Generating implant SQL files...")
        write_implant_sql(item_entries, extractor_cfg, implant_dir)

        # Generate perk tables
        log.info("Generating perks SQL file...")
        write_perks_sql(db_reader, records, item_entries, text_mdb, perks_dir)

        # Generate research levels
        log.info("Generating research SQL file...")
        write_research_sql(db_reader, records, item_entries, text_mdb, helpbot_dir)

        # Extract nanos
        nano_records = [r for r in records if r.resource_type == IndexRecordType.AODB_NANO_TYPE]
        total_nanos = len(nano_records)
        log.info(f"Extracting {total_nanos} entries for resource type {IndexRecordType.AODB_NANO_TYPE}...")

        nano_entries = []
        for count, rec in enumerate(nano_records, 1):
            try:
                nano = extractor.read_item(db_reader, rec, extract_functions=True)
                nano_entries.append(nano)
            except Exception as e:
                log.debug(f"Failed to read nano record {rec.resource_id}", exc_info=True)
            if count % 10000 == 0 or count == total_nanos:
                log.info(f"Extracted {count} / {total_nanos} entries ({count * 100 // total_nanos}%)...")

        log.info(f"Extracted {len(nano_entries)} entries for resource type {IndexRecordType.AODB_NANO_TYPE}.")

        # Match IDs and generate SQL dump files
        log.info("Starting SQL dump generation...")
        matcher = IdMatcher(str(config_dir))
        matcher.write_sql_file(item_entries, nano_entries, ao_path, items_dir, specials_dir)
        log.info("SQL dump completed successfully.")

    elapsed = int(time.time() - start_time)
    log.info(f"Total elapsed time: {elapsed}s")


if __name__ == "__main__":
    main()
