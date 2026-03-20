from __future__ import annotations

import json
import re
from collections import defaultdict
from pathlib import Path

import pandas as pd

from .analysis import load_works, write_analysis_outputs
from .config import (
    PROCESSED_DIR,
    RAW_DIR,
    ensure_directories,
    load_disease_dictionary,
    load_search_config,
    load_stopwords,
    load_synonyms_config,
    save_json,
)
from .figures import render_all_figures
from .io_utils import read_jsonl_gz, write_jsonl_gz
from .openalex import OpenAlexClient
from .text_processing import (
    apply_alias_replacements,
    build_alias_map,
    derive_focus_tags,
    display_term,
    find_disease_tags,
    join_pipe,
    match_patterns,
    normalize_text,
    period_label,
    reconstruct_abstract,
)


RAW_WORKS_PATH = RAW_DIR / "openalex_ahr_works.jsonl.gz"
FETCH_SUMMARY_PATH = RAW_DIR / "fetch_summary.csv"
WORKS_PATH = PROCESSED_DIR / "works.csv.gz"
CORPUS_SUMMARY_PATH = PROCESSED_DIR / "corpus_summary.json"


def fetch_data() -> None:
    ensure_directories()
    config = load_search_config()
    client = OpenAlexClient(
        base_url=config["api"]["base_url"],
        per_page=config["api"]["per_page"],
        mailto=config["api"]["mailto"],
        polite_sleep_seconds=config["api"]["polite_sleep_seconds"],
        max_retries=config["api"]["max_retries"],
    )
    filters = config["filters"]
    all_records: dict[str, dict] = {}
    summaries = []
    for query in config["queries"]:
        filter_expression = ",".join([query["filter"], *filters])
        count = 0
        for row in client.iter_query(filter_expression):
            work_id = row["id"]
            row["query_hits"] = sorted(set(row.get("query_hits", []) + [query["name"]]))
            if work_id in all_records:
                all_records[work_id]["query_hits"] = sorted(set(all_records[work_id]["query_hits"] + row["query_hits"]))
            else:
                all_records[work_id] = row
            count += 1
        summaries.append(
            {
                "query_name": query["name"],
                "filter_expression": filter_expression,
                "retrieved_rows_before_dedup": count,
                "rationale": query["rationale"],
            }
        )
    write_jsonl_gz(RAW_WORKS_PATH, all_records.values())
    pd.DataFrame(summaries).to_csv(FETCH_SUMMARY_PATH, index=False)


def _has_explicit_phrase(text: str, patterns: list[str]) -> bool:
    return any(pattern in text for pattern in patterns)


def _has_standalone_ahr(text: str) -> bool:
    return bool(re.search(r"\bahr\b(?!\s*\d)", text))


def _validated(record: dict, config: dict, title_text: str, abstract_text: str, metadata_text: str) -> tuple[bool, str]:
    validation = config["validation"]
    publication_year = int(record.get("publication_year") or 0)
    if publication_year < int(validation.get("minimum_publication_year", 0)):
        return False, "before_minimum_year"

    precise = [pattern.lower() for pattern in validation["precise_patterns"]]
    full_text = " ".join([title_text, abstract_text, metadata_text]).strip()
    has_exclusion = any(pattern in full_text for pattern in validation["exclude_patterns"])
    title_precise = _has_explicit_phrase(title_text, precise)
    abstract_precise = _has_explicit_phrase(abstract_text, precise)
    title_ahr = _has_standalone_ahr(title_text)
    title_has_anchor = any(anchor in title_text for anchor in validation["acronym_context_anchors"])

    if has_exclusion and not title_precise:
        return False, "excluded_non_biological_ahr_usage"
    if title_precise:
        return True, "explicit_title_match"
    if title_ahr and title_has_anchor and not has_exclusion:
        return True, "standalone_ahr_title_plus_anchor"
    if abstract_precise and title_has_anchor and not has_exclusion:
        return True, "abstract_phrase_with_anchor_title"
    return False, "failed_validation"


