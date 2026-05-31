"""x265 / codec conversion engine with hardware acceleration support"""

import os
import subprocess
from pathlib import Path
from typing import Callable

from socmed_dl.utils import find_ffmpeg, find_ffprobe, detect_hw_accel, hw_encoder_name


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

        if progress_callback:
            progress_callback({"status": "start", "file": mkv.name, "percent": 0})

        total_duration = None
        try:
            r = subprocess.run(
                [ffprobe, "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", str(mkv)],
                capture_output=True, text=True, timeout=15,
            )
            total_duration = float(r.stdout.strip())
        except (ValueError, TypeError, OSError):
            pass

        cmd = [ffmpeg, "-i", str(mkv), "-c:v", encoder, *enc_params,
               "-c:a", "copy", "-movflags", "+faststart", "-y", str(output)]

        try:
            r = subprocess.run(
                cmd, capture_output=True, text=True, timeout=3600,
            )
        except subprocess.TimeoutExpired:
            if progress_callback:
                progress_callback({"status": "error", "file": mkv.name})
            success = False
            continue

        if r.returncode != 0:
            error_msg = r.stderr[-300:] if r.stderr else "?"
            if progress_callback:
                progress_callback({"status": "error", "file": mkv.name})
            success = False
            continue

        if not keep_original:
            Path(mkv).unlink(missing_ok=True)

        if progress_callback:
            progress_callback({
                "status": "done",
                "file": mkv.name,
                "output": str(output),
                "size": os.path.getsize(output),
            })

    return success
