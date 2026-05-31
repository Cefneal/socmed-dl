"""Utility functions for socmed-dl"""

import os
import re
import shutil
import subprocess
import sys
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


def default_downloads_dir() -> str:
    if sys.platform == "win32":
        return os.path.join(os.environ.get("USERPROFILE", "C:\\"), "Downloads")
    if sys.platform == "darwin":
        return os.path.expanduser("~/Downloads")
    if "ANDROID_ROOT" in os.environ or "TERMUX_VERSION" in os.environ:
        return os.path.expanduser("~/storage/downloads")
    return os.path.expanduser("~/Downloads")


def format_size(size_bytes: int) -> str:
    if size_bytes <= 0:
        return "~?"
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


def detect_hw_accel() -> str | None:
    """Detect available HW encoder but default to None for reliability."""
    return None


def hw_encoder_name(hw: str) -> str | None:
    return {
        "nvenc": "hevc_nvenc",
        "amf": "hevc_amf",
        "qsv": "hevc_qsv",
        "videotoolbox": "hevc_videotoolbox",
    }.get(hw)


def codec_family(vcodec: str) -> str:
    v = vcodec.lower()
    if "av01" in v or "av1" in v:
        return "AV1"
    if "vp9" in v:
        return "VP9"
    if "hevc" in v or "h265" in v or "x265" in v:
        return "x265"
    if "h264" in v or "avc" in v or "x264" in v:
        return "x264"
    return v.split(".")[0][:6]


PLATFORM_EMOJI = {
    "youtube": "🎬", "facebook": "📘", "instagram": "📸", "tiktok": "🎵",
    "twitter": "🐦", "reddit": "🤖", "twitch": "📺", "vimeo": "🎥",
    "dailymotion": "🎞", "tumblr": "💬",
}
PLATFORM_COLORS = {
    "youtube": "red", "facebook": "blue", "instagram": "magenta",
    "tiktok": "cyan", "twitter": "white", "reddit": "orange1",
    "twitch": "purple", "vimeo": "bright_blue", "dailymotion": "yellow",
    "tumblr": "bright_magenta", "unknown": "white",
}


def platform_emoji(platform: str) -> str:
    return PLATFORM_EMOJI.get(platform, "🌐")


def platform_color(platform: str) -> str:
    return PLATFORM_COLORS.get(platform, "white")
