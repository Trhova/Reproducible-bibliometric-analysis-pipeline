from __future__ import annotations

from collections import Counter
import json
import math
import re
from typing import Any

import numpy as np
import pandas as pd
import requests

from .config import load_project_config, load_synonyms_config, project_paths, save_json
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


def _llm_cache_key(work_id: str, model_settings: dict[str, Any]) -> str:
    prompt_version = str(model_settings.get("prompt_version", "v1"))
    model_name = str(model_settings.get("model_name", "qwen2.5:7b"))
    return f"{work_id}::{model_name}::{prompt_version}"


def _load_llm_cache() -> dict[str, dict[str, Any]]:
    cache_path = project_paths().cancer_stance_llm_cache
    if not cache_path.exists():
        return {}
    with cache_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return payload if isinstance(payload, dict) else {}


def _save_llm_cache(cache: dict[str, dict[str, Any]]) -> None:
    save_json(project_paths().cancer_stance_llm_cache, cache)


def _extract_json_object(text: str) -> dict[str, Any]:
    text = (text or "").strip()
    if not text:
        raise ValueError("Empty LLM response.")
    try:
        payload = json.loads(text)
        if isinstance(payload, dict):
            return payload
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if not match:
        raise ValueError(f"Could not find JSON object in LLM response: {text[:240]}")
    payload = json.loads(match.group(0))
    if not isinstance(payload, dict):
        raise ValueError("LLM JSON payload was not an object.")
    return payload


def _normalize_llm_label(value: object) -> str:
    if value is None:
        return "unclear"
    text = str(value).strip().lower()
    mappings = {
        "pro_tumor": "pro_tumor",
        "pro-tumor": "pro_tumor",
        "pro tumor": "pro_tumor",
        "protumor": "pro_tumor",
        "anti_tumor": "anti_tumor",
        "anti-tumor": "anti_tumor",
        "anti tumor": "anti_tumor",
        "antitumor": "anti_tumor",
        "mixed_context": "mixed_context",
        "mixed/context-dependent": "mixed_context",
        "mixed": "mixed_context",
        "context-dependent": "mixed_context",
        "context dependent": "mixed_context",
        "unclear": "unclear",
    }
    return mappings.get(text, "unclear")


def _coerce_confidence(value: object) -> float:
    if isinstance(value, (int, float)):
        return float(max(0.0, min(1.0, value)))
    if value is None:
        return math.nan
    text = str(value).strip().lower().replace("%", "")
    buckets = {
        "very high": 0.95,
        "high": 0.85,
        "moderate": 0.65,
        "medium": 0.65,
        "low": 0.35,
        "very low": 0.15,
    }
    if text in buckets:
        return buckets[text]
    try:
        numeric = float(text)
        if numeric > 1:
            numeric /= 100.0
        return float(max(0.0, min(1.0, numeric)))
    except ValueError:
        return math.nan


def _truncate_text(text: str, max_chars: int) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    return text[:max_chars].strip()


def _default_model_result(model_settings: dict[str, Any], text_source: str, error: str = "") -> dict[str, Any]:
    return {
        "model_label": "not_scored",
        "model_display_label": "Not scored",
        "model_confidence": math.nan,
        "model_rationale": "",
        "model_evidence_span": "",
        "model_source": text_source,
        "model_provider": "ollama",
        "model_name": str(model_settings.get("model_name", "qwen2.5:7b")),
        "model_error": error,
    }


def _normalize_model_result(payload: dict[str, Any], model_settings: dict[str, Any], text_source: str) -> dict[str, Any]:
    label = _normalize_llm_label(payload.get("label"))
    return {
        "model_label": label,
        "model_display_label": stance_display_label(label),
        "model_confidence": _coerce_confidence(payload.get("confidence")),
        "model_rationale": str(payload.get("rationale", "")).strip(),
        "model_evidence_span": str(payload.get("evidence_span", "")).strip(),
        "model_source": text_source,
        "model_provider": "ollama",
        "model_name": str(model_settings.get("model_name", "qwen2.5:7b")),
        "model_error": "",
    }


def _build_llm_prompt(*, title_text: str, abstract_text: str) -> str:
    return (
        "Classify how this cancer-focused paper frames the aryl hydrocarbon receptor (AhR) in the text.\n"
        "This is a framing task, not a truth judgment about biology.\n"
        "Allowed labels:\n"
        "- pro_tumor: AhR is framed as promoting tumor growth, survival, invasion, metastasis, immune evasion, or therapy resistance.\n"
        "- anti_tumor: AhR is framed as suppressing tumor growth, preventing carcinogenesis, or supporting anti-tumor immunity.\n"
        "- mixed_context: the text explicitly presents AhR as context-dependent, dual, or having both pro-tumor and anti-tumor roles.\n"
        "- unclear: the text mentions AhR and cancer but does not clearly assign a directional role.\n"
        "Return exactly one JSON object with keys: label and confidence.\n"
        "Confidence must be a number between 0 and 1.\n\n"
        f"TITLE: {title_text or '[none]'}\n"
        f"ABSTRACT: {abstract_text or '[none]'}"
    )


