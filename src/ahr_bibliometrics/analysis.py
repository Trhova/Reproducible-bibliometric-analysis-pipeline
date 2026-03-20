from __future__ import annotations

from collections import Counter
from itertools import combinations
import re

import networkx as nx
import numpy as np
import pandas as pd
from sklearn.cluster import MiniBatchKMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer

from .config import TABLE_DIR, load_search_config, load_synonyms_config, save_json
from .io_utils import slugify
from .text_processing import apply_alias_replacements, build_alias_map, normalize_text, parse_pipe_list


RANDOM_STATE = 42

CONCEPT_EXCLUDE_TERMS = {
    "AhR",
    "chemistry",
    "biology",
    "receptor",
    "cell biology",
    "internal medicine",
    "cancer research",
    "medicine",
    "biochemistry",
    "molecular biology",
    "immunology",
    "pharmacology",
    "signal transduction",
    "gene",
    "gene expression",
    "enzyme",
    "cell",
    "in vivo",
    "in vitro",
    "computational biology",
    "animals",
    "humans",
    "mice",
    "female",
    "male",
    "rats",
    "adult",
    "middle aged",
    "cells cultured",
    "cell line",
    "cell line tumor",
    "tumor cells cultured",
    "disease models animal",
    "mice inbred c57bl",
    "mice knockout",
    "rats sprague dawley",
    "receptors drug",
    "molecular sequence data",
    "base sequence",
    "dose response relationship drug",
    "protein binding",
    "binding sites",
    "transcription factors",
    "transcription genetic",
    "gene expression regulation",
    "gene expression regulation neoplastic",
    "transcriptional activation",
    "ligands",
    "ligand biochemistry",
    "transfection",
    "messenger rna",
    "rna messenger",
    "basic helix loop helix proteins",
    "basic helix loop helix transcription factors",
    "endocrinology",
    "aryl",
    "hydrocarbon",
    "genetics",
    "environmental chemistry",
    "nuclear receptor",
    "population",
    "microbiology",
    "pregnancy",
    "species specificity",
    "time factors",
    "phenotype",
    "kinase",
    "luciferases",
    "bioassay",
    "flow cytometry",
    "blotting western",
    "immunohistochemistry",
    "reverse transcriptase polymerase chain reaction",
    "promoter regions genetic",
    "gene knockdown",
    "transcriptome",
    "amino acid sequence",
    "rna small interfering",
    "cell growth",
    "cell survival",
    "cell proliferation",
    "function biology",
    "receptors estrogen",
    "transcription factor",
    "downregulation and upregulation",
    "cell culture",
    "dna",
    "dna binding proteins",
    "cytosol",
    "stereochemistry",
    "biophysics",
}

CONCEPT_CANONICAL_MAP = {
    "ahr": "AhR",
    "receptors aryl hydrocarbon": "AhR",
    "ahr nuclear translocator": "ARNT",
    "aryl hydrocarbon receptor nuclear translocator": "ARNT",
    "cyp1a1": "CYP1A1",
    "cyp1b1": "CYP1B1",
    "cytochrome p 450 cyp1a1": "CYP1A1",
    "cytochrome p 450 cyp1b1": "CYP1B1",
    "cytochrome p450": "cytochrome P450",
    "aryl hydrocarbon hydroxylases": "cytochrome P450",
    "polychlorinated dibenzodioxins": "dioxin / TCDD",
    "dioxins": "dioxin / TCDD",
    "tetrachlorodibenzo p dioxin": "dioxin / TCDD",
    "tetrachlorodibenzo dioxin": "dioxin / TCDD",
    "dioxin tcdd": "dioxin / TCDD",
    "gut flora": "microbiome",
    "gastrointestinal microbiome": "microbiome",
    "microbiota": "microbiome",
    "breast neoplasms": "breast cancer",
    "estrogen receptor alpha": "estrogen receptor",
    "receptors estrogen": "estrogen receptor",
    "inflammatory bowel disease": "inflammatory bowel disease",
    "inflammatory bowel diseases": "inflammatory bowel disease",
    "colitis ulcerative": "inflammatory bowel disease",
    "ulcerative colitis": "inflammatory bowel disease",
    "crohn disease": "inflammatory bowel disease",
    "crohn s disease": "inflammatory bowel disease",
    "intestinal mucosa": "intestinal barrier",
    "intestinal epithelium": "intestinal barrier",
    "barrier function": "intestinal barrier",
    "t lymphocytes regulatory": "Treg cells",
    "foxp3": "Treg cells",
    "th17 cells": "Th17 cells",
    "interleukin 22": "IL-22",
    "interleukin 17": "IL-17",
    "interleukin 6": "IL-6",
    "tumor necrosis factor alpha": "TNF-alpha",
    "indoleamine 2 3 dioxygenase": "IDO1",
    "indoleamine pyrrole 2 3 dioxygenase": "IDO1",
    "benzo a pyrene": "benzo[a]pyrene",
    "polycyclic aromatic hydrocarbons": "PAHs",
    "carcinoma hepatocellular": "hepatocellular carcinoma",
    "liver neoplasms": "hepatocellular carcinoma",
    "tumor microenvironment": "tumor immunity",
    "immune cells in cancer": "tumor immunity",
}

