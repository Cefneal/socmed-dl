"""CLI entry point for socmed-dl"""

import argparse
import os
import sys

from rich.console import Console

from socmed_dl import __version__
from socmed_dl.app import interactive, banner
from socmed_dl.config import load as load_config
from socmed_dl.downloader import Downloader
from socmed_dl.utils import check_deps, find_yt_dlp

console = Console()


def show_help():
    help_text = """
[bold yellow]Usage:[/bold yellow]
  socmed-dl [URL] [quality] [output-dir] [options]

  Without arguments: starts interactive TUI

[bold yellow]Positional:[/bold yellow]
  URL            Video URL (YouTube, FB, IG, TikTok, Twitter, etc.)
  quality        144|240|360|480|720|1080  (default: 720)
  output-dir     Download directory        (default: .)

[bold yellow]Options:[/bold yellow]
  --audio, -a           Download audio only
  --audio-format        mp3|aac|flac|opus|wav  (default: mp3)
  --codec, -c           x265|x264|vp9|av1     (default: x265)
  --crf                 x265 quality 0-51     (default: 28)
  --preset              ultrafast|fast|medium|slow|veryslow  (default: medium)
  --cookies FILE        Cookies file for auth
  --proxy URL           HTTP/HTTPS proxy
  --concurrent, -j N    Concurrent downloads  (default: 1)
  --subs                Download subtitles
  --sub-lang LANG       Subtitle language    (default: en)
  --thumbnail           Embed thumbnail
  --keep-original       Keep original after conversion
  --no-convert          Skip x265 conversion
  --output-template     Output file template (default: %(title)s_%(height)s)
  --playlist            Download playlist
  --playlist-items ITEMS  Items to download  (e.g. 1-5,7)
  --playlist-reverse    Reverse playlist order
  --start-time MM:SS    Clip start time
  --end-time MM:SS      Clip end time
  --max-size SIZE       Max file size (e.g. 100M, 1G)
  --limit-rate RATE     Rate limit in MB/s  (e.g. 5)
  --dry-run             Show info without downloading
  --list-formats        List available formats and exit
  --version, -v         Show version
  --config KEY=VALUE    Override config (e.g. quality=1080)
  --help, -h            Show this help

[bold yellow]Examples:[/bold yellow]
  socmed-dl "https://youtube.com/watch?v=..." 1080 ~/Videos
  socmed-dl "https://youtube.com/playlist?list=..." --playlist --audio
  socmed-dl "https://facebook.com/..." 720 --codec x264
  socmed-dl "https://tiktok.com/..." --audio --audio-format flac
  socmed-dl URL1 URL2 URL3 --concurrent 3
  socmed-dl "https://youtube.com/..." --start-time 01:30 --end-time 03:00
  socmed-dl "https://youtube.com/..." --list-formats
  socmed-dl "https://youtube.com/..." --dry-run
  socmed-dl --config quality=1080 --config cookies_file=/path/to/cookies.txt
"""
    console.print(banner(), style="bold cyan")
    console.print(f"  [dim]v{__version__}[/dim]\n")
    console.print(help_text)
    sys.exit(0)


