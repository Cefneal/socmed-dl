"""CLI entry point for socmed-dl"""

import argparse
import os
import sys

from rich.console import Console

from socmed_dl import __version__
from socmed_dl.app import interactive, banner
from socmed_dl.config import load as load_config
from socmed_dl.downloader import Downloader
from socmed_dl.utils import check_deps, find_yt_dlp, default_downloads_dir
from socmed_dl.converter import convert_video

console = Console()


def show_help():
    console.print(banner(), style="bold cyan")
    print(f"""
Usage: socmed-dl [URL] [options]

Without URL: starts interactive TUI

Arguments:
  URL                  Video URL (YouTube, TikTok, IG, FB, Twitter, etc.)

Options:
  --audio, -a          Download audio only
  --audio-format       mp3|aac|flac|opus|wav  (default: mp3)
  --output, -o DIR     Output directory     (default: ~/Downloads)
  --cookies FILE       Cookies file for auth
  --proxy URL          HTTP/HTTPS proxy
  --list-formats       Show all formats with sizes and exit
  --format NUM         Download format # from --list-formats
  --version, -v        Show version
  --help, -h           Show this help

Examples:
  socmed-dl                                Interactive TUI
  socmed-dl "URL"                          720p → x265
  socmed-dl "URL" --audio                  Best audio → MP3
  socmed-dl "URL" --audio --audio-format flac
  socmed-dl "URL" --list-formats           Show sizes
  socmed-dl "URL" --format 3               Pick format #3
  socmed-dl "URL" --cookies cookies.txt    Auth required
""")
    sys.exit(0)


def main():
    if "-v" in sys.argv or "--version" in sys.argv:
        print(f"socmed-dl v{__version__}")
        return 0
    if "-h" in sys.argv or "--help" in sys.argv:
        show_help()

    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("url", nargs="?", default=None)
    parser.add_argument("--audio", "-a", action="store_true")
    parser.add_argument("--audio-format", default="mp3")
    parser.add_argument("--output", "-o", default=None)
    parser.add_argument("--cookies", default=None)
    parser.add_argument("--proxy", default=None)
    parser.add_argument("--list-formats", action="store_true")
    parser.add_argument("--format", type=int, default=None)

    args, _ = parser.parse_known_args()

    if not args.url:
        interactive()
        return 0

    deps = check_deps()
    if deps:
        console.print(f"[red]Missing: {', '.join(deps)}[/]")
        return 1

    cfg = load_config()
    dl = Downloader()
    outdir = args.output or cfg.get("output_dir") or default_downloads_dir()

    if args.list_formats:
        fmts, title, dur = dl.list_combined(args.url)
        print(f"\n  Title: {title}")
        print(f"  Formats:\n")
        for f in fmts:
            print(f"    #{f.num}  {f.height or 0:>4}p  {f.codec:4s}  {f.size_str:>8s}  "
                  f"{f.resolution}")
        return 0

    if args.format:
        fmts, title, dur = dl.list_combined(args.url)
        sel = next((f for f in fmts if f.num == args.format), None)
        if not sel:
            console.print(f"[red]Format #{args.format} not found[/]")
            return 1
    else:
        fmts, title, dur = dl.list_combined(args.url)
        sel = fmts[0] if fmts else None
        if not sel:
            console.print("[red]No formats found[/]")
            return 1

    progress = None
    task_id = None
    try:
        from rich.progress import Progress, BarColumn, TransferSpeedColumn, TimeRemainingColumn, SpinnerColumn, TextColumn
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(bar_width=None),
            "[progress.percentage]{task.percentage:>3.1f}%",
            TransferSpeedColumn(),
            TimeRemainingColumn(),
            console=console,
        )
        task_id = progress.add_task(f"[cyan]Downloading...[/]", total=None)

        def on_progress(dp):
            if dp.percent > 0:
                if progress.tasks[task_id].total is None:
                    progress.update(task_id, total=100)
                progress.update(task_id, completed=dp.percent)
            if dp.filename:
                progress.update(task_id, description=f"[cyan]{dp.filename[:50]}")

        dl.set_progress_callback(on_progress)
    except Exception:
        progress = None

    if args.audio:
        ok = dl.download_audio(args.url, outdir, args.audio_format)
    else:
        ok = dl.download_format(args.url, outdir, sel)

    if ok and not args.audio:
        convert_video(outdir)

    if ok:
        console.print(f"[green]✓ Saved to {outdir}[/]")
        return 0
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/]")
        sys.exit(130)
