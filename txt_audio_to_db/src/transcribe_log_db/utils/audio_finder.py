"""
Audio discovery utilities.

Find audio files stored one level deep under a root directory, where each
immediate subdirectory is a UUID-named folder containing one or more audio files.

Default behavior is one-level scan, returning candidate audio file paths.
Includes helpers to filter already processed files (based on DB `source_file.path`),
and to pick the newest file deterministically.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple

from common.config.proj_config import PROJ_CONFIG
from common.logging_utils.logging_config import get_logger


ALLOWED_EXTENSIONS = {".mp3", ".m4a", ".wav"}


def get_default_audio_root() -> Path:
    """Return the default audio root directory from project config."""
    return PROJ_CONFIG.get_download_dir()


def _is_audio_file(path: Path) -> bool:
    return path.is_file() and path.suffix.lower() in ALLOWED_EXTENSIONS


def find_audio_candidates(root_dir: Path, one_level: bool = True) -> List[Path]:
    """
    Find audio files under the root directory.
    - If one_level=True: only check immediate subdirectories (UUID folders).
    - If one_level=False: recursive scan.
    """
    logger = get_logger("audio_finder")
    candidates: List[Path] = []

    root_dir = Path(root_dir).expanduser().resolve()
    if not root_dir.exists() or not root_dir.is_dir():
        logger.warning(f"Audio root does not exist or is not a directory: {root_dir}")
        return candidates

    if one_level:
        for child in root_dir.iterdir():
            if child.is_dir():
                # Find all allowed audio files directly within this folder
                for item in child.iterdir():
                    if _is_audio_file(item):
                        candidates.append(item)
    else:
        for item in root_dir.rglob("*"):
            if _is_audio_file(item):
                candidates.append(item)

    return candidates


def _file_sort_key(path: Path) -> Tuple[float, float, str]:
    try:
        stat = path.stat()
        mtime = stat.st_mtime
        ctime = stat.st_ctime
    except OSError:
        # If we cannot stat, push it to the end
        mtime = -1.0
        ctime = -1.0
    return (mtime, ctime, str(path).lower())


def pick_newest(paths: Sequence[Path]) -> Path | None:
    """Return the newest file by mtime, breaking ties by ctime then path name."""
    if not paths:
        return None
    return sorted(paths, key=_file_sort_key, reverse=True)[0]


def filter_unprocessed(conn, paths: Sequence[Path]) -> List[Path]:
    """
    Return only paths that are not present in the source_file table by exact path string.
    """
    logger = get_logger("audio_finder")
    if not paths:
        return []

    path_strings = [str(p.resolve()) for p in paths]
    remaining = set(path_strings)

    # Query DB for existing paths
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT path FROM gdr_source_file WHERE path = ANY(%s)", (path_strings,)
            )
            rows = cur.fetchall() or []
            existing = {row["path"] for row in rows}
            remaining = remaining.difference(existing)
    except Exception as e:
        logger.warning(f"Failed to filter processed files, proceeding without filter: {e}")
        # If the filter fails, return all input paths
        return list(Path(p) for p in path_strings)

    return [Path(p) for p in path_strings if p in remaining]


