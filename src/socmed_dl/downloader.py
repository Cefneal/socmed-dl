"""Download engine — wraps yt-dlp with smart format listing, batch, resume, cookies"""

import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from socmed_dl.utils import (
    find_yt_dlp, find_ffmpeg, format_size, format_duration,
    codec_family,
)


@dataclass
class CombinedFormat:
    num: int
    height: int
    resolution: str
    codec: str
    filesize: int
    video_id: str
    audio_id: str
    fps: int
    vbitrate: float
    is_avc: bool = False

    @property
    def size_str(self) -> str:
        return format_size(self.filesize) if self.filesize else "~?"

    @property
    def quality_label(self) -> str:
        h = self.height
        if h >= 2160: return "4K"
        if h >= 1440: return "1440p"
        if h >= 1080: return "1080p"
        if h >= 720:  return "720p"
        if h >= 480:  return "480p"
        if h >= 360:  return "360p"
        if h >= 240:  return "240p"
        if h >= 144:  return "144p"
        return f"{h}p" if h else "Audio"


@dataclass
class DownloadProgress:
    filename: str = ""
    percent: float = 0
    speed: str = ""
    eta: str = ""
    downloaded: str = ""
    total: str = ""


CODEC_ORDER = {"x264": 0, "VP9": 1, "AV1": 2, "x265": 3}

CODEC_INFO = {
    "x264": "Universal — plays on everything, largest files",
    "VP9": "Google — great quality, medium files, 60fps capable",
    "AV1": "Latest — best compression, may not play on old devices",
    "x265": "HEVC — good compression, mixed support",
}


def _codec_sort_key(f):
    return (CODEC_ORDER.get(f["codec"], 99), -(f["height"] or 0))