TEXT_MARKERS = {
    "immune system": [r"\bimmune\b", r"\bimmunity\b"],
    "inflammation": [r"\binflamm"],
    "microbiome": [r"\bmicrobiome\b", r"\bmicrobiota\b", r"\bgut flora\b"],
    "intestinal barrier": [r"\bbarrier function\b", r"\bintestinal barrier\b", r"\bgut barrier\b", r"\bmucosal barrier\b"],
    "gut": [r"\bgut\b", r"\bintestinal\b", r"\bcolon\b", r"\bcolonic\b"],
    "tryptophan": [r"\btryptophan\b"],
    "kynurenine": [r"\bkynurenine\b"],
    "indoles": [r"\bindole", r"\bindoleamine\b"],
    "dioxin / TCDD": [r"\bdioxin\b", r"\btcdd\b", r"\btcdd\b"],
    "CYP1A1": [r"\bcyp1a1\b"],
    "CYP1B1": [r"\bcyp1b1\b"],
    "cytochrome P450": [r"\bcytochrome p450\b", r"\bp450\b"],
    "ARNT": [r"\barnt\b", r"\bnuclear translocator\b"],
    "breast cancer": [r"\bbreast cancer\b", r"\bbreast neoplasm"],
    "cancer": [r"\bcancer\b", r"\btumou?r\b", r"\bcarcinoma\b", r"\bneoplasm"],
    "estrogen receptor": [r"\bestrogen receptor\b"],
    "tumor immunity": [r"\btumou?r immunity\b", r"\btumou?r microenvironment\b", r"\bcancer immunotherapy\b", r"\bimmunotherapy\b"],
    "Treg cells": [r"\btreg\b", r"\bfoxp3\b", r"\bregulatory t"],
    "Th17 cells": [r"\bth17\b", r"\bil 17\b", r"\binterleukin 17\b"],
    "IL-22": [r"\bil 22\b", r"\binterleukin 22\b"],
    "TNF-alpha": [r"\btnf\b", r"\btumor necrosis factor\b"],
    "IDO1": [r"\bido1\b", r"\bindoleamine 2 3 dioxygenase\b", r"\bindoleamine pyrrole 2 3 dioxygenase\b"],
    "oxidative stress": [r"\boxidative stress\b", r"\breactive oxygen species\b"],
    "apoptosis": [r"\bapoptosis\b"],
    "stem cell": [r"\bstem cell"],
    "skin disease": [r"\bpsoriasis\b", r"\bdermatitis\b", r"\beczema\b", r"\bskin disease\b"],
}

THEME_PROFILES = {
    "toxicology": {
        "terms": {
            "dioxin / TCDD",
            "CYP1A1",
            "CYP1B1",
            "cytochrome P450",
            "ARNT",
            "liver",
            "toxicity",
            "environmental pollutants",
            "benzo[a]pyrene",
            "PAHs",
            "enzyme induction",
            "carcinogen",
            "cytochrome p 450 enzyme system",
        },
        "label": "Dioxin and xenobiotic toxicology",
    },
    "cancer": {
        "terms": {
            "cancer",
            "breast cancer",
            "estrogen receptor",
            "carcinogenesis",
            "tumor immunity",
            "apoptosis",
            "hepatocellular carcinoma",
        },
        "label": "Cancer and tumor signaling",
    },
    "immune": {
        "terms": {
            "immune system",
            "immunity",
            "Treg cells",
            "Th17 cells",
            "innate immune system",
            "cell differentiation",
            "IL-22",
            "IL-17",
            "stem cell",
        },
        "label": "T cell and cytokine regulation",
    },
    "inflammation": {
        "terms": {
            "inflammation",
            "TNF-alpha",
            "cytokine",
            "cytokines",
            "oxidative stress",
            "proinflammatory cytokine",
            "skin disease",
        },
        "label": "Inflammation and epithelial stress",
    },
    "tryptophan": {
        "terms": {
            "tryptophan",
            "kynurenine",
            "IDO1",
            "indoles",
            "metabolite",
            "metabolism",
            "kynurenine pathway",
        },
        "label": "Tryptophan-kynurenine immunometabolism",
    },
    "microbiome": {
        "terms": {
            "microbiome",
            "gut",
            "intestinal barrier",
            "inflammatory bowel disease",
            "colitis",
        },
        "label": "Microbiome and gut barrier biology",
    },
}


