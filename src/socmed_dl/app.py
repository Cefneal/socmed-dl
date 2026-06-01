"""Interactive TUI — URL → mode → pick codec → pick res → convert? → done"""

import os
import sys

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.table import Table
from rich.text import Text

from socmed_dl import __version__
from socmed_dl.config import load as load_config, save as save_config
from socmed_dl.downloader import Downloader, CODEC_INFO
from socmed_dl.utils import (
    detect_platform, check_deps, format_size, format_duration,
    default_downloads_dir, platform_emoji, platform_color, find_yt_dlp,
)
from socmed_dl.converter import convert_video
from socmed_dl.animation import animate_download, animate_convert

console = Console()

AUDIO_FORMATS = {1: "mp3", 2: "aac", 3: "flac", 4: "opus", 5: "wav"}

CODEC_BADGES = {
    "VP9": "[bold blue]VP9[/]",
    "AV1": "[bold yellow]AV1[/]",
    "x264": "[bold green]x264[/]",
    "x265": "[bold red]x265[/]",
}

CONVERT_CHOICES = {
    1: ("x265", True),
    2: ("x264", True),
    3: ("keep original", False),
}


_SHADOW = [
    "███████╗ ██████╗ ███╗   ███╗███████╗██████╗ ██╗     ",
    "██╔════╝██╔═══██╗████╗ ████║██╔════╝██╔══██╗██║     ",
    "███████╗██║   ██║██╔████╔██║█████╗  ██║  ██║██║     ",
    "╚════██║██║   ██║██║╚██╔╝██║██╔══╝  ██║  ██║██║     ",
    "███████║╚██████╔╝██║ ╚═╝ ██║███████╗██████╔╝███████╗",
    "╚══════╝ ╚═════╝ ╚═╝     ╚═╝╚══════╝╚═════╝ ╚══════╝",
]

_PLATFORM_NAMES = [
    "YouTube · TikTok · Instagram · FB",
    "Twitter · Reddit · Twitch · Vimeo",
]

_SHADOW_W = max(len(l) for l in _SHADOW)  # 52
_BOX_W = _SHADOW_W + 2  # 54


def _box(console: Console) -> None:
    top = Text("╔" + "═" * _SHADOW_W + "╗", style="cyan")
    bottom = Text("╚" + "═" * _SHADOW_W + "╝", style="cyan")
    console.print(top, justify="center")
    for line in _SHADOW:
        t = Text()
        t.append("║", style="cyan")
        t.append(line, style="bold cyan")
        t.append("║", style="cyan")
        console.print(t, justify="center")
    console.print(bottom, justify="center")


def show_banner(console: Console) -> None:
    _box(console)
    console.print()
    for line in _PLATFORM_NAMES:
        console.print(f"[bold]{line}[/]", justify="center")
    console.print()
    console.print(f"[dim]v{__version__} • paste URL to start (or 'q' to quit)[/dim]", justify="center")


