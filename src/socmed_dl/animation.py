"""CLI animations — chibi characters, animated progress, fun download vibes"""

import random
import threading
import time
from typing import Callable

from rich.live import Live
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.text import Text
from rich.table import Table
from rich.console import Console, Group


_CHIBI_FRAMES = [
    r"""
     ∩( ・ω・)∩
    """,
    r"""
      ( ・ω・)
    """,
    r"""
     ( ・ω・)∩
    """,
    r"""
     ( ・ω・)
    """,
]

_DANCE_CHIBI = [
    r"""
      ♪┏(・o・)┛♪
    """,
    r"""
      ♪┗(・o・)┓♪
    """,
]

_WAVE_CHIBI = [
    r"""
    ( ´▽`)/✋
    """,
    r"""
    ＼(´▽`)/✋
    """,
]

_SLEEP_CHIBI = [
    r"""
     (　-ω-) 💤
    """,
    r"""
     (￣ρ￣).zz💤
    """,
]

_HAPPY_CHIBI = [
    r"""
      ＼(^▽^)／
    """,
    r"""
      (ﾉ◕ヮ◕)ﾉ
    """,
    r"""
      \(★ω★)/
    """,
]

_DOWNLOAD_CHIBI = [
    r"""
     (◕‿◕)✧
     ↓↓↓↓↓
    """,
    r"""
     (◕‿◕)✧
     ╰⋃╯
    """,
    r"""
     (◕‿◕)✧
     📥📥📥
    """,
]

_CONVERT_CHIBI = [
    r"""
     (｀ω´)
     ⚙️⚙️⚙️
    """,
    r"""
     (｀ω´)
     🔄🔄🔄
    """,
]

_PAW_FRAMES = ["(´･ω･`)" , "(｀・ω・´)" , "（・ω・）" , "(・ω・)☀" , "₍˄·͈༝·͈˄₎"]
_RUNNING_CAT = ["ᓚᘏᗢ", "ᓚₒᘏᗢ", "ᓚₒᘏᗢ", "ᓚᘏᗢ"]

# ── Apple-style download progress frames ──────────────────────────────
_PROGRESS_FRAMES = [
    "▱▱▱▱▱▱▱▱▱▱",
    "▰▱▱▱▱▱▱▱▱▱",
    "▰▰▱▱▱▱▱▱▱▱",
    "▰▰▰▱▱▱▱▱▱▱",
    "▰▰▰▰▱▱▱▱▱▱",
    "▰▰▰▰▰▱▱▱▱▱",
    "▰▰▰▰▰▰▱▱▱▱",
    "▰▰▰▰▰▰▰▱▱▱",
    "▰▰▰▰▰▰▰▰▱▱",
    "▰▰▰▰▰▰▰▰▰▱",
    "▰▰▰▰▰▰▰▰▰▰",
]

_PLATFORM_KITS = {
    "youtube": "▶️🎬",
    "facebook": "👍📘",
    "instagram": "📸🌈",
    "tiktok": "🎵💃",
    "twitter": "🐦🔥",
    "reddit": "🤖👽",
    "twitch": "📺🎮",
    "vimeo": "🎥🎞",
    "dailymotion": "🎬🎭",
    "tumblr": "💬✨",
}


def _breathe() -> str:
    return random.choice(_PAW_FRAMES)


def _progress_bar(percent: float, width: int = 20) -> str:
    filled = int(width * percent / 100)
    bar = "█" * filled + "░" * (width - filled)
    return bar


