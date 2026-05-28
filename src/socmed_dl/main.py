"""Social Media Downloader TUI - YouTube, Facebook, Instagram
   Download video/audio in x265 (HEVC) from 144p to 1080p"""

import argparse
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.rule import Rule
from rich.table import Table

console = Console()

PLATFORMS = {
    "youtube": r"(youtube\.com|youtu\.be)",
    "facebook": r"(facebook\.com|fb\.watch|fb\.com)",
    "instagram": r"(instagram\.com|instagr\.am)",
}

QUALITY_MAP = {
    1: ("144p", 144),
    2: ("240p", 240),
    3: ("360p", 360),
    4: ("480p", 480),
    5: ("720p", 720),
    6: ("1080p", 1080),
}


def detect_platform(url: str) -> str:
    for platform, pattern in PLATFORMS.items():
        if re.search(pattern, url, re.IGNORECASE):
            return platform
    return "unknown"


def check_deps():
    missing = []
    yt_dlp = shutil.which("yt-dlp") or os.path.expanduser("~/.local/bin/yt-dlp")
    if not yt_dlp or not os.path.isfile(yt_dlp):
        missing.append("yt-dlp")
    if not shutil.which("ffmpeg"):
        missing.append("ffmpeg")
    return missing, yt_dlp


def print_banner():
    banner = r"""
╔══════════════════════════════════════════════╗
║         ██╗  ██╗ ██████╗██╗███╗   ███╗      ║
║         ██║  ██║██╔════╝██║████╗ ████║      ║
║         ███████║██║     ██║██╔████╔██║      ║
║         ██╔══██║██║     ██║██║╚██╔╝██║      ║
║         ██║  ██║╚██████╗██║██║ ╚═╝ ██║      ║
║         ╚═╝  ╚═╝ ╚═════╝╚═╝╚═╝     ╚═╝      ║
║           Social Media Downloader            ║
║      YouTube · Facebook · Instagram          ║
╚══════════════════════════════════════════════╝
"""
    console.print(banner, style="bold cyan")


def show_help():
    help_text = """
[bold yellow]Usage:[/bold yellow]
  socmed-dl [URL] [quality] [output-dir] [--audio]
  socmed-dl [URL] [output-dir] [--audio]

  If run without arguments, starts interactive TUI mode.

[bold yellow]Arguments:[/bold yellow]
  URL            Video URL from YouTube, Facebook, or Instagram
  quality        144|240|360|480|720|1080  (default: 720)
  output-dir     Download directory        (default: current dir)
  --audio, -a    Download audio only (MP3)

[bold yellow]Examples:[/bold yellow]
  socmed-dl "https://youtube.com/watch?v=..." 1080
  socmed-dl "https://youtube.com/watch?v=..." 1080 ~/Videos
  socmed-dl "https://facebook.com/..." --audio
  socmed-dl "https://instagram.com/..." 480
  socmed-dl -h  Show this help
"""
    console.print(Panel(help_text, title="Help", border_style="yellow"))
    sys.exit(0)


def select_quality_interactive() -> int:
    table = Table(title="Select Quality", box=box.ROUNDED, border_style="cyan")
    table.add_column("#", style="bold yellow", width=4)
    table.add_column("Quality", style="bold white")
    table.add_column("Max Height", style="dim")

    for key, (name, height) in QUALITY_MAP.items():
        table.add_row(str(key), name, f"{height}p")

    console.print(table)

    while True:
        try:
            choice = IntPrompt.ask(
                "[bold cyan]Choose quality[/bold cyan]",
                default=5,
                choices=[str(k) for k in QUALITY_MAP],
            )
            if choice in QUALITY_MAP:
                return QUALITY_MAP[choice][1]
        except (ValueError, KeyError):
            pass
        console.print("[red]Invalid choice. Please try again.[/red]")


def show_detected_info(platform: str, url: str):
    info = Table.grid(padding=(0, 1))
    info.add_column(style="bold")
    info.add_column()
    platform_colors = {"youtube": "red", "facebook": "blue", "instagram": "magenta"}
    color = platform_colors.get(platform, "white")
    info.add_row("Platform:", f"[bold {color}]◉ {platform.capitalize()}[/bold {color}]")
    info.add_row("URL:", f"[dim]{url[:80]}{'...' if len(url) > 80 else ''}[/dim]")
    console.print(Panel(info, title="Detected", border_style=color))


