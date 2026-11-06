from __future__ import annotations

from pathlib import Path


ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv"}
MAX_VIDEO_BYTES = 50 * 1024 * 1024
MAX_TEXT_LENGTH = 12_000


def allowed_video_file(filename: str) -> bool:
    return Path(filename).suffix.lower() in ALLOWED_VIDEO_EXTENSIONS