def _analysis_stopwords(stopwords: set[str]) -> list[str]:
    return sorted(set(stopwords) | set(ENGLISH_STOP_WORDS))


def load_works(path: str | None = None) -> pd.DataFrame:
    target = path or "data/processed/works.csv.gz"
    return pd.read_csv(target)


def _concept_resources() -> tuple[dict[str, str], dict[str, str]]:
    synonyms = load_synonyms_config()
    alias_to_token, _ = build_alias_map(synonyms)
    return alias_to_token, synonyms.get("normalizations", {})


def _normalize_concept(raw: str, alias_to_token: dict[str, str], normalizations: dict[str, str]) -> str | None:
    text = normalize_text(raw, normalizations=normalizations)
    text = apply_alias_replacements(text, alias_to_token)
    text = text.replace("_", " ").strip()
    text = CONCEPT_CANONICAL_MAP.get(text, text)
    if not text or text in CONCEPT_EXCLUDE_TERMS:
        return None
    return text


def _extract_concepts_from_row(row: pd.Series, alias_to_token: dict[str, str], normalizations: dict[str, str]) -> list[str]:
    terms = set()
    for field in ["keywords", "mesh_terms"]:
        for raw in parse_pipe_list(row.get(field, "")):
            concept = _normalize_concept(raw, alias_to_token, normalizations)
            if concept:
                terms.add(concept)
    text = str(row.get("analysis_text", "") or "")
    for concept, patterns in TEXT_MARKERS.items():
        if any(re.search(pattern, text) for pattern in patterns):
            terms.add(concept)
    return sorted(terms)


def _cluster_label(top_terms: list[str]) -> str:
    terms = set(top_terms)
    lower_terms = {term.lower() for term in terms}
    if any(term in lower_terms for term in {"structure activity relationship", "stereochemistry", "biophysics", "cytosol"}):
        return "Ligand chemistry and structure-activity"

    scores = {
        theme: sum(term in profile["terms"] for term in terms)
        for theme, profile in THEME_PROFILES.items()
    }
    environmental_terms = {"liver", "toxicity", "environmental pollutants", "xenobiotic"}
    cyp_terms = {"cytochrome P450", "CYP1A1", "CYP1B1", "cytochrome p 450 enzyme system"}

    if {"ARNT", "CYP1A1"} & terms and any(
        term in lower_terms
        for term in {
            "reporter gene",
            "transactivation",
            "basic helix loop helix",
            "helix loop helix motifs",
            "translocator protein",
            "transcription linguistics",
        }
    ):
        return "ARNT-CYP1 transcriptional response"
    if scores["toxicology"] >= 3 and scores["cancer"] >= 2:
        return "CYP1 toxicology and carcinogenesis"
    if scores["toxicology"] >= 3 and "dioxin / TCDD" in terms:
        return "Dioxin and xenobiotic toxicology"
    if scores["toxicology"] >= 3 and sum(term in terms for term in environmental_terms) >= 2:
        return "Environmental toxicology and liver response"
    if scores["toxicology"] >= 3 and any(term in terms for term in cyp_terms):
        return "CYP1 enzyme induction and toxicology"
    if scores["microbiome"] >= 2 and scores["tryptophan"] >= 2 and (scores["immune"] >= 1 or scores["inflammation"] >= 1):
        return "Immune-microbiome signaling"
    if scores["immune"] >= 2 and scores["inflammation"] >= 2:
        return "T cell and cytokine regulation"
    if scores["microbiome"] >= 2 and (scores["immune"] >= 1 or scores["inflammation"] >= 1):
        return "Microbiome and gut barrier biology"
    if scores["tryptophan"] >= 2:
        return "Tryptophan-kynurenine immunometabolism"
    if scores["inflammation"] >= 2:
        return "Inflammation and epithelial stress"
    if scores["immune"] >= 2:
        return "T cell and cytokine regulation"
    if scores["cancer"] >= 3:
        if any(term in terms for term in {"breast cancer", "estrogen receptor"}):
            return "Cancer and hormone signaling"
        return "Cancer and tumor signaling"
    if scores["toxicology"] >= 2:
        return "Dioxin and xenobiotic toxicology"
    if scores["cancer"] >= 2:
        return "Cancer and tumor signaling"

    best_theme = max(scores, key=scores.get)
    if scores[best_theme] > 0:
        return str(THEME_PROFILES[best_theme]["label"])
    return "Mechanistic and translational AhR studies"


