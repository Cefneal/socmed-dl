"""Download engine — wraps yt-dlp with smart format listing, batch, resume, cookies"""

import json
import os
import re
import subprocess
import sys
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

    @property
    def size_str(self) -> str:
        return format_size(self.filesize) if self.filesize else "~?"


@dataclass
class DownloadProgress:
    filename: str = ""
    percent: float = 0
    speed: str = ""
    eta: str = ""
    downloaded: str = ""
    total: str = ""


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
        """Fetch all formats and return combined video+audio options + title + duration"""
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
            filesize = f.get("filesize") or f.get("filesize_approx") or 0

            if vcodec != "none" and vcodec != "none":
                video_formats.append({
                    "id": f.get("format_id", ""),
                    "height": height,
                    "width": f.get("width") or 0,
                    "codec": codec_family(vcodec),
                    "filesize": filesize,
                    "fps": f.get("fps") or 0,
                    "tbr": f.get("tbr") or 0,
                    "ext": f.get("ext", ""),
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
        for v in sorted(video_formats, key=lambda v: v["height"], reverse=True):
            h = v["height"]
            if h in seen:
                continue
            seen.add(h)
            num += 1
            total_size = (v["filesize"] or 0) + (best_audio["filesize"] or 0)
            combined.append(CombinedFormat(
                num=num,
                height=h,
                resolution=f"{v['width']}x{h}" if h else "audio",
                codec=v["codec"],
                filesize=total_size,
                video_id=v["id"],
                audio_id=best_audio["id"],
                fps=v["fps"],
                vbitrate=v["tbr"],
            ))

        return combined, title, duration

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
