from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "configs"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
TABLE_DIR = PROJECT_ROOT / "output" / "tables"
FIGURE_DIR = PROJECT_ROOT / "output" / "figures"
METHODS_DIR = PROJECT_ROOT / "output" / "figure_methods"


def ensure_directories() -> None:
    for directory in [RAW_DIR, PROCESSED_DIR, TABLE_DIR, FIGURE_DIR, METHODS_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def load_search_config() -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "search_queries.yaml")


def load_synonyms_config() -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "synonyms.yaml")


def load_disease_dictionary() -> dict[str, Any]:
    return load_yaml(CONFIG_DIR / "disease_dictionary.yaml")


def load_stopwords() -> set[str]:
    path = CONFIG_DIR / "stopwords_terms.txt"
    with path.open("r", encoding="utf-8") as handle:
        return {line.strip() for line in handle if line.strip() and not line.startswith("#")}


def save_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)

