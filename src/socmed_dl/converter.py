"""x265 / codec conversion engine with hardware acceleration support"""

import os
import re
import select
import subprocess
from pathlib import Path
from typing import Callable

from socmed_dl.utils import find_ffmpeg, find_ffprobe, detect_hw_accel, hw_encoder_name


TIME_RE = re.compile(r'time=(\d+):(\d+):(\d+)\.(\d+)')


def _parse_ffmpeg_time(line: str) -> float | None:
    m = TIME_RE.search(line)
    if not m:
        return None
    h, mi, s, frac = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
    frac_str = m.group(4)
    divisor = 10 ** len(frac_str)
    return h * 3600 + mi * 60 + s + frac / divisor


def convert_video(
    directory: str,
    keep_original: bool = False,
    crf: int = 28,
    preset: str = "medium",
    progress_callback: Callable | None = None,
) -> bool:
    ffmpeg = find_ffmpeg()
    ffprobe = find_ffprobe()
    if not ffmpeg or not ffprobe:
        return False

    mkv_files = sorted(Path(directory).glob("*.mkv"))
    if not mkv_files:
        return True

    hw = detect_hw_accel()
    encoder = hw_encoder_name(hw) or "libx265"
    if encoder == "libx265":
        enc_params = ["-crf", str(crf), "-preset", preset]
    else:
        enc_params = ["-preset", "p7"] if hw != "qsv" else ["-global_quality", str(crf)]

    success = True
    for mkv in mkv_files:
        if "_x265" in mkv.name or "_converted" in mkv.name:
            continue
        output = mkv.parent / f"{mkv.stem}_x265{mkv.suffix}"

        total_duration = None
        try:
            r = subprocess.run(
                [ffprobe, "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(mkv)],
                capture_output=True, text=True, timeout=15,
            )
            total_duration = float(r.stdout.strip())
        except (ValueError, TypeError, OSError, subprocess.TimeoutExpired):
            pass

        if progress_callback:
            progress_callback({"status": "start", "file": mkv.name, "percent": 0})

        cmd = [ffmpeg, "-i", str(mkv), "-c:v", encoder, *enc_params,
               "-c:a", "copy", "-movflags", "+faststart", "-y", str(output)]

        process = subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            text=True, bufsize=1,
        )

        last_report = 0.0
        deadline = 3600.0
        import time as _time
        start = _time.monotonic()

        try:
            while True:
                if _time.monotonic() - start > deadline:
                    process.kill()
                    break
                r, _, _ = select.select([process.stderr], [], [], 1.0)
                if not r:
                    if process.poll() is not None:
                        break
                    continue
                line = process.stderr.readline()
                if not line:
                    break
                t = _parse_ffmpeg_time(line)
                if t is not None and total_duration and total_duration > 0:
                    pct = min(t / total_duration * 100, 99.9)
                    if pct - last_report >= 1.0:
                        last_report = pct
                        if progress_callback:
                            progress_callback({
                                "status": "progress",
                                "file": mkv.name,
                                "percent": pct,
                            })

            process.wait()
        except Exception:
            process.kill()
            process.wait()

        if process.returncode != 0:
            if progress_callback:
                progress_callback({"status": "error", "file": mkv.name})
            success = False
            continue

        if not keep_original:
            Path(mkv).unlink(missing_ok=True)

        if progress_callback:
            size = 0
            try:
                size = os.path.getsize(output)
            except OSError:
                pass
            progress_callback({
                "status": "done",
                "file": mkv.name,
                "output": str(output),
                "size": size,
            })

    return success