def run_download(
    yt_dlp_path: str,
    url: str,
    quality: int,
    mode: str,
    outdir: str,
) -> bool:
    os.makedirs(outdir, exist_ok=True)

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.1f}%",
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
    )

    if mode == "audio":
        console.print(f"\n[bold yellow]► Downloading audio...[/bold yellow]")
        cmd = [
            yt_dlp_path,
            url,
            "-f", "bestaudio/best",
            "--extract-audio",
            "--audio-format", "mp3",
            "--audio-quality", "0",
            "-o", f"{outdir}/%(title)s.%(ext)s",
            "--embed-metadata",
            "--no-playlist",
            "--progress",
            "--newline",
        ]
    else:
        console.print(f"\n[bold yellow]► Downloading video (max {quality}p) → x265[/bold yellow]")
        cmd = [
            yt_dlp_path,
            url,
            "-f", f"bestvideo[height<={quality}]+bestaudio/best[height<={quality}]",
            "--merge-output-format", "mkv",
            "-o", f"{outdir}/%(title)s.mkv",
            "--embed-metadata",
            "--no-playlist",
            "--newline",
        ]

    download_task = progress.add_task("[cyan]Downloading...", total=None)

    with progress:
        process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, bufsize=1,
        )

        for line in process.stdout or []:
            line = line.strip()
            if not line:
                continue
            if "%" in line:
                try:
                    pct_str = line.split("%")[0].split()[-1]
                    pct = float(pct_str.strip("%"))
                    if progress.tasks[download_task].total is None:
                        progress.update(download_task, total=100)
                    progress.update(download_task, completed=pct)
                except (ValueError, IndexError):
                    progress.advance(download_task)
            elif "Destination" in line:
                progress.update(download_task, description=f"[cyan]{line.split('/')[-1]}")

        process.wait()

    if process.returncode != 0:
        console.print("[red]Download failed![/red]")
        return False

    if mode == "video":
        return convert_to_x265(outdir)
    return True


def convert_to_x265(directory: str) -> bool:
    mkv_files = sorted(Path(directory).glob("*.mkv"))
    if not mkv_files:
        console.print("[yellow]No MKV files found to convert.[/yellow]")
        return True

    success = True
    for mkv in mkv_files:
        if "_x265" in mkv.name:
            continue
        output = mkv.parent / f"{mkv.stem}_x265{mkv.suffix}"

        console.print(
            f"\n[bold yellow]◉ Converting:[/bold yellow] [cyan]{mkv.name}[/cyan] → x265"
        )

        ffmpeg_progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.1f}%",
            TimeRemainingColumn(),
            console=console,
        )

        conv_task = ffmpeg_progress.add_task(
            f"[green]Encoding x265...[/green]", total=100
        )

        total_duration = None
        with ffmpeg_progress:
            proc = subprocess.Popen(
                [
                    "ffprobe", "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    str(mkv),
                ],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
            )
            dur_out, _ = proc.communicate()
            try:
                total_duration = float(dur_out.strip())
            except (ValueError, TypeError):
                total_duration = None

            cmd = [
                "ffmpeg",
                "-i", str(mkv),
                "-c:v", "libx265",
                "-crf", "28",
                "-preset", "medium",
                "-c:a", "aac",
                "-b:a", "128k",
                "-movflags", "+faststart",
                "-y",
                str(output),
            ]

            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1,
            )

            for line in process.stdout or []:
                line = line.strip()
                if total_duration and "time=" in line:
                    try:
                        time_str = line.split("time=")[1].split()[0]
                        parts = list(map(float, time_str.split(":")))
                        if len(parts) == 3:
                            current_time = parts[0] * 3600 + parts[1] * 60 + parts[2]
                            pct = min(99, int(current_time / total_duration * 100))
                            ffmpeg_progress.update(conv_task, completed=pct)
                    except (ValueError, IndexError):
                        pass
                elif "speed=" in line:
                    try:
                        speed_str = line.split("speed=")[1].split()[0]
                        ffmpeg_progress.update(
                            conv_task,
                            description=f"[green]Encoding x265... [{speed_str}][/green]",
                        )
                    except (IndexError, ValueError):
                        pass

            process.wait()

        if process.returncode == 0:
            ffmpeg_progress.update(conv_task, completed=100)
            console.print(f"  [green]✓ Saved: {output}[/green]")

            file_size = os.path.getsize(output)
            size_str = (
                f"{file_size / 1024 / 1024:.1f} MB"
                if file_size > 1024 * 1024
                else f"{file_size / 1024:.1f} KB"
            )
            console.print(f"  [dim]Size: {size_str}[/dim]")

            mkv.unlink(missing_ok=True)
        else:
            console.print(f"  [red]✗ Conversion failed for {mkv.name}[/red]")
            success = False

    return success