def _subset_mask(works: pd.DataFrame, subset_name: str) -> pd.Series:
    if subset_name == "all":
        return pd.Series(True, index=works.index)
    return works["focus_tags"].fillna("").str.contains("immune|microbiome|barrier|inflammation|gut|intestinal")


def _deduplicate_cluster_labels(cluster_summary: pd.DataFrame) -> pd.DataFrame:
    updated = cluster_summary.copy()
    for label, subset in updated.groupby("cluster_label"):
        if len(subset) == 1:
            continue
        for idx, row in subset.iterrows():
            terms = {term.strip().lower() for term in str(row["top_terms"]).split(",")}
            if label == "CYP1 toxicology and carcinogenesis" and terms & {"liver", "toxicity", "environmental pollutants"}:
                updated.at[idx, "cluster_label"] = "Environmental toxicology and liver response"
            elif label == "Environmental toxicology and liver response" and terms & {"cytochrome p450", "cyp1a1", "cyp1b1"} and not terms & {"toxicity", "environmental pollutants"}:
                updated.at[idx, "cluster_label"] = "CYP1 enzyme induction and toxicology"
            elif label == "Dioxin and xenobiotic toxicology" and terms & {"cytochrome p450", "cyp1a1", "cyp1b1"}:
                updated.at[idx, "cluster_label"] = "CYP1 enzyme induction and toxicology"
            elif label == "Cancer and hormone signaling" and terms & {"cyp1a1", "cyp1b1"}:
                updated.at[idx, "cluster_label"] = "CYP1-cancer signaling interface"
    return updated


def _concept_documents(works: pd.DataFrame) -> tuple[list[list[str]], list[str]]:
    alias_to_token, normalizations = _concept_resources()
    docs: list[list[str]] = []
    doc_strings: list[str] = []
    for _, row in works.iterrows():
        concepts = _extract_concepts_from_row(row, alias_to_token, normalizations)
        docs.append(concepts)
        doc_strings.append(" ".join(slugify(term) for term in concepts))
    return docs, doc_strings


