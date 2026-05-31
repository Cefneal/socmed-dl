"""Configuration management for socmed-dl"""

import json
import os
from pathlib import Path
from typing import Any

from socmed_dl.utils import default_downloads_dir

DEFAULT_CONFIG = {
    "quality": 720,
    "mode": "video",
    "codec": "x265",
    "audio_format": "mp3",
    "output_dir": default_downloads_dir(),
    "concurrent": 1,
    "crf": 28,
    "preset": "medium",
    "embed_metadata": True,
    "embed_thumbnail": False,
    "subtitles": False,
    "subtitle_lang": "en",
    "cookies_file": "",
    "proxy": "",
    "output_template": "%(title)s",
    "auto_convert": True,
    "keep_original": False,
    "max_filesize": 0,
    "rate_limit": 0,
    "retry_count": 3,
    "retry_delay": 10,
    "playlist_reverse": False,
    "playlist_items": "",
    "log_level": "INFO",
}


def config_dir() -> Path:
    xdg = os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")
    return Path(xdg) / "socmed-dl"


def config_file() -> Path:
    return config_dir() / "config.json"


def load() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    cf = config_file()
    if cf.exists():
        try:
            with open(cf) as f:
                user = json.load(f)
            cfg.update(user)
        except (json.JSONDecodeError, OSError):
            pass
    return cfg


def save(cfg: dict):
    cf = config_file()
    cf.parent.mkdir(parents=True, exist_ok=True)
    with open(cf, "w") as f:
        json.dump(cfg, f, indent=2)


def get(key: str, default=None) -> Any:
    return load().get(key, default)


def set_key(key: str, value: Any):
    cfg = load()
    cfg[key] = value
    save(cfg)