def interactive_mode():
    console.clear()
    print_banner()

    deps, yt_dlp_path = check_deps()
    if deps:
        console.print(
            Panel(
                f"[red]Missing dependencies: {', '.join(deps)}[/red]\n"
                "[yellow]Please install them:\n"
                "  yt-dlp: curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o ~/.local/bin/yt-dlp && chmod +x ~/.local/bin/yt-dlp\n"
                "  ffmpeg: sudo pacman -S ffmpeg[/yellow]",
                title="Error",
                border_style="red",
            )
        )
        return

    console.print(
        Panel(
            "[bold yellow]Interactive Downloader[/bold yellow]\n"
            "[dim]Enter a URL or type 'quit' to exit[/dim]",
            border_style="cyan",
        )
    )

    url = Prompt.ask("[bold cyan]⊙ Enter video URL[/bold cyan]")

    if url.lower() in ("quit", "exit", "q"):
        console.print("[yellow]Goodbye![/yellow]")
        return

    platform = detect_platform(url)
    if platform == "unknown":
        console.print(
            Panel(
                "[red]Unsupported platform![/red]\n"
                "[yellow]Supported: YouTube, Facebook, Instagram[/yellow]",
                border_style="red",
            )
        )
        if Confirm.ask("[bold]Try anyway?", default=False):
            platform = "unknown"
        else:
            return

    console.clear()
    print_banner()
    show_detected_info(platform, url)

    mode_table = Table(box=box.ROUNDED, border_style="cyan")
    mode_table.add_column("Option", style="bold yellow", width=6)
    mode_table.add_column("Mode", style="bold white")
    mode_table.add_row("1", "Video (x265)")
    mode_table.add_row("2", "Audio (MP3)")
    console.print(mode_table)

    mode_choice = IntPrompt.ask(
        "[bold cyan]Select mode[/bold cyan]", default=1, choices=["1", "2"]
    )
    mode = "video" if mode_choice == 1 else "audio"

    if mode == "video":
        height = select_quality_interactive()
    else:
        height = 0

    outdir = Prompt.ask(
        "[bold cyan]Output directory[/bold cyan]",
        default=os.getcwd(),
    )

    console.print()
    console.print(Rule(style="cyan"))

    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="bold")
    summary.add_column()
    summary.add_row("Platform:", f"[bold]{platform.capitalize()}[/bold]")
    summary.add_row("Mode:", f"[bold]{mode.upper()}[/bold]")
    if mode == "video":
        summary.add_row("Quality:", f"[bold]{height}p[/bold] → [green]x265[/green]")
    summary.add_row("Output:", f"[dim]{outdir}[/dim]")

    console.print(Panel(summary, title="Summary", border_style="green"))

    if not Confirm.ask("\n[bold green]Start download?[/bold green]", default=True):
        console.print("[yellow]Cancelled.[/yellow]")
        return

    success = run_download(yt_dlp_path, url, height, mode, outdir)

    console.print()
    if success:
        console.print(
            Panel(
                "[bold green]Download completed![/bold green]",
                border_style="green",
            )
        )
        if Confirm.ask("\n[bold cyan]Download another video?[/bold cyan]"):
            interactive_mode()
    else:
        console.print(
            Panel(
                "[red]Download failed![/red]",
                border_style="red",
            )
        )


def main():
    parser = argparse.ArgumentParser(
        description="Social Media Downloader - YouTube, Facebook, Instagram",
        add_help=False,
        usage="socmed-dl [URL] [quality|output-dir] [output-dir] [--audio]",
    )
    parser.add_argument("url", nargs="?", help="Video URL")
    parser.add_argument("opt1", nargs="?", default="720", help="Quality (144-1080) or output directory")
    parser.add_argument("opt2", nargs="?", default=None, help="Output directory (if opt1 is quality)")
    parser.add_argument("--audio", "-a", action="store_true", help="Download audio only")
    parser.add_argument("--help", "-h", action="store_true", help="Show help")
    parser.add_argument("--output", "-o", type=str, default=None, help="Output directory")

    args, _ = parser.parse_known_args()

    if args.help:
        show_help()
    if not args.url:
        interactive_mode()
        return

    deps, yt_dlp_path = check_deps()
    if deps:
        console.print(f"[red]Missing: {', '.join(deps)}[/red]")
        sys.exit(1)

    quality_map_v = {
        "144": 144, "144p": 144,
        "240": 240, "240p": 240,
        "360": 360, "360p": 360,
        "480": 480, "480p": 480,
        "720": 720, "720p": 720,
        "1080": 1080, "1080p": 1080,
    }

    quality_str = args.opt1
    outdir = "."
    if args.output:
        outdir = args.output
    elif args.opt2:
        quality_str = args.opt1
        outdir = args.opt2
    elif args.opt1 and args.opt1.lower() in quality_map_v:
        quality_str = args.opt1
    elif args.opt1:
        outdir = args.opt1

    quality = quality_map_v.get(str(quality_str).lower(), 720)
    mode = "audio" if args.audio else "video"

    success = run_download(yt_dlp_path, args.url, quality, mode, outdir)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(130)
