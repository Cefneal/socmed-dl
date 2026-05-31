"""Download engine — wraps yt-dlp with format listing, batch, resume, cookies"""

import json
import os
import re
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from socmed_dl.utils import find_yt_dlp, find_ffmpeg, get_format_sort, format_size, format_duration


@dataclass
class FormatInfo:
    id: str
    ext: str
    resolution: str
    fps: int
    filesize: int
    tbr: float
    vcodec: str
    acodec: str
    abr: float
    height: int
    note: str = ""

    @property
    def display(self) -> str:
        size = format_size(self.filesize) if self.filesize else "~?"
        v = self.vcodec.split(".")[0] if self.vcodec != "none" else ""
        a = self.acodec.split(".")[0] if self.acodec != "none" else ""
        codec = f"{v}/{a}" if v and a else v or a
        return (
            f"[cyan]{self.id:6s}[/] {self.resolution:14s} "
            f"{self.ext:4s} {size:>8s} "
            f"[yellow]{codec}[/] "
            f"{self.tbr:>7.0f}k {self.note}"
        )


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
        self.ffmpeg = find_ffmpeg()
        self._progress_callback: Callable | None = None
        self._cancel = False

    def set_progress_callback(self, cb: Callable):
        self._progress_callback = cb

    def cancel(self):
        self._cancel = True

    def list_formats(self, url: str, cookies_file: str = "", proxy: str = "") -> list[FormatInfo]:
        cmd = [self.yt_dlp, "-J", "--no-playlist", url]
        if cookies_file:
            cmd += ["--cookies", cookies_file]
        if proxy:
            cmd += ["--proxy", proxy]

        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            data = json.loads(r.stdout)
        except Exception:
            return []

        formats = []
        for f in data.get("formats", []):
            height = f.get("height") or 0
            res = f"{f.get('width', 0)}x{height}" if height else "audio"
            vcodec = f.get("vcodec", "none") or "none"
            acodec = f.get("acodec", "none") or "none"
            if vcodec == "none" and acodec == "none":
                continue
            fmt = FormatInfo(
                id=f.get("format_id", ""),
                ext=f.get("ext", ""),
                resolution=res,
                fps=f.get("fps", 0) or 0,
                filesize=f.get("filesize", 0) or f.get("filesize_approx", 0) or 0,
                tbr=f.get("tbr", 0) or 0,
                vcodec=vcodec,
                acodec=acodec,
                abr=f.get("abr", 0) or 0,
                height=height,
                note=f.get("format_note", ""),
            )
            formats.append(fmt)

        formats.sort(key=lambda x: x.height, reverse=True)
        return formats

    def parse_ytdlp_output(self, line: str) -> DownloadProgress | None:
        dp = DownloadProgress()
        m = re.search(r'\[download\]\s+(.+?)\s+of\s+(.+?)\s+at\s+(.+?)\s+ETA\s+(.+?)$', line)
        if m:
            dp.downloaded = m.group(1).strip()
            dp.total = m.group(2).strip()
            dp.speed = m.group(3).strip()
            dp.eta = m.group(4).strip()
            try:
                pct_str = dp.downloaded.replace("%", "")
                dp.percent = float(pct_str)
            except ValueError:
                dp.percent = 0
            return dp
        m2 = re.search(r'\[download\]\s+Destination:\s+(.+)', line)
        if m2:
            dp.filename = os.path.basename(m2.group(1).strip())
            return dp
        m3 = re.search(r'\[download\]\s+(\d+\.?\d*)\%\s+of\s+~?\s*([\d.]+.?[KMGT]?i?B)', line)
        if m3:
            dp.percent = float(m3.group(1))
            dp.total = m3.group(2)
            return dp
        return None

    def download(
        self,
        url: str,
        outdir: str,
        quality: int = 720,
        codec: str = "x265",
        mode: str = "video",
        audio_format: str = "mp3",
        cookies_file: str = "",
        proxy: str = "",
        concurrent: int = 1,
        output_template: str = "%(title)s_%(height)s",
        playlist: bool = False,
        playlist_items: str = "",
        playlist_reverse: bool = False,
        max_filesize: int = 0,
        rate_limit: int = 0,
        retry_count: int = 3,
        retry_delay: int = 10,
        subtitles: bool = False,
        subtitle_lang: str = "en",
        embed_thumbnail: bool = False,
        embed_metadata: bool = True,
        keep_original: bool = False,
        auto_convert: bool = True,
        dry_run: bool = False,
    ) -> bool:
        os.makedirs(outdir, exist_ok=True)
        self._cancel = False
        sort_spec = get_format_sort(codec, quality)

        if mode == "audio":
            return self._download_audio(
                url, outdir, audio_format, cookies_file, proxy, output_template,
                playlist, playlist_items, playlist_reverse,
                max_filesize, rate_limit, retry_count, retry_delay,
                dry_run,
            )
        return self._download_video(
            url, outdir, sort_spec, quality, codec,
            cookies_file, proxy, output_template, playlist,
            playlist_items, playlist_reverse, max_filesize,
            rate_limit, retry_count, retry_delay, subtitles,
            subtitle_lang, embed_thumbnail, embed_metadata,
            keep_original, auto_convert, dry_run,
        )

    def _build_base_cmd(
        self, url: str, outdir: str, output_template: str,
        cookies: str, proxy: str, retry: int, retry_delay: int,
        dry_run: bool, playlist: bool = False,
        playlist_items: str = "", playlist_reverse: bool = False,
    ) -> list[str]:
        cmd = [self.yt_dlp]
        if not playlist:
            cmd += ["--no-playlist"]
        else:
            if playlist_items:
                cmd += ["--playlist-items", playlist_items]
            if playlist_reverse:
                cmd += ["--playlist-reverse"]
        if cookies:
            cmd += ["--cookies", cookies]
        if proxy:
            cmd += ["--proxy", proxy]
        if retry > 0:
            cmd += ["--retries", str(retry), "--retry-sleep", str(retry_delay)]
        if dry_run:
            cmd += ["--simulate", "--print", "json"]
        cmd += ["-o", f"{outdir}/{output_template}.%(ext)s"]
        cmd += ["--no-warnings", "--newline", url]
        return cmd

    def _download_video(
        self, url, outdir, sort_spec, quality, codec,
        cookies, proxy, output_template, playlist, playlist_items,
        playlist_reverse, max_filesize, rate_limit, retry, retry_delay,
        subtitles, subtitle_lang, embed_thumbnail, embed_metadata,
        keep_original, auto_convert, dry_run,
    ) -> bool:
        cmd = self._build_base_cmd(
            url, outdir, output_template, cookies, proxy, retry, retry_delay, dry_run,
            playlist, playlist_items, playlist_reverse,
        )
        cmd += [
            "-S", sort_spec,
            "--merge-output-format", "mkv",
            "-f", f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]",
        ]
        if max_filesize:
            cmd += ["--max-filesize", str(max_filesize)]
        if rate_limit:
            cmd += ["--limit-rate", f"{rate_limit}M"]
        if subtitles:
            cmd += ["--write-subs", "--sub-langs", subtitle_lang]
        if embed_thumbnail:
            cmd += ["--embed-thumbnail"]
        if embed_metadata:
            cmd += ["--embed-metadata"]

        if dry_run:
            return self._run_dry(cmd)

        success = self._run_process(cmd)
        if not success:
            return False

        if auto_convert:
            from socmed_dl.converter import convert_to_x265
            return convert_to_x265(outdir, keep_original)
        return True

    def _download_audio(
        self, url, outdir, audio_format, cookies, proxy, output_template,
        playlist, playlist_items, playlist_reverse,
        max_filesize, rate_limit, retry, retry_delay, dry_run,
    ) -> bool:
        audio_ext = audio_format or "mp3"
        cmd = self._build_base_cmd(
            url, outdir, output_template, cookies, proxy, retry, retry_delay, dry_run,
            playlist, playlist_items, playlist_reverse,
        )
        cmd += [
            "-f", "bestaudio/best",
            "--extract-audio",
            "--audio-format", audio_ext,
            "--audio-quality", "0",
        ]
        if max_filesize:
            cmd += ["--max-filesize", str(max_filesize)]
        if rate_limit:
            cmd += ["--limit-rate", f"{rate_limit}M"]
        if embed_metadata:
            cmd += ["--embed-metadata"]

        if dry_run:
            return self._run_dry(cmd)
        return self._run_process(cmd)

    def _run_dry(self, cmd: list[str]) -> bool:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            data = json.loads(r.stdout)
            for f in data.get("requests", [data]):
                info = f.get("info_dict", f)
                title = info.get("title", "?")
                dur = info.get("duration", 0)
                size = info.get("filesize", 0) or info.get("filesize_approx", 0) or 0
                print(f"  Title: {title}")
                print(f"  Duration: {format_duration(dur)}")
                print(f"  Size: {format_size(size)}")
            return True
        except Exception as e:
            print(f"  Dry-run error: {e}")
            return False

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
                dp = self.parse_ytdlp_output(line)
                if dp:
                    self._progress_callback(dp)
                else:
                    self._progress_callback(DownloadProgress(filename=line))
            else:
                self._default_output(line)
            if self._cancel:
                process.terminate()
                return False

        process.wait()
        return process.returncode == 0

    def _default_output(self, line: str):
        if line.startswith("[download]"):
            print(f"\r  {line}", end="", flush=True)
        elif any(line.startswith(x) for x in ("[youtube", "[info", "ERROR", "WARNING")):
            print(f"  {line}")
        elif "Destination" in line:
            print(f"\n  {os.path.basename(line.split(': ')[-1])}")

    def download_batch(
        self, urls: list[str], **kwargs,
    ) -> list[tuple[str, bool]]:
        results = []
        with ThreadPoolExecutor(max_workers=kwargs.get("concurrent", 1)) as pool:
            fut_to_url = {pool.submit(self.download, url, **kwargs): url for url in urls}
            for fut in as_completed(fut_to_url):
                url = fut_to_url[fut]
                try:
                    ok = fut.result()
                    results.append((url, ok))
                except Exception as e:
                    results.append((url, False))
        return results
