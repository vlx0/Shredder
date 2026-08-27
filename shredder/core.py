"""Overwrite file contents, then remove — harder to recover than Recycle Bin."""

from __future__ import annotations

import os
import secrets
import stat
from collections.abc import Callable
from pathlib import Path

ProgressCb = Callable[[str, float], None]

CHUNK = 1024 * 1024  # 1 MiB


def _make_writable(path: Path) -> None:
    try:
        mode = path.stat().st_mode
        path.chmod(mode | stat.S_IWRITE)
    except OSError:
        pass


def shred_file(
    path: Path,
    passes: int = 3,
    on_progress: ProgressCb | None = None,
) -> None:
    """Overwrite a file with random data `passes` times, scramble name, delete."""
    path = path.resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Not a file: {path}")

    passes = max(1, min(7, int(passes)))
    _make_writable(path)
    size = path.stat().st_size
    label = path.name

    with open(path, "r+b", buffering=0) as fh:
        for p in range(passes):
            fh.seek(0)
            done = 0
            while done < size:
                n = min(CHUNK, size - done)
                fh.write(os.urandom(n))
                done += n
                if on_progress and size:
                    frac = (p + done / size) / passes
                    on_progress(label, frac)
            fh.flush()
            try:
                os.fsync(fh.fileno())
            except OSError:
                pass

    # Scramble filename so undelete tools don't keep the original name
    parent = path.parent
    junk = parent / (secrets.token_hex(8) + ".tmp")
    try:
        path.replace(junk)
        target = junk
    except OSError:
        target = path

    _make_writable(target)
    target.unlink(missing_ok=False)
    if on_progress:
        on_progress(label, 1.0)


def shred_path(
    path: Path,
    passes: int = 3,
    on_progress: ProgressCb | None = None,
) -> list[str]:
    """Shred a file or all files under a directory (files only, then empty dirs)."""
    path = path.resolve()
    shredded: list[str] = []

    if path.is_file():
        shred_file(path, passes=passes, on_progress=on_progress)
        shredded.append(str(path))
        return shredded

    if not path.is_dir():
        raise FileNotFoundError(f"Not found: {path}")

    files = [p for p in path.rglob("*") if p.is_file()]
    total = max(1, len(files))

    for i, f in enumerate(files):

        def _cb(name: str, frac: float, idx: int = i) -> None:
            if on_progress:
                on_progress(name, (idx + frac) / total)

        shred_file(f, passes=passes, on_progress=_cb)
        shredded.append(str(f))

    # remove empty directories bottom-up
    dirs = sorted((p for p in path.rglob("*") if p.is_dir()), reverse=True)
    for d in dirs:
        try:
            d.rmdir()
        except OSError:
            pass
    try:
        path.rmdir()
    except OSError:
        pass

    return shredded
