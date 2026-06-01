"""CLI progress animations for downloads and conversions"""

from typing import Callable

from rich.console import Console, ConsoleOptions, RenderResult
from rich.live import Live
from rich.text import Text
from rich.progress_bar import ProgressBar
from rich.segment import Segment


_SPINNER_FRAMES = ["-", "\\", "|", "/"]


class _ProgressDisplay:
    def __init__(self, description: str = "", total: float = 100, color: str = "cyan"):
        self.description = description
        self.total = total
        self.completed = 0.0
        self.color = color
        self._spin = 0
        self._speed = ""
        self._eta = ""

    def update(self, completed: float, description: str | None = None, speed: str = "", eta: str = ""):
        self.completed = min(completed, self.total)
        if description is not None:
            self.description = description
        if speed:
            self._speed = speed
        if eta:
            self._eta = eta

    def _render_spinner(self) -> str:
        return _SPINNER_FRAMES[self._spin % len(_SPINNER_FRAMES)]

    def __rich_console__(self, console: Console, options: ConsoleOptions) -> RenderResult:
        self._spin += 1
        pct = self.completed / self.total * 100 if self.total > 0 else 0
        info = f"{pct:>5.1f}%"
        if self._speed:
            info += f"  {self._speed}"
        if self._eta:
            info += f"  ETA {self._eta}"
        spinner = self._render_spinner()

        bar = ProgressBar(self.completed, self.total, width=40)
        text = Text.assemble(
            (f"{spinner} ", self.color),
            (self.description[:50], self.color),
        )

        yield from (s for s in console.render(text) if s.text != "\n")
        yield Segment(" ")
        yield from (s for s in console.render(bar) if s.text != "\n")
        yield Segment(f" {info}")


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
    display = _ProgressDisplay(description="Downloading...", total=100, color=color)

    with Live(display, console=console, refresh_per_second=10, transient=True):
        def on_progress(dp):
            if dp.percent > 0:
                display.update(
                    completed=dp.percent,
                    description=dp.filename[:50] if dp.filename else "Downloading...",
                    speed=dp.speed,
                    eta=dp.eta,
                )

        result[0] = download_fn(on_progress)

    return result[0]


def animate_convert(
    convert_fn: Callable[[Callable], None],
    console: Console | None = None,
) -> bool:
    if console is None:
        console = Console()

    result = [False]
    display = _ProgressDisplay(description="Converting...", total=100, color="green")

    with Live(display, console=console, refresh_per_second=10, transient=True):
        def on_convert(p: dict):
            if p.get("status") == "progress":
                display.update(
                    completed=p.get("percent", 0),
                    description=f"Convert {p.get('file', '')[:40]}" if p.get("file") else "Converting...",
                )
            elif p.get("status") == "start":
                display.update(
                    completed=0,
                    description=f"Convert {p.get('file', '')[:40]}..." if p.get("file") else "Converting...",
                )
            elif p.get("status") == "done":
                display.update(completed=100, description="Convert complete")
                result[0] = True
            elif p.get("status") == "error":
                display.update(completed=0, description="Conversion failed")

        convert_fn(on_convert)

    return result[0]
