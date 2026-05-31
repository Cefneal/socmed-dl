"""Interactive TUI — simple flow: URL → pick format → download"""

import os
import sys

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.progress import (
    BarColumn, Progress, SpinnerColumn, TextColumn,
    TimeRemainingColumn, TransferSpeedColumn,
)
from rich.table import Table
from rich.text import Text

from socmed_dl import __version__
from socmed_dl.config import load as load_config, save as save_config
from socmed_dl.downloader import Downloader
from socmed_dl.utils import (
    detect_platform, check_deps, format_size, format_duration,
    default_downloads_dir, platform_emoji, platform_color, find_yt_dlp,
)
from socmed_dl.converter import convert_video

console = Console()

AUDIO_FORMATS = {1: "mp3", 2: "aac", 3: "flac", 4: "opus", 5: "wav"}


def banner() -> str:
    return r"""
╔══════════════════════════════════════════════╗
║         ██╗  ██╗ ██████╗██╗███╗   ███╗      ║
║         ██║  ██║██╔════╝██║████╗ ████║      ║
║         ███████║██║     ██║██╔████╔██║      ║
║         ██╔══██║██║     ██║██║╚██╔╝██║      ║
║         ██║  ██║╚██████╗██║██║ ╚═╝ ██║      ║
║         ╚═╝  ╚═╝ ╚═════╝╚═╝╚═╝     ╚═╝      ║
║██████████████████████████████████████████████║
║      YouTube · TikTok · Instagram · FB       ║
║      Twitter · Reddit · Twitch · Vimeo       ║
╚══════════════════════════════════════════════╝
"""


def format_big_bits(tbr: float) -> str:
    return f"{tbr:.0f}k" if tbr else "-"