def main():
    parser = argparse.ArgumentParser(add_help=False, usage="socmed-dl [URL] [quality] [options]")
    parser.add_argument("url", nargs="+", help="Video URL(s)")
    parser.add_argument("--audio", "-a", action="store_true", help="Audio mode")
    parser.add_argument("--audio-format", default=None, help="Audio format")
    parser.add_argument("--codec", "-c", default=None, help="Video codec")
    parser.add_argument("--crf", type=int, default=None, help="CRF value")
    parser.add_argument("--preset", default=None, help="Encoding preset")
    parser.add_argument("--cookies", default=None, help="Cookies file")
    parser.add_argument("--proxy", default=None, help="Proxy URL")
    parser.add_argument("--concurrent", "-j", type=int, default=None, help="Concurrent downloads")
    parser.add_argument("--subs", action="store_true", default=None, help="Subtitles")
    parser.add_argument("--sub-lang", default=None, help="Subtitle language")
    parser.add_argument("--thumbnail", action="store_true", default=None, help="Embed thumbnail")
    parser.add_argument("--keep-original", action="store_true", default=None, help="Keep original")
    parser.add_argument("--no-convert", action="store_true", help="Skip conversion")
    parser.add_argument("--output-template", default=None, help="Output template")
    parser.add_argument("--playlist", action="store_true", help="Playlist mode")
    parser.add_argument("--playlist-items", default=None, help="Playlist items")
    parser.add_argument("--playlist-reverse", action="store_true", help="Reverse playlist")
    parser.add_argument("--start-time", default=None, help="Clip start")
    parser.add_argument("--end-time", default=None, help="Clip end")
    parser.add_argument("--max-size", default=None, help="Max file size")
    parser.add_argument("--limit-rate", default=None, help="Rate limit MB/s")
    parser.add_argument("--dry-run", action="store_true", help="Dry run")
    parser.add_argument("--list-formats", action="store_true", help="List formats")
    parser.add_argument("--version", "-v", action="store_true", help="Version")
    parser.add_argument("--config", action="append", default=[], help="Config KEY=VALUE")
    parser.add_argument("--help", "-h", action="store_true", help="Help")

    args, unknown = parser.parse_known_args()

    if args.help:
        show_help()
    if args.version:
        print(f"socmed-dl v{__version__}")
        sys.exit(0)

    # Interactive mode
    if not args.url:
        interactive()
        return 0

    # Config overrides
    cfg = load_config()
    for kv in args.config:
        if "=" in kv:
            k, v = kv.split("=", 1)
            cfg[k] = v

    # Parse positional arguments (URLs + optional quality + output)
    urls = args.url
    outdir = cfg.get("output_dir", ".")

    qmap = {"144": 144, "144p": 144, "240": 240, "240p": 240,
            "360": 360, "360p": 360, "480": 480, "480p": 480,
            "720": 720, "720p": 720, "1080": 1080, "1080p": 1080}

    quality = cfg.get("quality", 720)
    remaining = []
    for i, u in enumerate(urls):
        if u in qmap:
            quality = qmap[u]
        elif u.startswith("/") or u.startswith("~") or u.startswith(".") or ":" in u[:2] or (os.path.isdir(u.replace("~", os.path.expanduser("~")))):
            outdir = u
        else:
            remaining.append(u)
    urls = remaining or urls

    # CLI flags override config
    mode = "audio" if args.audio else cfg.get("mode", "video")
    codec = args.codec or cfg.get("codec", "x265")
    audio_fmt = args.audio_format or cfg.get("audio_format", "mp3")

    deps = check_deps()
    if deps:
        console.print(f"[red]Missing: {', '.join(deps)}[/]")
        return 1

    if args.list_formats:
        dl = Downloader()
        fmts = dl.list_formats(urls[0])
        if fmts:
            for f in fmts:
                print(f.display)
        else:
            print("No formats found")
        return 0

    dl = Downloader()
    for url in urls:
        ok = dl.download(
            url=url,
            outdir=outdir,
            quality=quality,
            codec=codec,
            mode=mode,
            audio_format=audio_fmt,
            cookies_file=args.cookies or cfg.get("cookies_file", ""),
            proxy=args.proxy or cfg.get("proxy", ""),
            concurrent=args.concurrent or cfg.get("concurrent", 1),
            output_template=args.output_template or cfg.get("output_template", "%(title)s_%(height)s"),
            playlist=args.playlist,
            playlist_items=args.playlist_items or cfg.get("playlist_items", ""),
            playlist_reverse=args.playlist_reverse or cfg.get("playlist_reverse", False),
            max_filesize=args.max_size or cfg.get("max_filesize", 0),
            rate_limit=args.limit_rate or cfg.get("rate_limit", 0),
            retry_count=cfg.get("retry_count", 3),
            retry_delay=cfg.get("retry_delay", 10),
            subtitles=args.subs if args.subs else cfg.get("subtitles", False),
            subtitle_lang=args.sub_lang or cfg.get("subtitle_lang", "en"),
            embed_thumbnail=args.thumbnail if args.thumbnail else cfg.get("embed_thumbnail", False),
            embed_metadata=cfg.get("embed_metadata", True),
            keep_original=args.keep_original if args.keep_original else cfg.get("keep_original", False),
            auto_convert=not args.no_convert,
            dry_run=args.dry_run,
        )
        if not ok:
            return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/]")
        sys.exit(130)
