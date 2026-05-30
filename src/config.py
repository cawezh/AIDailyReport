import os
import yaml
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_DIR = BASE_DIR / "config"


def load_yaml(name: str) -> dict:
    path = CONFIG_DIR / f"{name}.yaml"
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def get_keywords() -> dict[str, list[str]]:
    cfg = load_yaml("keywords")
    return cfg["categories"]


def get_sources() -> dict:
    return load_yaml("sources")


def get_env(name: str, default: str = "") -> str:
    return os.environ.get(name, default)
