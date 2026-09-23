"""
Guards the live bot's data directory against the test suite.

The bot runs out of this same checkout, so `data/` holds its real database and cache. A test that
writes or deletes there damages a running bot - this suite has already destroyed `data/cache` once,
via a `shutil.rmtree("./data/cache")` in a test. These hooks make that class of mistake fail loudly
at the call site instead of silently eating the bot's data. Tests that need files must use
`tempfile`.
"""

import builtins
import os
import shutil
import sqlite3
from pathlib import Path

LIVE_DATA_DIR = os.path.realpath(os.path.join(os.path.dirname(__file__), os.pardir, "data"))


def _is_live_data_path(path):
    if not isinstance(path, (str, bytes, os.PathLike)):
        # an open file descriptor or similar - not a path we can resolve, so not our business
        return False

    resolved = os.path.realpath(os.fsdecode(path) if isinstance(path, bytes) else os.fspath(path))
    return resolved == LIVE_DATA_DIR or resolved.startswith(LIVE_DATA_DIR + os.sep)


def _refuse(operation, path):
    raise RuntimeError(
        "%s on %r was blocked: it targets the live bot data directory (%s). "
        "Tests must use tempfile, not the bot's data." % (operation, os.fspath(path), LIVE_DATA_DIR))


def _relative_to_a_directory_fd(path, kwargs):
    """
    os.remove/rmdir/open/rename take a keyword-only dir_fd that a relative path is resolved
    against, so such a path cannot be checked against the cwd. shutil.rmtree uses this internally
    for every entry it walks. Skipping them is safe: the caller reached them through a top-level
    call that this guard already checked.
    """

    has_dir_fd = any(kwargs.get(name) is not None for name in ("dir_fd", "src_dir_fd", "dst_dir_fd"))
    return has_dir_fd and not os.path.isabs(os.fsdecode(path) if isinstance(path, bytes) else os.fspath(path))


def _guard(operation, original, path_arg=0, path_kwarg=None, allow=None):
    def wrapper(*args, **kwargs):
        path = kwargs.get(path_kwarg) if path_kwarg in kwargs else (args[path_arg] if len(args) > path_arg else None)
        if (path is not None
                and isinstance(path, (str, bytes, os.PathLike))
                and not _relative_to_a_directory_fd(path, kwargs)
                and _is_live_data_path(path)
                and not (allow and allow(*args, **kwargs))):
            _refuse(operation, path)
        return original(*args, **kwargs)

    return wrapper


def _opened_for_writing(file, mode="r", *args, **kwargs):
    return not any(c in mode for c in "wax+")


builtins.open = _guard("open() for writing", builtins.open, path_kwarg="file", allow=_opened_for_writing)
os.open = _guard("os.open() for writing", os.open, path_kwarg="path",
                 allow=lambda path, flags, *a, **kw: not flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT))
os.remove = _guard("os.remove()", os.remove, path_kwarg="path")
os.unlink = _guard("os.unlink()", os.unlink, path_kwarg="path")
os.rmdir = _guard("os.rmdir()", os.rmdir, path_kwarg="path")
os.makedirs = _guard("os.makedirs()", os.makedirs, path_kwarg="name")
os.rename = _guard("os.rename()", os.rename, path_kwarg="src")
shutil.rmtree = _guard("shutil.rmtree()", shutil.rmtree, path_kwarg="path")
sqlite3.connect = _guard("sqlite3.connect()", sqlite3.connect, path_kwarg="database")
Path.mkdir = _guard("Path.mkdir()", Path.mkdir, path_arg=0, path_kwarg="self")
Path.unlink = _guard("Path.unlink()", Path.unlink, path_arg=0, path_kwarg="self")