def preprocess_data() -> None:
    ensure_directories()
    search_config = load_search_config()
    synonyms_config = load_synonyms_config()
    disease_dictionary = load_disease_dictionary()
    stopwords = load_stopwords()
    alias_to_token, token_to_display = build_alias_map(synonyms_config)
    normalizations = synonyms_config.get("normalizations", {})

    rows = []
    for record in read_jsonl_gz(RAW_WORKS_PATH):
        title = record.get("title") or record.get("display_name") or ""
        abstract = reconstruct_abstract(record.get("abstract_inverted_index"))
        keywords = sorted(
            {
                keyword["display_name"]
                for keyword in (record.get("keywords") or [])
                if keyword.get("display_name") and keyword.get("score", 0) >= 0.35
            }
        )
        mesh_terms = sorted(
            {
                mesh["descriptor_name"]
                for mesh in (record.get("mesh") or [])
                if mesh.get("descriptor_name")
            }
        )
        topic_terms = sorted(
            {
                topic["display_name"]
                for topic in (record.get("topics") or [])
                if topic.get("display_name") and topic.get("score", 0) >= 0.35
            }
        )
        source_title = ((record.get("primary_location") or {}).get("source") or {}).get("display_name")
        countries = sorted({country for auth in (record.get("authorships") or []) for country in auth.get("countries", [])})
        institutions = sorted(
            {
                institution["display_name"]
                for auth in (record.get("authorships") or [])
                for institution in auth.get("institutions", [])
                if institution.get("display_name")
            }
        )
        title_norm = normalize_text(title, normalizations=normalizations)
        abstract_norm = normalize_text(abstract, normalizations=normalizations)
        metadata_blob = " ".join([" ".join(keywords), " ".join(mesh_terms)])
        metadata_norm = normalize_text(metadata_blob, normalizations=normalizations)
        classification_blob = " ".join([title_norm, abstract_norm, metadata_norm]).strip()
        analysis_blob = " ".join([title_norm, abstract_norm]).strip()
        is_valid, validation_reason = _validated(record, search_config, title_norm, abstract_norm, metadata_norm)
        if not is_valid:
            continue
        prepared_text = apply_alias_replacements(analysis_blob, alias_to_token)
        focus_tags = derive_focus_tags(classification_blob)
        disease_tags = find_disease_tags(classification_blob, disease_dictionary)
        rows.append(
            {
                "id": record["id"],
                "doi": record.get("doi") or "",
                "title": title,
                "abstract": abstract,
                "publication_year": int(record.get("publication_year")),
                "publication_date": record.get("publication_date") or "",
                "type": record.get("type") or "",
                "cited_by_count": int(record.get("cited_by_count") or 0),
                "source_title": source_title or "Unknown source",
                "language": record.get("language") or "",
                "countries": join_pipe(countries),
                "institutions": join_pipe(institutions),
                "keywords": join_pipe(keywords),
                "mesh_terms": join_pipe(mesh_terms),
                "topic_terms": join_pipe(topic_terms),
                "query_hits": join_pipe(record.get("query_hits", [])),
                "validation_reason": validation_reason,
                "normalized_text": classification_blob,
                "analysis_text": analysis_blob,
                "prepared_text": prepared_text,
                "focus_tags": join_pipe(focus_tags),
                "disease_tags": join_pipe(disease_tags),
                "time_slice": period_label(int(record["publication_year"]), search_config["time_slices"]),
            }
        )

    works = (
        pd.DataFrame(rows)
        .sort_values(["publication_year", "title"])
        .drop_duplicates(subset="id")
        .reset_index(drop=True)
    )
    works.to_csv(WORKS_PATH, index=False, compression="gzip")
    summary = {
        "n_papers": int(works["id"].nunique()),
        "year_min": int(works["publication_year"].min()),
        "year_max": int(works["publication_year"].max()),
        "n_with_abstract": int((works["abstract"].fillna("").str.len() > 0).sum()),
        "abstract_coverage": float((works["abstract"].fillna("").str.len() > 0).mean()),
        "top_focus_tags": works["focus_tags"].str.split("|").explode().replace("", pd.NA).dropna().value_counts().head(10).to_dict(),
    }
    save_json(CORPUS_SUMMARY_PATH, summary)


def analyze_data() -> dict:
    stopwords = load_stopwords()
    works = load_works(str(WORKS_PATH))
    return write_analysis_outputs(works, stopwords)


def render_figures() -> list[dict]:
    if not CORPUS_SUMMARY_PATH.exists():
        raise FileNotFoundError("Missing corpus summary; run preprocess first.")
    summary = json.loads(CORPUS_SUMMARY_PATH.read_text(encoding="utf-8"))
    return render_all_figures(summary)


def run_all() -> list[dict]:
    fetch_data()
    preprocess_data()
    analyze_data()
    return render_figures()