def build_publication_tables(works: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    annual = (
        works.groupby("publication_year")
        .size()
        .rename("publications")
        .reset_index()
        .sort_values("publication_year")
    )
    annual["rolling_mean_3y"] = annual["publications"].rolling(3, min_periods=1).mean()
    annual["cumulative_publications"] = annual["publications"].cumsum()

    theme_rows = []
    for _, row in works.iterrows():
        year = row["publication_year"]
        for tag in parse_pipe_list(row["focus_tags"]):
            theme_rows.append({"publication_year": year, "theme": tag})
    theme_df = pd.DataFrame(theme_rows)
    if theme_df.empty:
        return annual, pd.DataFrame(columns=["publication_year", "theme", "n_papers"])
    theme_counts = (
        theme_df.groupby(["publication_year", "theme"])
        .size()
        .rename("n_papers")
        .reset_index()
    )
    return annual, theme_counts


def build_disease_tables(works: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    rows = []
    for _, row in works.iterrows():
        for category in parse_pipe_list(row["disease_tags"]):
            rows.append(
                {
                    "work_id": row["id"],
                    "publication_year": row["publication_year"],
                    "period": row["time_slice"],
                    "category": category,
                }
            )
    disease_long = pd.DataFrame(rows)
    if disease_long.empty:
        return pd.DataFrame(columns=["category", "n_papers", "share"]), pd.DataFrame()
    dist = (
        disease_long.groupby("category")["work_id"]
        .nunique()
        .rename("n_papers")
        .reset_index()
        .sort_values("n_papers", ascending=False)
    )
    dist["share"] = dist["n_papers"] / works["id"].nunique()
    trends = (
        disease_long.groupby(["period", "category"])["work_id"]
        .nunique()
        .rename("n_papers")
        .reset_index()
    )
    period_sizes = works.groupby("time_slice")["id"].nunique().rename("period_total")
    trends = trends.merge(period_sizes, left_on="period", right_index=True, how="left")
    trends["share_within_period"] = trends["n_papers"] / trends["period_total"]
    return dist, trends


def build_term_evolution(works: pd.DataFrame) -> pd.DataFrame:
    trackers = [
        "dioxin / TCDD",
        "PAHs",
        "cytochrome P450",
        "CYP1A1",
        "cancer",
        "breast cancer",
        "inflammation",
        "immune system",
        "microbiome",
        "intestinal barrier",
        "tryptophan",
        "kynurenine",
        "tumor immunity",
        "Treg cells",
        "Th17 cells",
        "ARNT",
    ]
    docs, _ = _concept_documents(works)
    rows = []
    concept_sets = [set(doc) for doc in docs]
    for period, subset in works.groupby("time_slice"):
        idx = subset.index.to_numpy()
        total = len(idx)
        for term in trackers:
            prevalence = sum(term in concept_sets[i] for i in idx) / total if total else 0.0
            rows.append({"period": period, "term": term, "prevalence": prevalence})
    return pd.DataFrame(rows)


def _network_layout(graph: nx.Graph, cluster_map: dict[str, int]) -> dict[str, np.ndarray]:
    cluster_graph = nx.Graph()
    for node, cluster in cluster_map.items():
        cluster_graph.add_node(cluster)
    for source, target, data in graph.edges(data=True):
        c1 = cluster_map[source]
        c2 = cluster_map[target]
        if c1 == c2:
            continue
        weight = data["weight"]
        if cluster_graph.has_edge(c1, c2):
            cluster_graph[c1][c2]["weight"] += weight
        else:
            cluster_graph.add_edge(c1, c2, weight=weight)
    if cluster_graph.number_of_edges() == 0:
        cluster_centers = {cluster: np.array([float(idx), 0.0]) for idx, cluster in enumerate(sorted(cluster_graph.nodes()))}
    else:
        cluster_centers = nx.spring_layout(cluster_graph, weight="weight", seed=RANDOM_STATE, scale=4.0)

    positions: dict[str, np.ndarray] = {}
    for cluster in sorted(set(cluster_map.values())):
        nodes = [node for node, value in cluster_map.items() if value == cluster]
        subgraph = graph.subgraph(nodes).copy()
        if subgraph.number_of_nodes() == 1:
            positions[nodes[0]] = np.array(cluster_centers[cluster])
            continue
        local_layout = nx.spring_layout(
            subgraph,
            weight="weight",
            seed=RANDOM_STATE + cluster,
            k=0.9 / np.sqrt(max(subgraph.number_of_nodes(), 2)),
            scale=1.0,
        )
        radius = 0.55 + 0.08 * np.sqrt(subgraph.number_of_nodes())
        for node, coords in local_layout.items():
            positions[node] = np.array(cluster_centers[cluster]) + radius * np.array(coords)
    return positions


def build_network_tables(works: pd.DataFrame, subset_name: str) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    subset = works.loc[_subset_mask(works, subset_name)].copy()
    docs, _ = _concept_documents(subset)
    alias_to_token, normalizations = _concept_resources()
    doc_counter = Counter()
    pair_counter = Counter()
    for concepts in docs:
        filtered = sorted(set(concepts))
        for term in filtered:
            doc_counter[term] += 1
        for source, target in combinations(filtered, 2):
            pair_counter[(source, target)] += 1

    min_docs = 140 if subset_name == "all" else 45
    max_nodes = 42 if subset_name == "all" else 36
    candidate_terms = [term for term, count in doc_counter.items() if count >= min_docs]
    top_terms = sorted(candidate_terms, key=lambda term: (-doc_counter[term], term))[:max_nodes]
    top_term_set = set(top_terms)

    graph = nx.Graph()
    for term in top_terms:
        graph.add_node(term, frequency=doc_counter[term])
    for (source, target), count in pair_counter.items():
        if source not in top_term_set or target not in top_term_set:
            continue
        weight = count / float(np.sqrt(doc_counter[source] * doc_counter[target]))
        if count < (26 if subset_name == "all" else 12) or weight < 0.11:
            continue
        graph.add_edge(source, target, weight=weight, count=count)

    if graph.number_of_nodes() == 0:
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    graph.remove_nodes_from(list(nx.isolates(graph)))
    communities = list(nx.community.louvain_communities(graph, weight="weight", seed=RANDOM_STATE))
    cluster_map = {}
    cluster_rows = []
    for idx, community in enumerate(sorted(communities, key=len, reverse=True), start=1):
        subgraph = graph.subgraph(community)
        ranked_terms = sorted(
            community,
            key=lambda term: (-(graph.degree(term, weight="weight")), -graph.nodes[term]["frequency"], term),
        )
        top_terms_cluster = ranked_terms[:5]
        label_terms = ranked_terms[:10]
        label = _cluster_label(label_terms)
        for node in community:
            cluster_map[node] = idx
        cluster_rows.append(
            {
                "cluster": idx,
                "cluster_label": label,
                "top_terms": " | ".join(top_terms_cluster),
                "n_terms": len(community),
                "total_frequency": int(sum(graph.nodes[node]["frequency"] for node in community)),
            }
        )

    positions = _network_layout(graph, cluster_map)
    nodes = []
    for node in graph.nodes():
        nodes.append(
            {
                "term": node,
                "x": positions[node][0],
                "y": positions[node][1],
                "frequency": int(graph.nodes[node]["frequency"]),
                "cluster": cluster_map[node],
                "degree": int(graph.degree(node)),
                "weighted_degree": float(graph.degree(node, weight="weight")),
                "cluster_label": next(row["cluster_label"] for row in cluster_rows if row["cluster"] == cluster_map[node]),
            }
        )
    edges = []
    for source, target, data in graph.edges(data=True):
        edges.append(
            {
                "source": source,
                "target": target,
                "weight": float(data["weight"]),
                "count": int(data["count"]),
                "source_cluster": cluster_map[source],
                "target_cluster": cluster_map[target],
            }
        )

    nodes_df = pd.DataFrame(nodes).sort_values(["cluster", "weighted_degree", "frequency"], ascending=[True, False, False])
    edges_df = pd.DataFrame(edges).sort_values(["weight", "count"], ascending=[False, False])
    clusters_df = pd.DataFrame(cluster_rows).sort_values("cluster")
    return nodes_df, edges_df, clusters_df


def build_cluster_summary(works: pd.DataFrame, stopwords: set[str]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    docs, concept_doc_strings = _concept_documents(works)
    alias_to_token, normalizations = _concept_resources()
    vectorizer = TfidfVectorizer(
        token_pattern=r"(?u)\b[a-z][a-z0-9_]{2,}\b",
        min_df=20,
        max_df=0.25,
        max_features=700,
        stop_words=_analysis_stopwords(stopwords),
    )
    matrix = vectorizer.fit_transform(concept_doc_strings)
    latent = TruncatedSVD(n_components=12, random_state=RANDOM_STATE).fit_transform(matrix)
    coords = TruncatedSVD(n_components=2, random_state=RANDOM_STATE + 1).fit_transform(matrix)
    n_clusters = 7
    km = MiniBatchKMeans(n_clusters=n_clusters, random_state=RANDOM_STATE, batch_size=512, n_init="auto")
    labels = km.fit_predict(latent)
    features = np.array(vectorizer.get_feature_names_out())

    works_clustered = works[["id", "publication_year", "source_title", "time_slice"]].copy()
    works_clustered["cluster"] = labels + 1
    works_clustered["x"] = coords[:, 0]
    works_clustered["y"] = coords[:, 1]

    rows = []
    for idx in range(n_clusters):
        mask = labels == idx
        mean_tfidf = np.asarray(matrix[mask].mean(axis=0)).ravel()
        top_tokens = features[np.argsort(mean_tfidf)[::-1][:5]].tolist()
        label_tokens = features[np.argsort(mean_tfidf)[::-1][:12]].tolist()
        top_terms = [
            _normalize_concept(token.replace("_", " "), alias_to_token, normalizations) or token.replace("_", " ")
            for token in top_tokens
        ]
        label_terms = [
            _normalize_concept(token.replace("_", " "), alias_to_token, normalizations) or token.replace("_", " ")
            for token in label_tokens
        ]
        label = _cluster_label(label_terms)
        dominant_sources = (
            works.loc[mask, "source_title"]
            .fillna("Unknown source")
            .value_counts()
            .head(3)
            .index.tolist()
        )
        rows.append(
            {
                "cluster": idx + 1,
                "cluster_label": label,
                "x": float(np.median(coords[mask, 0])),
                "y": float(np.median(coords[mask, 1])),
                "n_papers": int(mask.sum()),
                "top_terms": ", ".join(top_terms),
                "dominant_sources": " | ".join(dominant_sources),
                "median_year": int(np.median(works.loc[mask, "publication_year"])),
            }
        )
    cluster_summary = pd.DataFrame(rows).sort_values("cluster")
    cluster_summary = _deduplicate_cluster_labels(cluster_summary)
    cluster_summary = _deduplicate_cluster_labels(cluster_summary)
    label_map = dict(zip(cluster_summary["cluster"], cluster_summary["cluster_label"], strict=False))
    works_clustered["cluster_label"] = works_clustered["cluster"].map(label_map)

    cluster_period = (
        works_clustered.groupby(["time_slice", "cluster", "cluster_label"])
        .size()
        .rename("n_papers")
        .reset_index()
    )
    period_totals = works_clustered.groupby("time_slice").size().rename("period_total").reset_index()
    cluster_period = cluster_period.merge(period_totals, on="time_slice", how="left")
    cluster_period["share"] = cluster_period["n_papers"] / cluster_period["period_total"]
    return cluster_summary, works_clustered, cluster_period


def build_journal_table(works: pd.DataFrame) -> pd.DataFrame:
    journal = (
        works["source_title"]
        .fillna("Unknown source")
        .value_counts()
        .rename_axis("journal")
        .rename("n_papers")
        .reset_index()
        .head(15)
    )
    return journal


def write_analysis_outputs(works: pd.DataFrame, stopwords: set[str]) -> dict:
    TABLE_DIR.mkdir(parents=True, exist_ok=True)

    annual, theme_counts = build_publication_tables(works)
    annual.to_csv(TABLE_DIR / "publication_counts.csv", index=False)
    theme_counts.to_csv(TABLE_DIR / "publication_theme_counts.csv", index=False)

    disease_dist, disease_trends = build_disease_tables(works)
    disease_dist.to_csv(TABLE_DIR / "disease_distribution.csv", index=False)
    disease_trends.to_csv(TABLE_DIR / "disease_trends.csv", index=False)

    term_evolution = build_term_evolution(works)
    term_evolution.to_csv(TABLE_DIR / "term_evolution.csv", index=False)

    network_all_nodes, network_all_edges, network_all_clusters = build_network_tables(works, subset_name="all")
    network_all_nodes.to_csv(TABLE_DIR / "network_all_nodes.csv", index=False)
    network_all_edges.to_csv(TABLE_DIR / "network_all_edges.csv", index=False)
    network_all_clusters.to_csv(TABLE_DIR / "network_all_clusters.csv", index=False)

    network_focus_nodes, network_focus_edges, network_focus_clusters = build_network_tables(works, subset_name="immune_barrier_microbiome")
    network_focus_nodes.to_csv(TABLE_DIR / "network_focus_nodes.csv", index=False)
    network_focus_edges.to_csv(TABLE_DIR / "network_focus_edges.csv", index=False)
    network_focus_clusters.to_csv(TABLE_DIR / "network_focus_clusters.csv", index=False)

    cluster_summary, cluster_assignments, cluster_period = build_cluster_summary(works, stopwords)
    cluster_summary.to_csv(TABLE_DIR / "cluster_summary.csv", index=False)
    cluster_assignments.to_csv(TABLE_DIR / "cluster_assignments.csv", index=False)
    cluster_period.to_csv(TABLE_DIR / "cluster_period_shares.csv", index=False)

    journals = build_journal_table(works)
    journals.to_csv(TABLE_DIR / "top_journals.csv", index=False)

    summary = {
        "n_papers": int(works["id"].nunique()),
        "year_min": int(works["publication_year"].min()),
        "year_max": int(works["publication_year"].max()),
        "n_journals": int(works["source_title"].nunique()),
        "n_countries": int(
            len({country for countries in works["countries"].fillna("") for country in parse_pipe_list(countries)})
        ),
    }
    save_json(TABLE_DIR / "analysis_summary.json", summary)
    return summary
