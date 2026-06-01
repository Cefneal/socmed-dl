"""CLI entry point for socmed-dl"""

import argparse
import os
import sys

from rich.console import Console

from socmed_dl import __version__
from socmed_dl.app import interactive, banner
from socmed_dl.config import load as load_config
from socmed_dl.downloader import Downloader, CODEC_INFO
from socmed_dl.utils import check_deps, find_yt_dlp, default_downloads_dir
from socmed_dl.converter import convert_video
from socmed_dl.animation import animate_download, animate_convert

console = Console()


def show_help():
    console.print(banner(), style="bold cyan")
    print(f"""
Usage: socmed-dl [URL] [options]

Without URL: starts interactive TUI

Arguments:
  URL                  Video URL

Options:
  --codec              Codec preference: x264, VP9, AV1  (default: best)
  --keep-original      Don't re-encode, keep original codec
  --to-x265            Convert to x265 (HEVC) after download
  --audio, -a          Download audio only
  --audio-format       mp3|aac|flac|opus|wav  (default: mp3)
  --output, -o DIR     Output directory     (default: ~/Downloads)
  --cookies FILE       Cookies file for auth
  --proxy URL          HTTP/HTTPS proxy
  --list-formats       Show all codecs + resolutions with sizes
  --format NUM         Download format # from --list-formats
  --version, -v        Show version
  --help, -h           Show this help

CLI flow (no auto convert):
  socmed-dl "URL"               Best format, no re-encode
  socmed-dl "URL" --to-x265     Best format → x265 convert
  socmed-dl "URL" --codec x264  Force x264, no re-encode
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
    parser.add_argument("--codec", default=None, help="x264, VP9, or AV1")
    parser.add_argument("--keep-original", action="store_true", help="No re-encode")
    parser.add_argument("--to-x265", action="store_true", help="Convert to x265")
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
        from socmed_dl.utils import format_duration
        dur_str = format_duration(dur) if dur else "?"
        print(f"\n  Title: {title}  ({dur_str})")
        codecs = dl.get_codecs(fmts)
        print(f"  Available codecs: {', '.join(codecs)}\n")
        for c in codecs:
            badge = {"VP9": "blue", "AV1": "yellow", "x264": "green", "x265": "red"}.get(c, "white")
            desc = CODEC_INFO.get(c, "")
            print(f"  [bold {badge}]{c}:[/] {desc}")
            print()
        print(f"    {'#':>3}  {'Quality':>7}  {'Codec':>6}  {'Size':>9}  {'Resolution':>12}")
        print(f"    {'─'*3}  {'─'*7}  {'─'*6}  {'─'*9}  {'─'*12}")
        for f in fmts:
            q = f.quality_label
            print(f"    {f.num:>3}  {q:>7}  {f.codec:>6}  {f.size_str:>9}  {f.resolution:>12}")
        return 0

    fmts, title, dur = dl.list_combined(args.url)
    if not fmts:
        console.print("[red]No formats found[/]")
        return 1

    sel = None
    if args.format:
        if args.codec:
            cfmts = Downloader.filter_by_codec(fmts, args.codec)
            sel = next((f for f in cfmts if f.num == args.format), None)
        else:
            sel = next((f for f in fmts if f.num == args.format), None)
        if not sel:
            console.print(f"[red]Format #{args.format} not found[/]")
            return 1
    elif args.codec:
        cfmts = Downloader.filter_by_codec(fmts, args.codec)
        if not cfmts:
            codecs = dl.get_codecs(fmts)
            console.print(f"[red]Codec '{args.codec}' not found. Available: {', '.join(codecs)}[/]")
            return 1
        sel = cfmts[0]
    else:
        sel = fmts[0]

    do_convert = args.to_x265 and not args.keep_original

    if args.audio:
        ok = animate_download(
            lambda cb: (dl.set_progress_callback(cb), dl.download_audio(
                args.url, outdir, args.audio_format))[1],
            title=title,
            console=console,
        )
        if ok:
            console.print(f"[green]✓ Audio saved to {outdir}[/]")
        return 0 if ok else 1

    ok = animate_download(
        lambda cb: (dl.set_progress_callback(cb), dl.download_format(args.url, outdir, sel))[1],
        title=title,
        console=console,
    )

    if ok and do_convert:
        console.print("[yellow]Converting to x265...[/]")
        animate_convert(
            lambda cb: convert_video(outdir, progress_callback=cb),
            console=console,
        )

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