def show_centered(console: Console, extra_bottom: int = 0) -> None:
    h = console.height
    art_h = len(_SHADOW) + 2
    plat_h = len(_PLATFORM_NAMES)
    content = art_h + 1 + plat_h + 1 + 1 + 2 + extra_bottom
    pad = max(0, (h - content) // 2)
    for _ in range(pad):
        console.print()

    _box(console)
    console.print()
    for line in _PLATFORM_NAMES:
        console.print(f"[bold]{line}[/]", justify="center")
    console.print()
    console.print(f"[dim]v{__version__} • paste URL to start (or 'q' to quit)[/dim]", justify="center")
    console.print()


def chat_input(console: Console) -> str:
    cw = min(console.width - 4, _SHADOW_W + 20)
    left_pad = max(0, (console.width - cw) // 2)

    console.print(" " * left_pad + "╭" + "─" * (cw - 2) + "╮")

    label = "│  ⊙ Paste video URL:"
    label_pad = cw - 2 - len(label)
    console.print(" " * left_pad + label + " " * max(label_pad, 0) + " │")

    line = " " * left_pad + "│  " + " " * (cw - 5) + " │"
    sys.stdout.write(line)
    sys.stdout.write("\r" + " " * left_pad + "│  ")
    sys.stdout.flush()
    url = sys.stdin.readline().strip()

    sys.stdout.write("\r" + " " * left_pad + "│" + " " * (cw - 2) + "│\n")
    console.print(" " * left_pad + "╰" + "─" * (cw - 2) + "╝")
    return url


def format_big_bits(tbr: float) -> str:
    return f"{tbr:.0f}k" if tbr else "-"


def _quality_label(height: int) -> str:
    if height >= 2160: return "4K"
    if height >= 1440: return "1440p"
    if height >= 1080: return "1080p"
    if height >= 720:  return "720p"
    if height >= 480:  return "480p"
    if height >= 360:  return "360p"
    if height >= 240:  return "240p"
    if height >= 144:  return "144p"
    return f"{height}p" if height else "Audio"


def _sanitize_prefix(title: str) -> str:
    sanitized = ""
    for ch in title[:60]:
        if ch.isalnum() or ch in " ._-()[]":
            sanitized += ch
        else:
            sanitized += "_"
    return sanitized


def interactive():
    while True:
        console.clear()
        show_centered(console)

        deps = check_deps()
        if deps:
            console.print(Panel(
                f"[red]Missing: {', '.join(deps)}[/red]\n"
                "[yellow]Quick install:[/yellow]\n"
                "  Linux/macOS:  curl -sL https://is.gd/socmed_dl | bash\n"
                "  Windows:      winget install yt-dlp ffmpeg",
                title="Error", border_style="red",
            ))
            return

        cfg = load_config()
        downloader = Downloader()

        url = chat_input(console)
        if url.lower() in ("q", "quit", "exit"):
            console.print("[yellow]Bye![/yellow]")
            return

        platform = detect_platform(url)
        if platform == "unknown":
            if not Confirm.ask("[bold]⚠ Platform not recognized, try anyway?", default=True):
                continue

        color = platform_color(platform)
        emoji = platform_emoji(platform)

        console.clear()
        show_centered(console)
        console.print()

        with console.status(f"[bold {color}]{emoji} Fetching info from {platform}...[/]", spinner="dots"):
            formats, title, duration = downloader.list_combined(url)

        if not formats:
            console.print("[red]No formats found. The video may be private/age-restricted.[/red]")
            if Confirm.ask("[bold]Try with cookies file?", default=False):
                cookies = Prompt.ask("  Path to cookies.txt")
                with console.status("Retrying..."):
                    formats, title, duration = downloader.list_combined(url, cookies_file=cookies)

        if not formats:
            console.print("[red]Still no formats available[/red]")
            continue

        dur_str = format_duration(duration) if duration else "?"

        info = Panel(
            Text.assemble(
                (f" {emoji} ", f"bold {color}"),
                (f"{platform.upper()}", f"bold {color}"),
                ("  │  ", "dim"),
                (f"📹 {title[:60]}", "bold white"),
                ("  │  ", "dim"),
                (f"⏱ {dur_str}", "yellow"),
            ),
            border_style=color,
        )

        # ── Step 1: Mode ─────────────────────────────────────────────────
        console.print(info)
        console.print()
        mode_table = Table(box=box.MINIMAL_HEAVY_HEAD, border_style="cyan", show_header=False, padding=(0, 2))
        mode_table.add_column("#", style="bold yellow", width=4)
        mode_table.add_column("Mode", style="bold white")
        mode_table.add_row("[1]", "🎬  [bold]Video[/]  → pick codec + resolution")
        mode_table.add_row("[2]", "🎵  [bold]Audio[/] → MP3 / AAC / FLAC / Opus / WAV")
        mode_table.add_row("[3]", "📁  [bold]Both[/]   → video + audio separately")
        console.print(Panel(mode_table, title="[bold]What to download?[/]", border_style="cyan"))

        mode_choice = Prompt.ask("[bold cyan]Choose[/]", default="1", choices=["1", "2", "3"])
        is_video = mode_choice in ("1", "3")
        is_audio = mode_choice in ("2", "3")

        selected_video = None
        selected_audio_fmt = "mp3"

        # ── Step 2: Codec picker ─────────────────────────────────────────
        if is_video:
            console.clear()
            show_centered(console)
            console.print(info)

            codecs = downloader.get_codecs(formats)
            if not codecs:
                console.print("[red]No recognizable codecs found in formats[/red]")
                continue
            codec_choices = [str(i + 1) for i in range(len(codecs))]

            console.print(f"\n[bold]Pick a codec family:[/bold]")
            console.print()

            for i, c in enumerate(codecs):
                count = sum(1 for f in formats if f.codec == c)
                badge = CODEC_BADGES.get(c, c)
                desc = CODEC_INFO.get(c, "")
                console.print(
                    f"  [bold yellow]{i+1}.[/] {badge}  — {desc}"
                )
                console.print(f"      [dim]Available: {count} resolutions[/dim]")
                console.print()

            codec_idx = IntPrompt.ask(
                "[bold cyan]Choose codec[/]",
                default=1,
                choices=codec_choices,
            ) - 1
            selected_codec = codecs[codec_idx]

            # ── Step 3: Resolution picker (renumbered from 1!) ───────────
            console.clear()
            show_centered(console)
            console.print(info)

            codec_formats = Downloader.filter_by_codec(formats, selected_codec)
            badge = CODEC_BADGES.get(selected_codec, selected_codec)

            res_table = Table(
                box=box.SIMPLE_HEAVY,
                border_style="green",
                title=f"[bold]{badge} — available resolutions[/]",
                title_justify="left",
            )
            res_table.add_column("#", style="bold yellow", width=4)
            res_table.add_column("Quality", style="bold cyan", width=8)
            res_table.add_column("Resolution", style="white")
            res_table.add_column("Size", style="magenta", justify="right", width=10)
            res_table.add_column("FPS", justify="right", width=5)
            res_table.add_column("Bitrate", justify="right", width=8)

            for f in codec_formats:
                res_table.add_row(
                    str(f.num),
                    f.quality_label,
                    f.resolution,
                    f.size_str,
                    str(f.fps) if f.fps else "-",
                    format_big_bits(f.vbitrate),
                )

            console.print(res_table)

            size_note = {
                "x264": "[bold green]x264:[/] plays on everything, largest files",
                "VP9": "[bold blue]VP9:[/] great quality, medium files",
                "AV1": "[bold yellow]AV1:[/] best compression, needs modern device",
                "x265": "[bold red]x265:[/] HEVC, good compression",
            }.get(selected_codec, "")

            if size_note:
                console.print(f"  [dim]{size_note}[/dim]")

            res_choices = [str(f.num) for f in codec_formats]
            choice = IntPrompt.ask(
                f"[bold cyan]Choose {selected_codec} resolution (#)[/]",
                default=1,
                choices=res_choices,
            )
            selected_video = codec_formats[choice - 1]

        # ── Step 4: Convert choice (NO auto x265!) ──────────────────────
        do_convert = False
        convert_codec = ""

        if is_video and selected_video:
            console.clear()
            show_centered(console)
            console.print(info)

            console.print(f"\n[bold]Convert options for [green]{selected_video.quality_label}[/] [green]{selected_codec}[/]:[/]")
            console.print()

            convert_table = Table(box=box.MINIMAL_HEAVY_HEAD, border_style="yellow", show_header=False)
            convert_table.add_column("#", style="bold yellow", width=4)
            convert_table.add_column("Option", style="bold")
            convert_table.add_column("Note", style="dim")
            convert_table.add_row("[1]", "[bold red]x265[/] (HEVC)", "~50% smaller file, slower encode, newer devices")
            convert_table.add_row("[2]", "[bold green]x264[/] (AVC)", "plays on everything, fast encode, larger file")
            convert_table.add_row("[3]", "[bold white]Keep original[/]", f"keep as {selected_codec}, no re-encode")
            console.print(convert_table)
            console.print()

            conv_choice = Prompt.ask(
                "[bold cyan]Convert to?[/]",
                default="1",
                choices=["1", "2", "3"],
            )

            if conv_choice == "1":
                do_convert = True
                convert_codec = "x265"
            elif conv_choice == "2":
                do_convert = True
                convert_codec = "x264"
            else:
                do_convert = False
                convert_codec = selected_codec

        # ── Step 5: Audio format ─────────────────────────────────────────
        if is_audio:
            console.print()
            af_table = Table(box=box.MINIMAL_HEAVY_HEAD, border_style="magenta", show_header=False)
            af_table.add_column("#", style="bold yellow", width=4)
            af_table.add_column("Format", style="bold")
            af_table.add_column("Note", style="dim")
            notes = {"mp3": "Universal, best compat", "aac": "Apple ecosystem",
                     "flac": "Lossless, large", "opus": "Best quality/size", "wav": "Uncompressed"}
            for k, v in AUDIO_FORMATS.items():
                af_table.add_row(f"[{k}]", v.upper(), notes.get(v, ""))
            console.print(Panel(af_table, title="[bold]Audio format[/]", border_style="magenta"))
            af_choice = IntPrompt.ask(
                "[bold magenta]Choose audio format[/]",
                default=1,
                choices=[str(k) for k in AUDIO_FORMATS],
            )
            selected_audio_fmt = AUDIO_FORMATS[af_choice]

        # ── Step 6: Output dir ──────────────────────────────────────────
        outdir = Prompt.ask(
            "[bold cyan]Save to[/bold cyan]",
            default=cfg.get("output_dir", default_downloads_dir()),
        )

        if not cfg.get("output_dir") or outdir != default_downloads_dir():
            cfg["output_dir"] = outdir
            save_config(cfg)

        # ── Step 7: Summary ──────────────────────────────────────────────────
        console.clear()
        est_size = format_size(selected_video.filesize) if selected_video and selected_video.filesize else "~?"

        summary = Table.grid(padding=(0, 2))
        summary.add_column(style="bold", width=14)
        summary.add_column()
        summary.add_row("Platform", f"[bold {color}]{emoji}  {platform.capitalize()}[/]")
        summary.add_row("Title", title[:70])
        summary.add_row("Duration", dur_str)
        if is_video and selected_video:
            summary.add_row("Codec", CODEC_BADGES.get(selected_video.codec, selected_video.codec))
            summary.add_row("Quality", f"{selected_video.quality_label} ({selected_video.resolution})")
            summary.add_row("Est. size", f"[magenta]{est_size}[/magenta]")
            if do_convert:
                summary.add_row("→ Convert", f"[bold red]{convert_codec}[/] [dim](re-encode)[/dim]")
            else:
                summary.add_row("→ Keep", f"{selected_codec} [dim](no re-encode)[/dim]")
        if is_audio and mode_choice in ("2", "3"):
            summary.add_row("Audio format", f"[magenta]{selected_audio_fmt.upper()}[/]")
        summary.add_row("Output dir", f"[dim]{outdir}[/dim]")

        console.print(Panel(summary, title="[bold]Summary[/]", border_style="green"))

        if not Confirm.ask("\n[bold green]▶ Start download?", default=True):
            continue

        # ── Step 8: Download! ──────────────────────────────────────────────
        console.clear()
        ok = True
        convert_ok = True

        if is_video and selected_video:
            ok = animate_download(
                lambda cb: (
                    downloader.set_progress_callback(cb),
                    downloader.download_format(
                        url, outdir, selected_video,
                        cookies_file=cfg.get("cookies_file", ""),
                        proxy=cfg.get("proxy", ""),
                    )
                )[1],
                title=title,
                platform=platform,
                color=color,
                console=console,
            )

            if ok and do_convert:
                convert_ok = animate_convert(
                    lambda cb: convert_video(
                        outdir,
                        keep_original=cfg.get("keep_original", False),
                        crf=cfg.get("crf", 28),
                        preset=cfg.get("preset", "medium"),
                        progress_callback=cb,
                    ),
                    console=console,
                )

        if is_audio and mode_choice in ("2", "3"):
            ok = animate_download(
                lambda cb: (
                    downloader.set_progress_callback(cb),
                    downloader.download_audio(
                        url, outdir, selected_audio_fmt,
                        cookies_file=cfg.get("cookies_file", ""),
                    )
                )[1],
                title=title,
                platform=platform,
                color=color,
                console=console,
            )

        # ── Done ───────────────────────────────────────────────────────────
        if ok and convert_ok:
            found_files = []
            if os.path.isdir(outdir):
                prefix = _sanitize_prefix(title)
                found_files = [f for f in os.listdir(outdir) if f.startswith(prefix)]
            if found_files:
                try:
                    total = sum(os.path.getsize(os.path.join(outdir, f)) for f in found_files)
                    console.print(f"[green]✓ Download complete — {format_size(total)} total[/]")
                except OSError:
                    console.print("[green]✓ Download complete[/]")
            else:
                console.print("[green]✓ Download complete[/]")
        elif not ok:
            console.print(Panel("[red]Download failed![/]", border_style="red"))
        else:
            console.print(Panel("[red]Conversion failed![/]", border_style="red"))

        console.print()
        if not Confirm.ask("\n[bold cyan]Download another?", default=True):
            break
