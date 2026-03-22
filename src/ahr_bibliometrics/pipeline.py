from __future__ import annotations

import json
import re

import pandas as pd

from .analysis import load_works, write_analysis_outputs
from .config import (
    ensure_directories,
    load_disease_dictionary,
    load_project_config,
    load_search_config,
    load_stopwords,
    load_synonyms_config,
    project_paths,
    save_json,
)
from .figures import render_all_figures
from .io_utils import read_jsonl_gz, write_jsonl_gz
from .openalex import OpenAlexClient
from .reporting import build_summary_report
from .text_processing import (
    apply_alias_replacements,
    build_alias_map,
    derive_focus_tags,
    find_disease_tags,
    join_pipe,
    normalize_text,
    period_label,
    reconstruct_abstract,
)


def fetch_data() -> None:
    ensure_directories()
    config = load_project_config()
    search_config = load_search_config()
    paths = project_paths(config)
    client = OpenAlexClient(
        base_url=config["api"]["base_url"],
        per_page=config["api"]["per_page"],
        mailto=config["api"]["mailto"],
        polite_sleep_seconds=config["api"]["polite_sleep_seconds"],
        max_retries=config["api"]["max_retries"],
    )
    filters = search_config["filters"]
    all_records: dict[str, dict] = {}
    summaries = []
    for query in search_config["queries"]:
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
    write_jsonl_gz(paths.raw_records, all_records.values())
    pd.DataFrame(summaries).to_csv(paths.fetch_summary, index=False)


def _has_literal_phrase(text: str, patterns: list[str]) -> bool:
    return any(pattern in text for pattern in patterns)


def _has_regex_match(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text) for pattern in patterns)


def _validated(record: dict, validation: dict, title_text: str, abstract_text: str, metadata_text: str) -> tuple[bool, str]:
    publication_year = int(record.get("publication_year") or 0)
    if publication_year < int(validation.get("minimum_publication_year", 0)):
        return False, "before_minimum_year"

    exact_patterns = [pattern.lower() for pattern in validation.get("exact_phrase_patterns", [])]
    acronym_patterns = validation.get("acronym_patterns", [])
    anchor_patterns = [pattern.lower() for pattern in validation.get("acronym_context_anchors", [])]
    exclude_patterns = [pattern.lower() for pattern in validation.get("exclude_patterns", [])]
    full_text = " ".join([title_text, abstract_text, metadata_text]).strip()

    has_exclusion = any(pattern in full_text for pattern in exclude_patterns)
    title_exact = _has_literal_phrase(title_text, exact_patterns)
    abstract_exact = _has_literal_phrase(abstract_text, exact_patterns)
    title_acronym = _has_regex_match(title_text, acronym_patterns)
    title_has_anchor = any(anchor in title_text for anchor in anchor_patterns)

    if has_exclusion and not title_exact:
        return False, "excluded_non_target_acronym_usage"
    if title_exact:
        return True, "explicit_title_match"
    if title_acronym and title_has_anchor and not has_exclusion:
        return True, "standalone_acronym_title_plus_anchor"
    if abstract_exact and title_has_anchor and not has_exclusion:
        return True, "abstract_phrase_with_anchor_title"
    return False, "failed_validation"


def preprocess_data() -> None:
    ensure_directories()
    config = load_project_config()
    search_config = load_search_config()
    synonyms_config = load_synonyms_config()
    disease_dictionary = load_disease_dictionary()
    paths = project_paths(config)
    alias_to_token, _ = build_alias_map(synonyms_config)
    normalizations = synonyms_config.get("normalizations", {})
    focus_tag_patterns = config["text_processing"].get("focus_tag_patterns", {})

    rows = []
    for record in read_jsonl_gz(paths.raw_records):
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
        is_valid, validation_reason = _validated(record, search_config["validation"], title_norm, abstract_norm, metadata_norm)
        if not is_valid:
            continue
        prepared_text = apply_alias_replacements(analysis_blob, alias_to_token)
        focus_tags = derive_focus_tags(classification_blob, focus_tag_patterns)
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
    works.to_csv(paths.works, index=False, compression="gzip")

    fetch_summary = pd.read_csv(paths.fetch_summary) if paths.fetch_summary.exists() else pd.DataFrame()
    total_retrieved = int(fetch_summary["retrieved_rows_before_dedup"].sum()) if not fetch_summary.empty else 0
    summary = {
        "project_name": config["project"]["name"],
        "project_short_name": config["project"]["short_name"],
        "corpus_name": config["project"]["corpus_name"],
        "output_prefix": config["project"]["output_prefix"],
        "query_summary": config["project"]["query_summary"],
        "n_papers": int(works["id"].nunique()),
        "year_min": int(works["publication_year"].min()),
        "year_max": int(works["publication_year"].max()),
        "n_with_abstract": int((works["abstract"].fillna("").str.len() > 0).sum()),
        "abstract_coverage": float((works["abstract"].fillna("").str.len() > 0).mean()),
        "n_with_disease_tags": int((works["disease_tags"].fillna("") != "").sum()),
        "disease_tag_coverage": float((works["disease_tags"].fillna("") != "").mean()),
        "n_with_focus_tags": int((works["focus_tags"].fillna("") != "").sum()),
        "focus_tag_coverage": float((works["focus_tags"].fillna("") != "").mean()),
        "n_records_retrieved_before_dedup": total_retrieved,
        "n_unique_candidates_after_dedup": int(sum(1 for _ in read_jsonl_gz(paths.raw_records))),
        "top_focus_tags": works["focus_tags"].str.split("|").explode().replace("", pd.NA).dropna().value_counts().head(10).to_dict(),
    }
    save_json(paths.corpus_summary, summary)


def analyze_data() -> dict:
    stopwords = load_stopwords()
    works = load_works(str(project_paths().works))
    return write_analysis_outputs(works, stopwords)


def render_figures(include: set[str] | None = None) -> list[dict]:
    paths = project_paths()
    if not paths.corpus_summary.exists():
        raise FileNotFoundError("Missing corpus summary; run preprocess first.")
    summary = json.loads(paths.corpus_summary.read_text(encoding="utf-8"))
    return render_all_figures(summary, include=include)


def generate_report() -> str:
    render_figures(include={"figure_00_corpus_flow_summary"})
    return str(build_summary_report())


def run_all() -> list[dict]:
    fetch_data()
    preprocess_data()
    analyze_data()
    figures = render_figures()
    build_summary_report()
    return figures
