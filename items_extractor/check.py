import argparse
import logging
from pathlib import Path
import sys

from src.checks import run_checks
from src.function_sets import FunctionSets
from src.rdb_file import MultiChunkReader, find_database_files
from src.rdb_index import read_index_file

log = logging.getLogger("ItemsChecker")


def main():
    parser = argparse.ArgumentParser(description="Check the bot's hand-maintained module data against the game and the generated item tables")
    parser.add_argument("-d", "--dir", dest="ao_path", required=True, help="Path to Anarchy Online directory")
    parser.add_argument("-c", "--config", dest="config_dir", default=None, help="Path to config directory (default: ./config)")
    parser.add_argument("-m", "--modules-dir", dest="modules_dir", default=None,
                        help="Path to the standard modules directory (default: ../modules/standard)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)-5s %(message)s", stream=sys.stdout)

    config_dir = Path(args.config_dir).resolve() if args.config_dir else Path(__file__).resolve().parent / "config"
    modules_dir = Path(args.modules_dir).resolve() if args.modules_dir else Path(__file__).resolve().parent.parent / "modules" / "standard"

    db_files = find_database_files(args.ao_path)
    if not db_files:
        log.error(f"No ResourceDatabase.dat files found in {Path(args.ao_path) / 'cd_image' / 'data' / 'db'}")
        sys.exit(1)
    idx_path = Path(args.ao_path) / "cd_image" / "data" / "db" / "ResourceDatabase.idx"
    text_mdb = Path(args.ao_path) / "cd_image" / "text" / "text.mdb"
    for path in (idx_path, text_mdb, config_dir / "FunctionSets.cfg", config_dir / "extractor.cfg"):
        if not path.is_file():
            log.error(f"File not found: {path}")
            sys.exit(1)
    if not modules_dir.is_dir():
        log.error(f"Modules directory not found: {modules_dir}")
        sys.exit(1)

    with MultiChunkReader(db_files) as db_reader:
        records = read_index_file(str(idx_path))
        count = run_checks(db_reader, records, FunctionSets(str(config_dir / "FunctionSets.cfg")), config_dir / "extractor.cfg", text_mdb, modules_dir)

    # A non-zero exit when any check found a problem
    if count:
        log.error(f"Found {count} problems")
        sys.exit(1)
    log.info("No problems found")


if __name__ == "__main__":
    main()
