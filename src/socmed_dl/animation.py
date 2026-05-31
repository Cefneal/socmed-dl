"""CLI animations — anime ASCII art characters for download/convert/success"""

import time
from typing import Callable

from rich.panel import Panel
from rich.progress import (
    BarColumn, Progress, SpinnerColumn, TextColumn,
    TimeRemainingColumn, TransferSpeedColumn,
)
from rich.console import Console

# ── Anime-style ASCII art frames (NO emoji) ──────────────────────────

_CONNECT_FRAMES = [
    r"""
     ∩( ・ω・)∩
     ~ connecting
    """,
    r"""
     ( ・ω・)∩
     ~ connecting.
    """,
    r"""
     ( ・ω・)
     ~ connecting..
    """,
    r"""
     ( ・ω・)∩
     ~ connecting...
    """,
]

_DOWNLOAD_FRAMES = [
    r"""
     ╭( ・ω・)╮
    ╭┻━━━━┻╮
    ┃ ▌╭╮  ┃
    ╰┳━━━━┳╯
    """,
    r"""
     ╭( ・ω・)╮
    ╭┻━━━━┻╮
    ┃ ▌╭╮▌ ┃
    ╰┳━━━━┳╯
    """,
    r"""
     ╭(｀・ω・´)╮
    ╭┻━━━━┻╮
    ┃ ▌╭╮▌ ┃
    ╰┳━━━━┳╯
    """,
    r"""
     ╭(｀・ω・´)╮
    ╭┻━━━━┻╮
    ┃ ▌╭╮▌ ┃
    ╰┳━━━━┳╯
    """,
]

_CONVERT_FRAMES = [
    r"""
     (｀・ω・´)
      ╔════╗
      ║ ██ ║
      ╚════╝
    """,
    r"""
     (｀・ω・´)
      ╔════╗
      ║ ██ ║
      ╚════╝
       ░░░
    """,
    r"""
     (｀・ω・´)
      ╔════╗
      ║ ██ ║
      ╚════╝
      ░░░░
    """,
    r"""
     (｀・ω・´)
      ╔════╗
      ║ ██ ║
      ╚════╝
     ░░░░░
    """,
]

_SUCCESS_FRAMES = [
    r"""
      ＼(^▽^)／
       ／＼
    """,
    r"""
      ／(^▽^)＼
      ＼ ／
    """,
    r"""
      ＼(^▽^)／
       ／＼
    """,
]

_DANCE_FRAMES = [
    r"""
      ♪┏(・o・)┛♪
    """,
    r"""
      ♪┗(・o・)┓♪
    """,
]

_IDLE_FRAMES = [
    r"""
     (　・ω・)
    """,
    r"""
     (　・ω・)∩
    """,
    r"""
     (　・ω・)
    """,
    r"""
      (　・ω・)∩
    """,
]

_PLATFORM_KITS = {
    "youtube": "▶", "facebook": "f", "instagram": "@", "tiktok": "♪",
    "twitter": "♯", "reddit": "r/", "twitch": "📺", "vimeo": "▷",
    "dailymotion": "▷", "tumblr": "t",
}


def _frames(base, duration=0.25):
    """Generator that cycles through frames."""
    i = 0
    while True:
        yield base[i % len(base)]
        i += 1
        time.sleep(duration)


def _progress_bar(percent: float, width: int = 20) -> str:
    filled = int(width * percent / 100)
    bar = "█" * filled + "░" * (width - filled)
    return bar


def animate_download(
    download_fn: Callable[[Callable], None],
    title: str = "",
    platform: str = "",
    color: str = "cyan",
    console: Console | None = None,
) -> bool:
    if console is None:
        console = Console()

    result = [False]

    progress = Progress(
        SpinnerColumn(spinner_name="dots", style=color),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.1f}%",
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
    )

    dl_task = progress.add_task(f"[{color}]Downloading...[/]", total=None)

    def on_progress(dp):
        if dp.percent > 0:
            if progress.tasks[dl_task].total is None:
                progress.update(dl_task, total=100)
            progress.update(dl_task, completed=dp.percent)
        if dp.filename:
            progress.update(dl_task, description=f"[{color}]{dp.filename[:45]}")

    with progress:
        result[0] = download_fn(on_progress)

    return result[0]


def animate_convert(
    convert_fn: Callable[[Callable], None],
    console: Console | None = None,
) -> bool:
    if console is None:
        console = Console()

    result = [False]

    progress = Progress(
        SpinnerColumn(spinner_name="dots", style="green"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(bar_width=None),
        "[progress.percentage]{task.percentage:>3.1f}%",
        console=console,
    )

    conv_task = progress.add_task("[green]Converting...", total=1)

    def on_convert(p: dict):
        if p.get("status") == "start":
            progress.update(conv_task, total=1, description=f"[green]Convert {p.get('file', '')}...")
            progress.update(conv_task, completed=0)
        elif p.get("status") == "done":
            progress.update(conv_task, completed=1, description="[green]✓ Convert complete")
            result[0] = True
        elif p.get("status") == "error":
            progress.update(conv_task, description="[red]✗ Conversion failed")

    with progress:
        convert_fn(on_convert)

    return result[0]


def success_animation(console: Console, title: str = "", size: str = ""):
    for i in range(4):
        console.clear()
        frame = _SUCCESS_FRAMES[i % len(_SUCCESS_FRAMES)]
        console.print(f"\n\n[bold green]{frame}[/]")
        console.print(f"\n[bold green]  ✓ Download Complete![/]")
        if title:
            console.print(f"  [white]{title[:55]}[/]")
        if size:
            console.print(f"\n  [yellow]╭{'─'*25}╮")
            console.print(f"  │  File size: [bold]{size}[/bold]  │")
            console.print(f"  ╰{'─'*25}╯")
        time.sleep(0.4)

    # Final dance
    for _ in range(2):
        for f in _DANCE_FRAMES:
            console.clear()
            console.print(f"\n\n[bold green]{f}[/]")
            console.print(f"\n[bold green]  (ﾉ ・ω・)ﾉ  Done! ヽ(・ω・ヽ)[/]")
            if size:
                console.print(f"\n  [yellow]File size: {size}[/]")
            time.sleep(0.3)


def happy_start(console: Console):
    console.print(Panel(
        r"""
  ╭( ・ω・)╮
  socmed-dl ready!
""",
        border_style="cyan",
    ))


def connecting_animation(console: Console, platform: str, color: str = "cyan"):
    kit = _PLATFORM_KITS.get(platform.lower(), "?")
    for i in range(3):
        console.clear()
        frame = _CONNECT_FRAMES[i % len(_CONNECT_FRAMES)]
        console.print(f"\n\n[bold {color}]{frame}[/]")
        dots = "." * (i + 1)
        console.print(f"\n[bold {color}]  [{kit}] Connecting to {platform}{dots}[/]")
        time.sleep(0.35 + i * 0.1)


def show_progress_card(
    console: Console,
    percent: float,
    description: str = "",
    speed: str = "",
    eta: str = "",
    platform: str = "",
):
    bar = _progress_bar(percent)
    frame = _IDLE_FRAMES[int(time.time() * 2) % len(_IDLE_FRAMES)]
    console.clear()
    console.print(f"\n[bold cyan]{frame}[/]")
    console.print(f"  Status: [cyan]{description}[/]")
    console.print(f"  [green]{bar}[/] [bold]{percent:.1f}%[/]")
    if speed:
        console.print(f"  Speed: [yellow]{speed}[/]")
    if eta:
        console.print(f"  ETA: [magenta]{eta}[/]")
