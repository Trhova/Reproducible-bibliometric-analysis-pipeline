from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml


PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "configs"
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
OUTPUT_DIR = PROJECT_ROOT / "output"
TABLE_DIR = OUTPUT_DIR / "tables"
FIGURE_DIR = OUTPUT_DIR / "figures"
METHODS_DIR = OUTPUT_DIR / "figure_methods"
REPORT_DIR = OUTPUT_DIR / "reports"
DEFAULT_PROJECT_CONFIG_PATH = CONFIG_DIR / "project.yaml"

_ACTIVE_PROJECT_CONFIG_PATH = DEFAULT_PROJECT_CONFIG_PATH


@dataclass(frozen=True)
class ProjectPaths:
    raw_records: Path
    fetch_summary: Path
    works: Path
    corpus_summary: Path
    cancer_stance_llm_cache: Path
    report_pdf: Path
    report_markdown: Path
    mermaid_flow: Path
    mermaid_markdown: Path


def set_active_project_config(path: str | Path | None) -> None:
    global _ACTIVE_PROJECT_CONFIG_PATH
    if path is None:
        _ACTIVE_PROJECT_CONFIG_PATH = DEFAULT_PROJECT_CONFIG_PATH
    else:
        _ACTIVE_PROJECT_CONFIG_PATH = Path(path).resolve()


def get_active_project_config_path() -> Path:
    return _ACTIVE_PROJECT_CONFIG_PATH


def ensure_directories() -> None:
    for directory in [RAW_DIR, PROCESSED_DIR, TABLE_DIR, FIGURE_DIR, METHODS_DIR, REPORT_DIR]:
        directory.mkdir(parents=True, exist_ok=True)


def load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


@lru_cache(maxsize=None)
def _load_project_config_cached(path_str: str) -> dict[str, Any]:
    return load_yaml(Path(path_str))


def load_project_config(path: str | Path | None = None) -> dict[str, Any]:
    config_path = Path(path).resolve() if path else get_active_project_config_path()
    return _load_project_config_cached(str(config_path))


def load_search_config() -> dict[str, Any]:
    project = load_project_config()
    return {
        "api": project["api"],
        "filters": project["search"]["filters"],
        "queries": project["search"]["queries"],
        "validation": project["search"]["validation"],
        "time_slices": project["analysis"]["time_slices"],
        "focus_subsets": project["analysis"].get("focus_subsets", {}),
    }


def load_synonyms_config() -> dict[str, Any]:
    text = load_project_config()["text_processing"]
    return {
        "normalizations": text.get("normalizations", {}),
        "aliases": text.get("aliases", {}),
    }


def load_disease_dictionary() -> dict[str, Any]:
    return load_project_config()["disease_dictionary"]


def load_stopwords() -> set[str]:
    stopwords = load_project_config()["text_processing"].get("stopwords", [])
    return {str(item).strip() for item in stopwords if str(item).strip()}


def project_paths(project_config: dict[str, Any] | None = None) -> ProjectPaths:
    config = project_config or load_project_config()
    prefix = config["project"]["output_prefix"]
    return ProjectPaths(
        raw_records=RAW_DIR / f"openalex_{prefix}_works.jsonl.gz",
        fetch_summary=RAW_DIR / "fetch_summary.csv",
        works=PROCESSED_DIR / "works.csv.gz",
        corpus_summary=PROCESSED_DIR / "corpus_summary.json",
        cancer_stance_llm_cache=PROCESSED_DIR / f"{prefix}_cancer_stance_llm_cache.json",
        report_pdf=REPORT_DIR / f"{prefix}_bibliometric_report.pdf",
        report_markdown=REPORT_DIR / f"{prefix}_bibliometric_report.md",
        mermaid_flow=REPORT_DIR / f"{prefix}_corpus_flow.mmd",
        mermaid_markdown=REPORT_DIR / f"{prefix}_corpus_flow.md",
    )


def save_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
