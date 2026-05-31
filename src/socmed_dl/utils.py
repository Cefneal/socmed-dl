"""Utility functions for socmed-dl"""

import os
import re
import shutil
import subprocess
from pathlib import Path

PLATFORMS = {
    "youtube": r"(youtube\.com|youtu\.be)",
    "facebook": r"(facebook\.com|fb\.watch|fb\.com)",
    "instagram": r"(instagram\.com|instagr\.am)",
    "tiktok": r"(tiktok\.com|vm\.tiktok)",
    "twitter": r"(twitter\.com|x\.com)",
    "reddit": r"(reddit\.com|redd\.it)",
    "twitch": r"(twitch\.tv)",
    "vimeo": r"(vimeo\.com)",
    "dailymotion": r"(dailymotion\.com|dai\.ly)",
    "tumblr": r"(tumblr\.com)",
}


def detect_platform(url: str) -> str:
    for platform, pattern in PLATFORMS.items():
        if re.search(pattern, url, re.IGNORECASE):
            return platform
    return "unknown"


def find_yt_dlp() -> str | None:
    candidates = [
        shutil.which("yt-dlp"),
        os.path.expanduser("~/.local/bin/yt-dlp"),
        str(Path.home() / ".local" / "bin" / "yt-dlp"),
        shutil.which("youtube-dl"),
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return None


def find_ffmpeg() -> str | None:
    return shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")


def find_ffprobe() -> str | None:
    return shutil.which("ffprobe") or shutil.which("ffprobe.exe")


def check_deps():
    missing = []
    if not find_yt_dlp():
        missing.append("yt-dlp")
    if not find_ffmpeg():
        missing.append("ffmpeg")
    return missing


def format_size(size_bytes: int) -> str:
    if size_bytes <= 0:
        return "Unknown"
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def format_duration(seconds: float) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


CODEC_PRIORITY = {
    "x265": ["h265", "hevc", "vp9", "av01", "h264"],
    "x264": ["h264", "vp9", "hevc", "av01"],
    "vp9": ["vp9", "av01", "h265", "h264"],
    "av1": ["av01", "vp9", "h265", "h264"],
}


def get_format_sort(codec: str, height: int) -> str:
    priority = CODEC_PRIORITY.get(codec, CODEC_PRIORITY["x265"])
    codec_sort = "+".join(f"codec:{c}" for c in priority)
    return f"+{codec_sort},height:{height},tbr"
