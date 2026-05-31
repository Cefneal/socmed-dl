"""Interactive TUI application for socmed-dl"""

import os
import re
import sys

from rich import box
from rich.console import Console, Group
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.progress import (
    BarColumn, Progress, SpinnerColumn, TextColumn,
    TimeRemainingColumn, TransferSpeedColumn,
)
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

from socmed_dl import __version__
from socmed_dl.config import load as load_config, save as save_config
from socmed_dl.downloader import Downloader, FormatInfo
from socmed_dl.utils import (
    detect_platform, check_deps, format_size, format_duration, find_yt_dlp,
)
from socmed_dl.converter import convert_to_x265

console = Console()

QUALITY_OPTIONS = {1: 144, 2: 240, 3: 360, 4: 480, 5: 720, 6: 1080}
CODEC_OPTIONS = {1: "x265", 2: "x264", 3: "vp9", 4: "av1"}
AUDIO_FORMATS = {1: "mp3", 2: "aac", 3: "flac", 4: "opus", 5: "wav"}
PLATFORM_COLORS = {
    "youtube": "red", "facebook": "blue", "instagram": "magenta",
    "tiktok": "cyan", "twitter": "white", "reddit": "orange1",
    "twitch": "purple", "vimeo": "bright_blue", "dailymotion": "yellow",
    "tumblr": "bright_magenta",
}


def banner() -> str:
    return r"""
╔══════════════════════════════════════════════╗
║         ██╗  ██╗ ██████╗██╗███╗   ███╗      ║
║         ██║  ██║██╔════╝██║████╗ ████║      ║
║         ███████║██║     ██║██╔████╔██║      ║
║         ██╔══██║██║     ██║██║╚██╔╝██║      ║
║         ██║  ██║╚██████╗██║██║ ╚═╝ ██║      ║
║         ╚═╝  ╚═╝ ╚═════╝╚═╝╚═╝     ╚═╝      ║
║           Social Media Downloader            ║
║      YouTube · Facebook · Instagram          ║
║      TikTok · Twitter · Reddit · Twitch      ║
╚══════════════════════════════════════════════╝
"""


def _make_quality_table() -> Table:
    t = Table(box=box.ROUNDED, border_style="cyan")
    t.add_column("#", style="bold yellow", width=4)
    t.add_column("Quality", style="bold white")
    t.add_column("Max Height", style="dim")
    for k, v in QUALITY_OPTIONS.items():
        t.add_row(str(k), f"{v}p", f"{v}p")
    return t


def _make_codec_table() -> Table:
    t = Table(box=box.ROUNDED, border_style="cyan")
    t.add_column("#", style="bold yellow", width=4)
    t.add_column("Codec", style="bold white")
    t.add_column("Description", style="dim")
    t.add_row("1", "x265 (HEVC)", "Best compression, ~50% smaller than x264")
    t.add_row("2", "x264 (AVC)", "Widest compatibility")
    t.add_row("3", "VP9", "Google codec, good quality")
    t.add_row("4", "AV1", "Best quality, but slow encoding")
    return t


