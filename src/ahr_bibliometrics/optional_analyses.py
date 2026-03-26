from __future__ import annotations

from collections import Counter
import math
import re

import numpy as np
import pandas as pd

from .config import load_project_config, load_synonyms_config
from .text_processing import normalize_text, parse_pipe_list


STANCE_DISPLAY_LABELS = {
    "pro_tumor": "Pro-tumor framing",
    "anti_tumor": "Anti-tumor framing",
    "mixed_context": "Mixed / context-dependent",
    "unclear": "Unclear",
}


def cancer_stance_settings() -> dict:
    return (
        load_project_config()
        .get("analysis", {})
        .get("optional_products", {})
        .get("cancer_stance", {})
    )


def phrase_map_settings() -> dict:
    return (
        load_project_config()
        .get("analysis", {})
        .get("optional_products", {})
        .get("phrase_map", {})
    )


def stance_display_label(key: str) -> str:
    return STANCE_DISPLAY_LABELS.get(key, key.replace("_", " ").title())


def extract_phrase_hits(text: str, phrase_patterns: dict[str, list[str]]) -> list[str]:
    hits = []
    for phrase, patterns in phrase_patterns.items():
        if any(re.search(pattern, text) for pattern in patterns):
            hits.append(phrase)
    return sorted(set(hits))


def _pipe_overlap(value: str, targets: set[str]) -> bool:
    if not targets:
        return False
    return bool(set(parse_pipe_list(value)) & targets)


def cancer_subset_mask(works: pd.DataFrame, settings: dict | None = None) -> pd.Series:
    settings = settings or cancer_stance_settings()
    subset = settings.get("subset", {})
    focus_targets = set(subset.get("focus_tags", []))
    disease_targets = set(subset.get("disease_tags", []))
    return works.apply(
        lambda row: _pipe_overlap(row.get("focus_tags", ""), focus_targets)
        or _pipe_overlap(row.get("disease_tags", ""), disease_targets),
        axis=1,
    )


def _normalize_stance_text(text: str) -> str:
    normalizations = load_synonyms_config().get("normalizations", {})
    return normalize_text(text or "", normalizations=normalizations)


def _clean_optional_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, float) and pd.isna(value):
        return ""
    text = str(value).strip()
    return "" if text.lower() == "nan" else text


def _marker_hits(text: str, marker_map: dict[str, list[str]]) -> list[str]:
    hits = []
    for name, patterns in marker_map.items():
        if any(re.search(pattern, text) for pattern in patterns):
            hits.append(name)
    return hits


def classify_stance_text(
    *,
    title_text: str,
    abstract_text: str,
    settings: dict | None = None,
) -> dict[str, str | int | float]:
    settings = settings or cancer_stance_settings()
    markers = settings.get("rule_markers", {})
    title_norm = _normalize_stance_text(title_text)
    abstract_norm = _normalize_stance_text(abstract_text)
    use_title_fallback = bool(settings.get("use_title_fallback", True))

    def evaluate(text: str) -> dict[str, list[str]]:
        return {
            "pro_tumor": _marker_hits(text, markers.get("pro_tumor", {})),
            "anti_tumor": _marker_hits(text, markers.get("anti_tumor", {})),
            "mixed_context": _marker_hits(text, markers.get("mixed_context", {})),
        }

    def summarize(hit_map: dict[str, list[str]], source: str) -> dict[str, str | int | float]:
        pro_hits = hit_map["pro_tumor"]
        anti_hits = hit_map["anti_tumor"]
        mixed_hits = hit_map["mixed_context"]
        if mixed_hits or (pro_hits and anti_hits):
            label = "mixed_context"
            confidence = "high" if mixed_hits or min(len(pro_hits), len(anti_hits)) >= 1 else "moderate"
        elif pro_hits:
            label = "pro_tumor"
            confidence = "high" if len(pro_hits) >= 2 else "moderate"
        elif anti_hits:
            label = "anti_tumor"
            confidence = "high" if len(anti_hits) >= 2 else "moderate"
        else:
            label = "unclear"
            confidence = "low"
        return {
            "rule_label": label,
            "rule_display_label": stance_display_label(label),
            "rule_confidence": confidence,
            "rule_source": source,
            "pro_marker_count": len(pro_hits),
            "anti_marker_count": len(anti_hits),
            "mixed_marker_count": len(mixed_hits),
            "pro_markers": " | ".join(pro_hits),
            "anti_markers": " | ".join(anti_hits),
            "mixed_markers": " | ".join(mixed_hits),
        }

    abstract_hits = evaluate(abstract_norm) if abstract_norm else {"pro_tumor": [], "anti_tumor": [], "mixed_context": []}
    abstract_result = summarize(abstract_hits, "abstract" if abstract_norm else "none")
    if abstract_result["rule_label"] != "unclear" or not use_title_fallback:
        return abstract_result

    title_hits = evaluate(title_norm) if title_norm else {"pro_tumor": [], "anti_tumor": [], "mixed_context": []}
    title_result = summarize(title_hits, "title_fallback" if title_norm else "none")
    if title_result["rule_label"] != "unclear":
        return title_result
    return abstract_result


