from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from typing import Iterable


def reconstruct_abstract(inverted_index: dict | None) -> str:
    if not inverted_index:
        return ""
    positions: dict[int, str] = {}
    for token, token_positions in inverted_index.items():
        for idx in token_positions:
            positions[idx] = token
    return " ".join(token for _, token in sorted(positions.items()))


def normalize_text(text: str, normalizations: dict[str, str] | None = None) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[/]", " ", text)
    text = re.sub(r"[-–—]", " ", text)
    text = re.sub(r"[^a-z0-9\s+]", " ", text)
    if normalizations:
        for src, dst in normalizations.items():
            text = re.sub(rf"\b{re.escape(src)}\b", dst, text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def build_alias_map(synonyms_config: dict) -> tuple[dict[str, str], dict[str, str]]:
    alias_to_token: dict[str, str] = {}
    token_to_display: dict[str, str] = {}
    aliases = synonyms_config.get("aliases", {})
    for display, variants in aliases.items():
        token = display.lower().replace(" ", "_")
        token_to_display[token] = display
        alias_to_token[normalize_text(display)] = token
        for variant in variants:
            alias_to_token[normalize_text(variant)] = token
    return alias_to_token, token_to_display


def apply_alias_replacements(text: str, alias_to_token: dict[str, str]) -> str:
    if not text:
        return ""
    prepared = f" {text} "
    for alias in sorted(alias_to_token, key=len, reverse=True):
        prepared = re.sub(rf"(?<!\w){re.escape(alias)}(?!\w)", f" {alias_to_token[alias]} ", prepared)
    return re.sub(r"\s+", " ", prepared).strip()


def compile_patterns(patterns: Iterable[str]) -> list[re.Pattern]:
    return [re.compile(pattern, flags=re.IGNORECASE) for pattern in patterns]


def match_patterns(text: str, patterns: Iterable[re.Pattern]) -> bool:
    return any(pattern.search(text) for pattern in patterns)


def parse_pipe_list(text: str) -> list[str]:
    if text is None:
        return []
    if isinstance(text, float):
        return []
    text = str(text)
    if not text or text.lower() == "nan":
        return []
    return [part for part in text.split("|") if part]


def join_pipe(items: Iterable[str]) -> str:
    ordered = []
    seen = set()
    for item in items:
        if item and item not in seen:
            seen.add(item)
            ordered.append(item)
    return "|".join(ordered)


def derive_focus_tags(text: str) -> list[str]:
    tag_map = {
        "immune": [r"\bimmune\b", r"\btreg\b", r"\bth17\b", r"\bcytokine\b", r"\binterleukin\b"],
        "inflammation": [r"\binflamm", r"\bcolitis\b"],
        "microbiome": [r"\bmicrobiome\b", r"\bmicrobiota\b", r"\bdysbiosis\b", r"\bcommensal\b"],
        "barrier": [r"\bbarrier\b", r"\bmucosal\b", r"\bpermeability\b", r"\bepitheli"],
        "cancer": [r"\bcancer\b", r"\btumou?r\b", r"\bcarcinoma\b", r"\bmelanoma\b", r"\bglioma\b"],
        "toxicology": [r"\bdioxin\b", r"\bxenobiotic\b", r"\btoxic", r"\bpah\b", r"\btcdd\b"],
        "metabolism": [r"\bmetabol", r"\bobesity\b", r"\bdiabetes\b", r"\binsulin\b"],
    }
    hits = []
    for tag, patterns in tag_map.items():
        if any(re.search(pattern, text) for pattern in patterns):
            hits.append(tag)
    return hits


def find_disease_tags(text: str, disease_dictionary: dict) -> list[str]:
    categories = []
    for category in disease_dictionary.get("categories", []):
        if any(re.search(rf"\b{pattern}", text) for pattern in category["patterns"]):
            categories.append(category["name"])
    return categories


def select_curated_terms(
    normalized_text: str,
    keyword_tokens: Iterable[str],
    mesh_tokens: Iterable[str],
    topic_tokens: Iterable[str],
    stopwords: set[str],
) -> list[str]:
    terms = set()
    tokens = re.findall(r"\b[a-z][a-z0-9_]{2,}\b", normalized_text)
    for token in tokens:
        if token not in stopwords and not token.isdigit():
            terms.add(token)
    for collection in [keyword_tokens, mesh_tokens, topic_tokens]:
        for token in collection:
            if token and token not in stopwords:
                terms.add(token)
    filtered = []
    for term in sorted(terms):
        pieces = term.split("_")
        if len(pieces) == 1 and len(term) < 4:
            continue
        if all(piece in stopwords for piece in pieces):
            continue
        filtered.append(term)
    return filtered


def display_term(term: str, token_to_display: dict[str, str]) -> str:
    if term in token_to_display:
        return token_to_display[term]
    return term.replace("_", " ")


def period_label(year: int, time_slices: list[dict]) -> str:
    for item in time_slices:
        if item["start_year"] <= year <= item["end_year"]:
            return item["label"]
    return "Other"