def interactive():
    console.clear()
    console.print(banner(), style="bold cyan")
    console.print(f"  [dim]v{__version__} • Type 'quit' to exit[/dim]\n")

    deps = check_deps()
    if deps:
        console.print(Panel(
            f"[red]Missing: {', '.join(deps)}[/red]\n"
            "[yellow]Install:\n"
            "  yt-dlp: curl -L https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp -o ~/.local/bin/yt-dlp && chmod +x ~/.local/bin/yt-dlp\n"
            "  ffmpeg: sudo pacman -S ffmpeg / winget install FFmpeg / brew install ffmpeg[/yellow]",
            title="Error", border_style="red",
        ))
        return

    cfg = load_config()
    downloader = Downloader()

    # ── URL input ──────────────────────────────────────────────────────
    url_raw = Prompt.ask("[bold cyan]⊙ Enter URL(s)[/bold cyan]")
    if url_raw.lower() in ("quit", "exit", "q"):
        console.print("[yellow]Goodbye![/yellow]")
        return

    urls = [u.strip() for u in re.split(r'[,\s]+', url_raw) if u.strip()]
    is_playlist = len(urls) > 1
    url = urls[0]

    platform = detect_platform(url)
    if platform == "unknown":
        if not Confirm.ask("[bold]Unsupported platform, try anyway?", default=False):
            return

    console.clear()
    console.print(banner(), style="bold cyan")

    # Info panel
    pc = PLATFORM_COLORS.get(platform, "white")
    info = Table.grid(padding=(0, 2))
    info.add_column(style="bold")
    info.add_column()
    info.add_row("Platform:", f"[bold {pc}]◉ {platform.capitalize()}[/]")
    info.add_row("URLs:", f"[dim]{len(urls)} URL(s)[/]")
    if is_playlist:
        info.add_row("Mode:", "[bold yellow]Batch mode[/]")
    console.print(Panel(info, title="Detected", border_style=pc))

    # ── List formats with sizes ─────────────────────────────────────────
    if Confirm.ask("[bold]Show available formats with sizes?", default=False):
        with console.status("[cyan]Fetching formats..."):
            fmts = downloader.list_formats(url)
        if fmts:
            t = Table(title="Available Formats", box=box.ROUNDED, border_style="green")
            t.add_column("ID", style="cyan")
            t.add_column("Resolution")
            t.add_column("Ext")
            t.add_column("Size", style="yellow")
            t.add_column("Codec", style="magenta")
            t.add_column("Bitrate")
            t.add_column("FPS")
            for f in fmts:
                if not f.resolution or f.resolution == "audio":
                    continue
                t.add_row(
                    f.id, f.resolution, f.ext,
                    format_size(f.filesize) if f.filesize else "~?",
                    (f.vcodec or "").split(".")[0],
                    f"{f.tbr:.0f}k",
                    str(f.fps) if f.fps else "",
                )
            console.print(t)
        else:
            console.print("[yellow]Could not fetch formats[/yellow]")

    # ── Mode ────────────────────────────────────────────────────────────
    mode_t = Table(box=box.ROUNDED, border_style="cyan")
    mode_t.add_column("#", style="bold yellow", width=6)
    mode_t.add_column("Mode", style="bold white")
    mode_t.add_row("1", "Video → x265/AV1/VP9")
    mode_t.add_row("2", "Audio (MP3/FLAC/Opus)")
    console.print(mode_t)
    mc = IntPrompt.ask("[bold cyan]Select mode[/]", default=1, choices=["1", "2"])
    mode = "video" if mc == 1 else "audio"

    height = 720
    codec = "x265"
    audio_fmt = "mp3"

    if mode == "video":
        console.print(_make_quality_table())
        height = QUALITY_OPTIONS.get(
            IntPrompt.ask("[bold cyan]Quality[/]", default=5, choices=[str(k) for k in QUALITY_OPTIONS]),
            720,
        )
        console.print(_make_codec_table())
        codec = CODEC_OPTIONS.get(
            IntPrompt.ask("[bold cyan]Codec[/]", default=1, choices=[str(k) for k in CODEC_OPTIONS]),
            "x265",
        )
    else:
        t = Table(box=box.ROUNDED, border_style="cyan")
        t.add_column("#", style="bold yellow", width=4)
        t.add_column("Format", style="bold white")
        t.add_column("Desc", style="dim")
        for k, v in AUDIO_FORMATS.items():
            descs = {"mp3": "Universal", "aac": "Apple", "flac": "Lossless", "opus": "Efficient", "wav": "Uncompressed"}
            t.add_row(str(k), v, descs.get(v, ""))
        console.print(t)
        audio_fmt = AUDIO_FORMATS.get(
            IntPrompt.ask("[bold cyan]Audio format[/]", default=1, choices=[str(k) for k in AUDIO_FORMATS]),
            "mp3",
        )

    # ── Extra options ───────────────────────────────────────────────────
    extras = {}
    if Confirm.ask("[bold]Configure advanced options?", default=False):
        extras["concurrent"] = IntPrompt.ask("  Concurrent downloads", default=cfg.get("concurrent", 1))
        extras["cookies_file"] = Prompt.ask("  Cookies file (enter path or leave blank)", default=cfg.get("cookies_file", ""))
        extras["proxy"] = Prompt.ask("  Proxy (http://... or leave blank)", default=cfg.get("proxy", ""))
        extras["subtitles"] = Confirm.ask("  Download subtitles?", default=cfg.get("subtitles", False))
        extras["embed_thumbnail"] = Confirm.ask("  Embed thumbnail?", default=cfg.get("embed_thumbnail", False))
        extras["keep_original"] = Confirm.ask("  Keep original file after conversion?", default=False)
        if Confirm.ask("  Trim clip?", default=False):
            extras["start_time"] = Prompt.ask("    Start (MM:SS)", default="00:00")
            extras["end_time"] = Prompt.ask("    End (MM:SS)", default="")

    outdir = Prompt.ask(
        "[bold cyan]Output directory[/]",
        default=cfg.get("output_dir", "."),
    )

    # ── Save config ─────────────────────────────────────────────────────
    if Confirm.ask("[dim]Save these settings as default?[/]", default=False):
        cfg["quality"] = height
        cfg["codec"] = codec
        cfg["mode"] = mode
        cfg["audio_format"] = audio_fmt
        cfg["output_dir"] = outdir
        save_config(cfg)
        console.print("[green]Settings saved![/]")

    # ── Summary ─────────────────────────────────────────────────────────
    console.print()
    console.print(Rule(style="cyan"))
    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="bold")
    summary.add_column()
    summary.add_row("Mode:", f"[bold]{mode.upper()}[/]")
    if mode == "video":
        summary.add_row("Quality:", f"{height}p  →  [green]{codec}[/]")
    else:
        summary.add_row("Format:", f"[green]{audio_fmt}[/]")
    summary.add_row("Output:", f"[dim]{outdir}[/]")
    if extras.get("concurrent", 1) > 1:
        summary.add_row("Jobs:", f"{extras['concurrent']}")
    console.print(Panel(summary, title="Summary", border_style="green"))

    if not Confirm.ask("\n[bold green]▶ Start?[/]", default=True):
        return

    # ── Download loop ───────────────────────────────────────────────────
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.1f}%",
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
    )

    for i, u in enumerate(urls, 1):
        if len(urls) > 1:
            console.print(f"\n[bold]━━─ {i}/{len(urls)} ─ {u[:60]} ─[/]")

        task_id = progress.add_task(f"[cyan]{u[:50]}...", total=None)

        def mk_cb(tid):
            def cb(dp):
                if hasattr(dp, "percent") and dp.percent > 0:
                    if progress.tasks[tid].total is None:
                        progress.update(tid, total=100)
                    progress.update(tid, completed=dp.percent, description=f"[cyan]{dp.filename or u[:40]}...[/]")
                elif hasattr(dp, "filename") and dp.filename:
                    progress.update(tid, description=f"[cyan]{dp.filename[:50]}[/]")
            return cb

        downloader.set_progress_callback(mk_cb(task_id))

        with progress:
            ok = downloader.download(
                url=u,
                outdir=outdir,
                quality=height,
                codec=codec,
                mode=mode,
                audio_format=audio_fmt,
                cookies_file=extras.get("cookies_file", ""),
                proxy=extras.get("proxy", ""),
                concurrent=extras.get("concurrent", 1),
                subtitles=extras.get("subtitles", False),
                embed_thumbnail=extras.get("embed_thumbnail", False),
                keep_original=extras.get("keep_original", False),
            )

        if ok and mode == "video":
            conv_task = progress.add_task("[green]Converting to x265...[/]", total=100)
            with progress:
                convert_to_x265(
                    outdir,
                    keep_original=extras.get("keep_original", False),
                    progress_callback=lambda p: (
                        progress.update(conv_task, completed=p.get("percent", 0))
                        if p.get("status") != "done"
                        else progress.update(conv_task, completed=100, description="[green]Done[/]")
                    ),
                )

        if ok:
            progress.update(task_id, completed=100, description=f"[green]✓ {u[:40]}[/]")
        else:
            progress.update(task_id, description=f"[red]✗ {u[:40]}[/]")

    # ── Done ────────────────────────────────────────────────────────────
    console.print()
    console.print(Panel("[bold green]All done![/]", border_style="green"))
    if Confirm.ask("\n[bold cyan]Download again?[/]"):
        interactive()
