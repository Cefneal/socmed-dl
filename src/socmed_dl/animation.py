"""CLI progress animations for downloads and conversions"""

from typing import Callable

from rich.progress import (
    BarColumn, Progress, SpinnerColumn, TextColumn,
    TimeRemainingColumn, TransferSpeedColumn,
)
from rich.console import Console


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
        BarColumn(bar_width=40),
        "[progress.percentage]{task.percentage:>3.1f}%",
        TransferSpeedColumn(),
        TimeRemainingColumn(),
        console=console,
        transient=True,
    )

    dl_task = progress.add_task(f"[{color}]Downloading...[/]", total=None)

    def on_progress(dp):
        nonlocal dl_task
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
        BarColumn(bar_width=40),
        "[progress.percentage]{task.percentage:>3.1f}%",
        TimeRemainingColumn(),
        console=console,
        transient=True,
    )

    conv_task = progress.add_task("[green]Converting...", total=100)

    def on_convert(p: dict):
        if p.get("status") == "progress":
            progress.update(
                conv_task,
                completed=p.get("percent", 0),
                description=f"[green]Convert {p.get('file', '')[:35]}[/]",
            )
        elif p.get("status") == "start":
            progress.update(conv_task, total=100, completed=0, description=f"[green]Convert {p.get('file', '')[:35]}...")
        elif p.get("status") == "done":
            progress.update(conv_task, completed=100, description="[green]✓ Convert complete")
            result[0] = True
        elif p.get("status") == "error":
            progress.update(conv_task, description="[red]✗ Conversion failed")

    with progress:
        convert_fn(on_convert)

    return result[0]
