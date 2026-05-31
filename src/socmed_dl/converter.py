"""x265 / codec conversion engine"""

import os
import subprocess
from pathlib import Path
from typing import Callable

from socmed_dl.utils import find_ffmpeg, find_ffprobe


def convert_to_x265(
    directory: str,
    keep_original: bool = False,
    crf: int = 28,
    preset: str = "medium",
    audio_bitrate: str = "128k",
    audio_codec: str = "aac",
    progress_callback: Callable | None = None,
) -> bool:
    ffmpeg = find_ffmpeg()
    ffprobe = find_ffprobe()
    if not ffmpeg or not ffprobe:
        return False

    mkv_files = sorted(Path(directory).glob("*.mkv"))
    if not mkv_files:
        return True

    success = True
    for mkv in mkv_files:
        if "_x265" in mkv.name or "_converted" in mkv.name:
            continue
        output = mkv.parent / f"{mkv.stem}_x265{mkv.suffix}"

        if progress_callback:
            progress_callback({"status": "converting", "file": mkv.name, "percent": 0})

        total_duration = None
        try:
            r = subprocess.run(
                [ffprobe, "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(mkv)],
                capture_output=True, text=True,
            )
            total_duration = float(r.stdout.strip())
        except (ValueError, TypeError, OSError):
            total_duration = None

        cmd = [
            ffmpeg, "-i", str(mkv),
            "-c:v", "libx265",
            "-crf", str(crf),
            "-preset", preset,
            "-c:a", audio_codec,
            "-b:a", audio_bitrate,
            "-movflags", "+faststart",
            "-y", str(output),
        ]

        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )

        for line in process.stdout or []:
            line = line.strip()
            if total_duration and "time=" in line:
                try:
                    ts = line.split("time=")[1].split()[0]
                    parts = list(map(float, ts.split(":")))
                    if len(parts) == 3:
                        ct = parts[0] * 3600 + parts[1] * 60 + parts[2]
                        pct = min(99, int(ct / total_duration * 100))
                        if progress_callback:
                            progress_callback({
                                "status": "converting",
                                "file": mkv.name,
                                "percent": pct,
                            })
                except (ValueError, IndexError):
                    pass

        process.wait()

        if process.returncode == 0:
            if progress_callback:
                progress_callback({
                    "status": "done",
                    "file": mkv.name,
                    "output": str(output),
                    "size": os.path.getsize(output),
                })
            if not keep_original:
                Path(mkv).unlink(missing_ok=True)
        else:
            success = False

    return success