def _build_llm_batch_prompt(items: list[dict[str, Any]]) -> str:
    serialized_items = json.dumps(
        [
            {
                "idx": item["idx"],
                "title": item["title_text"] or "[none]",
                "abstract": item["abstract_text"] or "[none]",
            }
            for item in items
        ],
        ensure_ascii=False,
    )
    return (
        "Classify how each cancer-focused paper frames the aryl hydrocarbon receptor (AhR) in the text.\n"
        "This is a framing task, not a truth judgment about biology.\n"
        "Allowed labels: pro_tumor, anti_tumor, mixed_context, unclear.\n"
        "Definitions:\n"
        "- pro_tumor: AhR is framed as promoting tumor growth, survival, invasion, metastasis, immune evasion, or therapy resistance.\n"
        "- anti_tumor: AhR is framed as suppressing tumor growth, preventing carcinogenesis, or supporting anti-tumor immunity.\n"
        "- mixed_context: the text explicitly presents AhR as context-dependent, dual, or having both pro-tumor and anti-tumor roles.\n"
        "- unclear: the text mentions AhR and cancer but does not clearly assign a directional role.\n"
        "Return exactly one JSON object with key `results`, whose value is a list of objects with keys: idx, label, confidence.\n"
        "Confidence must be a number between 0 and 1.\n\n"
        f"PAPERS: {serialized_items}"
    )


def _single_response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "label": {
                "type": "string",
                "enum": list(STANCE_DISPLAY_LABELS.keys()),
            },
            "confidence": {
                "type": "number",
            },
        },
        "required": ["label", "confidence"],
        "additionalProperties": False,
    }


def _batch_response_schema() -> dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "results": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "idx": {"type": "integer"},
                        "label": {
                            "type": "string",
                            "enum": list(STANCE_DISPLAY_LABELS.keys()),
                        },
                        "confidence": {"type": "number"},
                    },
                    "required": ["idx", "label", "confidence"],
                    "additionalProperties": False,
                },
            },
        },
        "required": ["results"],
        "additionalProperties": False,
    }


def _call_ollama_json(*, prompt: str, model_settings: dict[str, Any], response_schema: dict[str, Any] | None = None) -> dict[str, Any]:
    endpoint = str(model_settings.get("endpoint", "http://127.0.0.1:11434/api/generate"))
    payload = {
        "model": model_settings.get("model_name", "qwen2.5:7b"),
        "prompt": prompt,
        "stream": False,
        "format": response_schema or "json",
        "options": {
            "temperature": float(model_settings.get("temperature", 0.0)),
            "num_ctx": int(model_settings.get("num_ctx", 4096)),
            "num_predict": int(model_settings.get("num_predict", 512)),
        },
    }
    timeout_seconds = float(model_settings.get("timeout_seconds", 180))
    response = requests.post(endpoint, json=payload, timeout=timeout_seconds)
    response.raise_for_status()
    body = response.json()
    return _extract_json_object(str(body.get("response", "")))