class Downloader:
    def __init__(self):
        self.yt_dlp = find_yt_dlp()
        self._progress_callback: Callable | None = None
        self._cancel = False

    def set_progress_callback(self, cb: Callable):
        self._progress_callback = cb

    def cancel(self):
        self._cancel = True

    def list_combined(
        self, url: str, cookies_file: str = "", proxy: str = "",
    ) -> tuple[list[CombinedFormat], str, float]:
        """Fetch all formats — returns EVERY distinct (codec, height) combo."""
        cmd = [self.yt_dlp, "-J", "--no-playlist", url]
        if cookies_file:
            cmd += ["--cookies", cookies_file]
        if proxy:
            cmd += ["--proxy", proxy]

        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            data = json.loads(r.stdout)
        except Exception:
            return [], "Unknown", 0

        title = data.get("title", "Unknown")
        duration = data.get("duration", 0)

        video_formats = []
        audio_formats = []
        for f in data.get("formats", []):
            vcodec = (f.get("vcodec") or "none").lower()
            acodec = (f.get("acodec") or "none").lower()
            height = f.get("height") or 0
            width = f.get("width") or 0
            filesize = f.get("filesize") or f.get("filesize_approx") or 0

            if vcodec != "none":
                video_formats.append({
                    "id": f.get("format_id", ""),
                    "height": height,
                    "width": width,
                    "codec": codec_family(vcodec),
                    "raw_codec": vcodec,
                    "filesize": filesize,
                    "fps": f.get("fps") or 0,
                    "tbr": f.get("tbr") or 0,
                    "ext": f.get("ext", ""),
                    "vcodec": vcodec,
                })
            elif acodec != "none":
                audio_formats.append({
                    "id": f.get("format_id", ""),
                    "filesize": filesize,
                    "abr": f.get("abr") or 0,
                })

        if not audio_formats:
            audio_formats.append({"id": "bestaudio", "filesize": 0, "abr": 0})

        best_audio = max(audio_formats, key=lambda a: a.get("abr", 0) or 0)

        seen = set()
        combined = []
        num = 0

        for v in sorted(video_formats, key=_codec_sort_key):
            key = (v["height"], v["codec"])
            if key in seen:
                continue
            seen.add(key)
            num += 1
            total_size = (v["filesize"] or 0) + (best_audio["filesize"] or 0)
            combined.append(CombinedFormat(
                num=num,
                height=v["height"],
                resolution=f"{v['width']}x{v['height']}" if v["height"] else "audio",
                codec=v["codec"],
                filesize=total_size,
                video_id=v["id"],
                audio_id=best_audio["id"],
                fps=v["fps"],
                vbitrate=v["tbr"],
            ))

        return combined, title, duration

    def get_codecs(self, formats: list[CombinedFormat]) -> list[str]:
        """Extract unique, ordered codec families from a format list."""
        seen: set[str] = set()
        ordered: list[str] = []
        for f in formats:
            if f.codec not in seen:
                seen.add(f.codec)
                ordered.append(f.codec)
        return ordered

    @staticmethod
    def filter_by_codec(formats: list[CombinedFormat], codec: str) -> list[CombinedFormat]:
        """Filter formats by codec family and renumber from 1."""
        filtered = [f for f in formats if f.codec.lower() == codec.lower()]
        for i, f in enumerate(filtered, 1):
            f.num = i
        return filtered

    def download_format(
        self, url: str, outdir: str, fmt: CombinedFormat,
        cookies_file: str = "", proxy: str = "",
        output_template: str = "%(title)s",
        embed_metadata: bool = True,
        dry_run: bool = False,
    ) -> bool:
        os.makedirs(outdir, exist_ok=True)
        self._cancel = False

        cmd = [
            self.yt_dlp, url,
            "-f", f"{fmt.video_id}+{fmt.audio_id}",
            "--merge-output-format", "mkv",
            "-o", f"{outdir}/{output_template}.%(ext)s",
            "--no-playlist",
            "--newline",
        ]
        if cookies_file:
            cmd += ["--cookies", cookies_file]
        if proxy:
            cmd += ["--proxy", proxy]
        if embed_metadata:
            cmd += ["--embed-metadata"]

        return self._run_process(cmd)

    def download_audio(
        self, url: str, outdir: str,
        audio_format: str = "mp3",
        cookies_file: str = "", proxy: str = "",
        output_template: str = "%(title)s",
        dry_run: bool = False,
    ) -> bool:
        os.makedirs(outdir, exist_ok=True)
        self._cancel = False

        cmd = [
            self.yt_dlp, url,
            "-f", "bestaudio/best",
            "--extract-audio",
            "--audio-format", audio_format,
            "--audio-quality", "0",
            "-o", f"{outdir}/{output_template}.%(ext)s",
            "--no-playlist",
            "--embed-metadata",
            "--newline",
        ]
        if cookies_file:
            cmd += ["--cookies", cookies_file]
        if proxy:
            cmd += ["--proxy", proxy]

        return self._run_process(cmd)

    def _run_process(self, cmd: list[str]) -> bool:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )

        for line in process.stdout or []:
            line = line.rstrip()
            if not line:
                continue
            if self._progress_callback:
                dp = self._parse_line(line)
                if dp:
                    self._progress_callback(dp)
            if self._cancel:
                process.terminate()
                process.wait()
                return False

        process.wait()
        return process.returncode == 0

    def _parse_line(self, line: str) -> DownloadProgress | None:
        dp = DownloadProgress()
        m = re.search(
            r'\[download\]\s+([\d.]+%)\s+of\s+~?\s*([\d.]+.?[KMGT]?i?B)'
            r'(?:\s+at\s+([\d.]+.?[KMGT]?i?B/s))?(?:\s+ETA\s+([\d:]+))?',
            line,
        )
        if m:
            dp.percent = float(m.group(1).replace("%", ""))
            dp.total = m.group(2)
            dp.speed = m.group(3) or ""
            dp.eta = m.group(4) or ""
            return dp
        m2 = re.search(r'\[download\]\s+Destination:\s+(.+)', line)
        if m2:
            dp.filename = os.path.basename(m2.group(1).strip())
            return dp
        return None