def _year_bin_label(year: int, year_min: int, year_max: int, width: int) -> str:
    bin_start = year_min + ((year - year_min) // width) * width
    bin_end = min(bin_start + width - 1, year_max)
    return f"{bin_start}-{bin_end}"


def _assign_year_bins(years: pd.Series, width: int) -> pd.Series:
    year_min = int(years.min())
    year_max = int(years.max())
    return years.apply(lambda year: _year_bin_label(int(year), year_min, year_max, width))


def _prototype_scores(texts: list[str], settings: dict) -> np.ndarray:
    from sentence_transformers import SentenceTransformer

    model_settings = settings.get("model", {})
    model = SentenceTransformer(model_settings.get("model_name", "sentence-transformers/all-MiniLM-L6-v2"))
    batch_size = int(model_settings.get("batch_size", 32))
    labels = list(STANCE_DISPLAY_LABELS.keys())
    prototypes = model_settings.get("label_prototypes", {})
    label_texts = [prototype for label in labels for prototype in prototypes.get(label, [])]
    label_slices: dict[str, slice] = {}
    start = 0
    for label in labels:
        n = len(prototypes.get(label, []))
        label_slices[label] = slice(start, start + n)
        start += n

    text_embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    prototype_embeddings = model.encode(
        label_texts,
        batch_size=batch_size,
        show_progress_bar=False,
        normalize_embeddings=True,
    )
    scores = np.zeros((len(texts), len(labels)), dtype=float)
    for idx, label in enumerate(labels):
        label_emb = prototype_embeddings[label_slices[label]]
        scores[:, idx] = np.max(text_embeddings @ label_emb.T, axis=1)
    return scores


def build_cancer_stance_outputs(works: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    settings = cancer_stance_settings()
    subset = works.loc[cancer_subset_mask(works, settings)].copy()
    if subset.empty:
        empty = pd.DataFrame()
        return empty, empty, empty, {"enabled": False, "n_cancer_subset": 0}

    label_rows = []
    model_texts: list[str] = []
    model_indices: list[int] = []
    min_text_chars = int(settings.get("model", {}).get("min_text_chars", 80))
    for idx, row in subset.iterrows():
        rule = classify_stance_text(
            title_text=_clean_optional_text(row.get("title", "")),
            abstract_text=_clean_optional_text(row.get("abstract", "")),
            settings=settings,
        )
        abstract_text = _clean_optional_text(row.get("abstract", ""))
        title_text = _clean_optional_text(row.get("title", ""))
        abstract_norm = _normalize_stance_text(abstract_text)
        title_norm = _normalize_stance_text(title_text)
        model_text = abstract_norm if len(abstract_norm) >= min_text_chars else ""
        if not model_text and settings.get("use_title_fallback", True) and title_norm:
            model_text = title_norm
        label_rows.append(
            {
                "work_id": row["id"],
                "publication_year": int(row["publication_year"]),
                "time_slice": row.get("time_slice", ""),
                "title": title_text,
                "source_title": row.get("source_title", ""),
                "has_abstract": bool(abstract_text),
                "model_text_source": "abstract" if model_text == abstract_norm and model_text else ("title_fallback" if model_text else "not_scored"),
                **rule,
            }
        )
        if model_text:
            model_indices.append(len(label_rows) - 1)
            model_texts.append(model_text[: int(settings.get("model", {}).get("max_chars", 1800))])

    labels_df = pd.DataFrame(label_rows)
    labels_df["model_label"] = "not_scored"
    labels_df["model_display_label"] = "Not scored"
    labels_df["model_confidence"] = np.nan
    labels_df["model_margin"] = np.nan

    if settings.get("model", {}).get("enabled", True) and model_texts:
        scores = _prototype_scores(model_texts, settings)
        label_keys = list(STANCE_DISPLAY_LABELS.keys())
        for row_idx, score_row in zip(model_indices, scores, strict=False):
            best = int(np.argmax(score_row))
            ranked = np.argsort(score_row)[::-1]
            top = float(score_row[ranked[0]])
            second = float(score_row[ranked[1]]) if len(ranked) > 1 else top
            model_label = label_keys[best]
            labels_df.at[row_idx, "model_label"] = model_label
            labels_df.at[row_idx, "model_display_label"] = stance_display_label(model_label)
            labels_df.at[row_idx, "model_confidence"] = top
            labels_df.at[row_idx, "model_margin"] = top - second

    labels_df["label_agreement"] = np.where(
        labels_df["model_label"].eq("not_scored"),
        "not_scored",
        np.where(labels_df["rule_label"].eq(labels_df["model_label"]), "agree", "disagree"),
    )
    labels_df["rule_model_pair"] = labels_df["rule_display_label"] + " -> " + labels_df["model_display_label"]

    year_bin_width = int(settings.get("year_bin_width", 5))
    labels_df["time_bin"] = _assign_year_bins(labels_df["publication_year"], year_bin_width)
    trend = (
        labels_df.groupby(["time_bin", "rule_label", "rule_display_label"], as_index=False)
        .agg(n_papers=("work_id", "nunique"))
    )
    totals = labels_df.groupby("time_bin", as_index=False).agg(bin_total=("work_id", "nunique"))
    trend = trend.merge(totals, on="time_bin", how="left")
    trend["share"] = trend["n_papers"] / trend["bin_total"]

    comparison = (
        labels_df[labels_df["model_label"] != "not_scored"]
        .groupby(["rule_display_label", "model_display_label"], as_index=False)
        .agg(n_papers=("work_id", "nunique"))
        .sort_values("n_papers", ascending=False)
    )
    agreement_scope = labels_df[(labels_df["model_label"] != "not_scored") & (labels_df["rule_label"] != "unclear")]
    agreement_rate = float((agreement_scope["rule_label"] == agreement_scope["model_label"]).mean()) if not agreement_scope.empty else math.nan

    summary = {
        "enabled": True,
        "n_cancer_subset": int(labels_df["work_id"].nunique()),
        "n_with_abstract": int(labels_df["has_abstract"].sum()),
        "abstract_coverage": float(labels_df["has_abstract"].mean()),
        "n_model_scored": int((labels_df["model_label"] != "not_scored").sum()),
        "rule_model_agreement_excluding_unclear": agreement_rate,
        "rule_label_counts": Counter(labels_df["rule_display_label"]).most_common(),
        "year_bin_width": year_bin_width,
    }
    return labels_df, trend, comparison, summary


def build_phrase_documents(works: pd.DataFrame) -> list[list[str]]:
    settings = phrase_map_settings()
    phrase_patterns = settings.get("phrase_patterns", {})
    docs = []
    for text in works["analysis_text"].fillna(""):
        docs.append(extract_phrase_hits(str(text), phrase_patterns))
    return docs