def _classify_with_local_llm(
    *,
    work_id: str,
    title_text: str,
    abstract_text: str,
    text_source: str,
    settings: dict[str, Any],
    cache: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    model_settings = settings.get("model", {})
    cache_key = _llm_cache_key(work_id, model_settings)
    cached = cache.get(cache_key)
    if cached:
        return cached

    prompt = _build_llm_prompt(title_text=title_text, abstract_text=abstract_text)
    last_error = ""
    retries = int(model_settings.get("retries", 1))
    for _ in range(retries + 1):
        try:
            payload = _call_ollama_json(
                prompt=prompt,
                model_settings=model_settings,
                response_schema=_single_response_schema(),
            )
            result = _normalize_model_result(payload, model_settings, text_source)
            cache[cache_key] = result
            return result
        except Exception as exc:  # noqa: BLE001
            last_error = str(exc)

    result = _default_model_result(model_settings, text_source, error=last_error)
    cache[cache_key] = result
    return result


def _classify_batch_with_local_llm(
    items: list[dict[str, Any]],
    *,
    settings: dict[str, Any],
    cache: dict[str, dict[str, Any]],
) -> dict[int, dict[str, Any]]:
    model_settings = settings.get("model", {})
    prompt = _build_llm_batch_prompt(items)
    try:
        payload = _call_ollama_json(
            prompt=prompt,
            model_settings=model_settings,
            response_schema=_batch_response_schema(),
        )
        raw_results = payload.get("results", [])
        by_idx: dict[int, dict[str, Any]] = {}
        for result in raw_results:
            idx = int(result.get("idx"))
            item = next((candidate for candidate in items if candidate["idx"] == idx), None)
            if item is None:
                continue
            normalized = _normalize_model_result(result, model_settings, item["text_source"])
            cache[_llm_cache_key(item["work_id"], model_settings)] = normalized
            by_idx[idx] = normalized
        missing = [item for item in items if item["idx"] not in by_idx]
        for item in missing:
            by_idx[item["idx"]] = _classify_with_local_llm(
                work_id=item["work_id"],
                title_text=item["title_text"],
                abstract_text=item["abstract_text"],
                text_source=item["text_source"],
                settings=settings,
                cache=cache,
            )
        return by_idx
    except Exception:  # noqa: BLE001
        return {
            item["idx"]: _classify_with_local_llm(
                work_id=item["work_id"],
                title_text=item["title_text"],
                abstract_text=item["abstract_text"],
                text_source=item["text_source"],
                settings=settings,
                cache=cache,
            )
            for item in items
        }


def build_cancer_stance_outputs(works: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    settings = cancer_stance_settings()
    subset = works.loc[cancer_subset_mask(works, settings)].copy()
    if subset.empty:
        empty = pd.DataFrame()
        return empty, empty, empty, {"enabled": False, "n_cancer_subset": 0}

    label_rows = []
    model_settings = settings.get("model", {})
    min_text_chars = int(model_settings.get("min_text_chars", 80))
    score_rule_labels = set(model_settings.get("score_rule_labels", []))
    cache = _load_llm_cache() if model_settings.get("enabled", True) else {}
    cache_dirty = False
    new_cache_rows = 0
    scorable_items: list[dict[str, Any]] = []
    for _, row in subset.iterrows():
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
        model_text_source = "abstract" if model_text == abstract_norm and model_text else ("title_fallback" if model_text else "not_scored")
        label_rows.append(
            {
                "work_id": row["id"],
                "publication_year": int(row["publication_year"]),
                "time_slice": row.get("time_slice", ""),
                "title": title_text,
                "source_title": row.get("source_title", ""),
                "has_abstract": bool(abstract_text),
                "model_text_source": model_text_source,
                **rule,
                **_default_model_result(model_settings, model_text_source),
            }
        )
        should_score = bool(model_text) and (not score_rule_labels or rule["rule_label"] in score_rule_labels)
        if model_settings.get("enabled", True) and should_score:
            scorable_items.append(
                {
                    "idx": len(label_rows) - 1,
                    "work_id": str(row["id"]),
                    "title_text": _truncate_text(title_text, int(model_settings.get("max_title_chars", 220))),
                    "abstract_text": _truncate_text(model_text, int(model_settings.get("max_chars", 900))),
                    "text_source": model_text_source,
                }
            )

    labels_df = pd.DataFrame(label_rows)
    if model_settings.get("enabled", True) and scorable_items:
        pending: list[dict[str, Any]] = []
        for item in scorable_items:
            cache_key = _llm_cache_key(item["work_id"], model_settings)
            cached = cache.get(cache_key)
            if cached:
                for key, value in cached.items():
                    labels_df.at[item["idx"], key] = value
                continue
            pending.append(item)

        batch_size = int(model_settings.get("batch_size", 6))
        for start in range(0, len(pending), batch_size):
            batch = pending[start : start + batch_size]
            if batch_size <= 1:
                batch_results = {
                    item["idx"]: _classify_with_local_llm(
                        work_id=item["work_id"],
                        title_text=item["title_text"],
                        abstract_text=item["abstract_text"],
                        text_source=item["text_source"],
                        settings=settings,
                        cache=cache,
                    )
                    for item in batch
                }
            else:
                batch_results = _classify_batch_with_local_llm(batch, settings=settings, cache=cache)
            for item in batch:
                result = batch_results[item["idx"]]
                for key, value in result.items():
                    labels_df.at[item["idx"], key] = value
                new_cache_rows += 1
                cache_dirty = True
            if new_cache_rows % int(model_settings.get("save_every", 25)) == 0:
                _save_llm_cache(cache)
                cache_dirty = False
    if cache_dirty:
        _save_llm_cache(cache)

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
        "n_model_failed": int((labels_df["model_label"] == "not_scored").sum()),
        "rule_model_agreement_excluding_unclear": agreement_rate,
        "rule_label_counts": Counter(labels_df["rule_display_label"]).most_common(),
        "model_label_counts": Counter(labels_df.loc[labels_df["model_label"] != "not_scored", "model_display_label"]).most_common(),
        "model_provider": "ollama",
        "model_name": str(model_settings.get("model_name", "qwen2.5:7b")),
        "model_endpoint": str(model_settings.get("endpoint", "http://127.0.0.1:11434/api/generate")),
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
