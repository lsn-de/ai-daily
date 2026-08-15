"""配置加载：config.yaml + .env"""
import os
from datetime import date as date_cls
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

DEFAULTS: dict = {
    "fetch": {"hours": 24, "max_items_per_source": 30, "timeout": 20},
    "organize": {"min_reports": 4, "max_reports": 10, "max_items_in_prompt": 60},
    "rating": {"scale": 5, "criteria": []},
    "llm": {"model": "deepseek-chat", "temperature": 0.3, "max_tokens": 4096},
    "review": {"host": "127.0.0.1", "port": 7860},
    "data_dir": "data",
    "sources": [],
}


def load_config() -> dict:
    cfg_path = ROOT / "config.yaml"
    if not cfg_path.exists():
        cfg_path = ROOT / "config.example.yaml"
    user_cfg = {}
    if cfg_path.exists():
        user_cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    cfg = dict(DEFAULTS)
    for key, val in user_cfg.items():
        if isinstance(val, dict) and isinstance(cfg.get(key), dict):
            cfg[key].update(val)
        else:
            cfg[key] = val
    return cfg


def has_api_key() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def data_root(cfg: dict) -> Path:
    return ROOT / cfg["data_dir"]


def date_dirs(cfg: dict, day: str) -> dict:
    """返回某天的 raw / drafts / published 三个目录路径（自动创建）"""
    root = data_root(cfg)
    dirs = {
        "raw": root / "raw" / day,
        "drafts": root / "drafts" / day,
        "published": root / "published" / day,
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs


def today_str() -> str:
    return date_cls.today().isoformat()