def interactive():
    console.clear()
    console.print(banner(), style="bold cyan")
    console.print(f"  [dim]v{__version__} • paste URL to start (or 'q' to quit)[/dim]\n")

    deps = check_deps()
    if deps:
        console.print(Panel(
            f"[red]Missing: {', '.join(deps)}[/red]\n"
            "[yellow]Quick install:[/yellow]\n"
            "  Linux/macOS:  curl -sL https://is.gd/socmed_dl | bash\n"
            "  Windows:      pip install socmed-dl yt-dlp",
            title="Error", border_style="red",
        ))
        return

    cfg = load_config()
    downloader = Downloader()

    url = Prompt.ask("[bold cyan]⊙ Paste video URL[/bold cyan]")
    if url.lower() in ("q", "quit", "exit"):
        console.print("[yellow]Bye![/yellow]")
        return

    platform = detect_platform(url)
    if platform == "unknown":
        if not Confirm.ask("[bold]⚠ Platform not recognized, try anyway?", default=True):
            return

    console.clear()
    console.print(banner(), style="bold cyan")

    # ── Fetch formats ─────────────────────────────────────────────────
    color = platform_color(platform)
    emoji = platform_emoji(platform)

    with console.status(f"[bold {color}]{emoji} Contacting {platform}...[/]", spinner="dots"):
        formats, title, duration = downloader.list_combined(url)

    if not formats:
        console.print("[red]No video formats found. The video may be private/age-restricted.[/red]")
        if Confirm.ask("[bold]Try with cookies file?", default=False):
            cookies = Prompt.ask("  Path to cookies.txt")
            with console.status("Retrying..."):
                formats, title, duration = downloader.list_combined(url, cookies_file=cookies)

    if not formats:
        console.print("[red]Still no formats available[/red]")
        return

    # ── Info bar ───────────────────────────────────────────────────────
    dur_str = format_duration(duration) if duration else "?"
    info = Text.assemble(
        (f" {emoji} ", f"bold {color}"),
        (f"{platform.upper()}", f"bold {color}"),
        ("  │  ", "dim"),
        (f"📹 {title[:60]}", "bold white"),
        ("  │  ", "dim"),
        (f"⏱ {dur_str}", "yellow"),
    )
    console.print(Panel(info, border_style=color))

    # ── Format table ───────────────────────────────────────────────────
    table = Table(box=box.SIMPLE_HEAVY, border_style="green", title="Select format")
    table.add_column("#", style="bold yellow", width=4)
    table.add_column("Quality", style="bold cyan", width=10)
    table.add_column("Resolution")
    table.add_column("Codec", style="green")
    table.add_column("Size", style="magenta", justify="right")
    table.add_column("FPS", justify="right")
    table.add_column("Bitrate", justify="right")

    for f in formats:
        label = f"{f.height}p" if f.height else "Auto"
        table.add_row(
            str(f.num),
            label,
            f.resolution,
            f.codec,
            f.size_str,
            str(f.fps) if f.fps else "-",
            format_big_bits(f.vbitrate),
        )

    console.print(table)

    # If only audio, add audio format row
    fmt_list = formats

    # ── Pick ───────────────────────────────────────────────────────────
    choice = IntPrompt.ask(
        "[bold cyan]Choose format (#)[/bold cyan]",
        default=1,
        choices=[str(f.num) for f in fmt_list],
    )
    selected = next((f for f in fmt_list if f.num == choice), fmt_list[0])

    # ── Audio mode? ────────────────────────────────────────────────────
    mode = "video"
    audio_fmt = "mp3"
    if selected.height == 0:
        mode = "audio"
        t = Table(box=box.ROUNDED, border_style="cyan")
        t.add_column("#", style="bold", width=4)
        t.add_column("Format", style="bold")
        for k, v in AUDIO_FORMATS.items():
            t.add_row(str(k), v)
        console.print(t)
        af = IntPrompt.ask("[bold cyan]Audio format[/]", default=1, choices=[str(k) for k in AUDIO_FORMATS])
        audio_fmt = AUDIO_FORMATS[af]

    # ── Output ─────────────────────────────────────────────────────────
    outdir = Prompt.ask(
        "[bold cyan]Save to[/bold cyan]",
        default=cfg.get("output_dir", default_downloads_dir()),
    )

    # Save as default
    if not cfg.get("output_dir") or outdir != default_downloads_dir():
        cfg["output_dir"] = outdir
        save_config(cfg)

    # ── Summary ────────────────────────────────────────────────────────
    est_size = format_size(selected.filesize) if selected.filesize else "?"
    summary = Table.grid(padding=(0, 2))
    summary.add_column(style="bold")
    summary.add_column()
    summary.add_row("Platform:", f"[bold {color}]{emoji} {platform.capitalize()}[/]")
    summary.add_row("File:", title[:60])
    summary.add_row("Quality:", f"{selected.height}p ({selected.resolution})")
    summary.add_row("Output:", outdir)
    summary.add_row("Est. size:", f"[magenta]{est_size}[/]")
    if mode == "video":
        summary.add_row("→ x265:", "[green]Auto convert[/green]")

    console.print(Panel(summary, title="Summary", border_style="green"))

    if not Confirm.ask("\n[bold green]▶ Start download?[/]", default=True):
        return

    # ── Download ───────────────────────────────────────────────────────
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

    downloader.set_progress_callback(on_progress)

    ok = False
    with progress:
        if mode == "video":
            ok = downloader.download_format(
                url, outdir, selected,
                cookies_file=cfg.get("cookies_file", ""),
                proxy=cfg.get("proxy", ""),
            )
        else:
            ok = downloader.download_audio(
                url, outdir, audio_fmt,
                cookies_file=cfg.get("cookies_file", ""),
            )

    # ── Convert ────────────────────────────────────────────────────────
    if ok and mode == "video":
        conv_task = progress.add_task("[green]Converting to x265...[/]", total=100)
        with progress:
            convert_video(outdir, progress_callback=lambda p: (
                progress.update(conv_task, completed=p.get("percent", 0))
                if p.get("status") != "done"
                else progress.update(conv_task, completed=100,
                                     description="[green]✓ Converted[/]")
            ))

    # ── Done ───────────────────────────────────────────────────────────
    console.print()
    if ok:
        size_str = format_size(os.path.getsize(
            os.path.join(outdir, f"{title}_x265.mkv") if mode == "video"
            else os.path.join(outdir, f"{title}.{audio_fmt}")
        )) if os.path.exists(os.path.join(outdir, f"{title}_x265.mkv") if mode == "video"
                            else os.path.join(outdir, f"{title}.{audio_fmt}")) else "?"
        console.print(Panel(
            f"[bold green]✓ Done![/]  [dim]{size_str}[/]",
            border_style="green",
        ))
    else:
        console.print(Panel("[red]Download failed![/]", border_style="red"))

    if Confirm.ask("\n[bold cyan]Download another?[/]", default=True):
        interactive()