class ChibiProgress:
    def __init__(self, console: Console):
        self.console = console
        self._stop = False
        self._current_desc = ""
        self._percent = 0.0
        self._speed = ""
        self._eta = ""
        self._state = "idle"

    def start(self, description: str = ""):
        self._stop = False
        self._current_desc = description

    def update(self, percent: float = 0, speed: str = "", eta: str = "", description: str = ""):
        self._percent = percent
        if speed: self._speed = speed
        if eta: self._eta = eta
        if description: self._current_desc = description

    def set_state(self, state: str):
        self._state = state

    def stop(self):
        self._stop = True

    def get_renderable(self) -> Panel:
        if self._state == "download":
            chibi = _DOWNLOAD_CHIBI[int(time.time() * 2) % len(_DOWNLOAD_CHIBI)]
        elif self._state == "convert":
            chibi = _CONVERT_CHIBI[int(time.time() * 2) % len(_CONVERT_CHIBI)]
        elif self._state == "connecting":
            chibi = _WAVE_CHIBI[int(time.time() * 3) % len(_WAVE_CHIBI)]
        else:
            chibi = _CHIBI_FRAMES[int(time.time() * 2) % len(_CHIBI_FRAMES)]

        bar = _progress_bar(self._percent)
        info = Table.grid(padding=(0, 2))
        info.add_column(style="bold", width=12)
        info.add_column()
        info.add_row("Status", f"[cyan]{self._current_desc}[/]")
        info.add_row("Progress", f"[green]{bar}[/] [bold]{self._percent:.1f}%[/]")
        if self._speed:
            info.add_row("Speed", f"[yellow]{self._speed}[/]")
        if self._eta:
            info.add_row("ETA", f"[magenta]{self._eta}[/]")

        return Panel(
            Group(f"[bold cyan]{chibi}[/]", info),
            border_style="cyan",
            title="[bold]socmed-dl[/]",
            title_align="left",
        )


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

    conv_task = progress.add_task("[green]Converting to x265...", total=1)

    def on_convert(p: dict):
        if p.get("status") == "start":
            progress.update(conv_task, total=1, description=f"[green]Convert {p.get('file', '')}...")
            progress.update(conv_task, completed=0)
        elif p.get("status") == "done":
            progress.update(conv_task, completed=1, description="[green]✓ Converted to x265")
            result[0] = True
        elif p.get("status") == "error":
            progress.update(conv_task, description="[red]✗ Conversion failed")

    with progress:
        convert_fn(on_convert)

    return result[0]


def success_animation(console: Console, title: str = "", size: str = ""):
    for i in range(4):
        console.clear()
        frame = _HAPPY_CHIBI[i % len(_HAPPY_CHIBI)]
        console.print(f"\n\n[bold green]{frame}[/]")
        console.print(f"\n[bold green]  ✓ Download Complete![/]")
        if title:
            console.print(f"  [white]{title[:55]}[/]")
        if size:
            console.print(f"\n  [yellow]╭{'─'*25}╮")
            console.print(f"  │  File size: [bold]{size}[/bold]  │")
            console.print(f"  ╰{'─'*25}╯")

        stars = "✨" * (i + 1)
        console.print(f"\n  [bold yellow]{stars}[/]")
        time.sleep(0.4)

    console.clear()
    console.print(f"\n\n[bold green]  (ﾉ◕ヮ◕)ﾉ  Done! ヽ(◕ヮ◕ヽ)[/]")
    if size:
        console.print(f"\n  [yellow]File size: {size}[/]")
    time.sleep(0.5)


def happy_start(console: Console):
    console.print(Panel(
        Text.assemble(
            ("  ᕦ(ò_óˇ)ᕤ  ", "bold cyan"),
            ("socmed-dl ready to download!", "white"),
        ),
        border_style="cyan",
    ))


def connecting_animation(console: Console, platform: str, color: str = "cyan"):
    kit = _PLATFORM_KITS.get(platform.lower(), "🌐")
    for i in range(3):
        console.clear()
        frame = _WAVE_CHIBI[i % len(_WAVE_CHIBI)]
        console.print(f"\n\n\n[bold {color}]{frame}[/]")
        dots = "." * (i + 1)
        console.print(f"\n[bold {color}]  ~ Connecting to {platform}{dots} ~[/]")
        console.print(f"\n[dim]  {kit}  [/dim]")
        time.sleep(0.35 + i * 0.1)


def show_progress_card(
    console: Console,
    percent: float,
    description: str = "",
    speed: str = "",
    eta: str = "",
    platform: str = "",
):
    chibi = _breathe()
    bar = _progress_bar(percent)
    console.clear()

    info = Table.grid(padding=(0, 2))
    info.add_column(style="bold", width=12)
    info.add_column()
    info.add_row("Status", f"[cyan]{description}[/]")
    info.add_row("Progress", f"[green]{bar}[/] [bold]{percent:.1f}%[/]")
    if speed:
        info.add_row("Speed", f"[yellow]{speed}[/]")
    if eta:
        info.add_row("ETA", f"[magenta]{eta}[/]")

    console.print(Panel(
        Group(f"[bold cyan]{chibi}[/]", info),
        border_style="cyan",
        title=f"[bold]{' 📥 ' if 'Download' in description else ' 🔄 '} {platform}[/]",
    ))
