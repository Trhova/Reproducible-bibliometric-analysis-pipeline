from __future__ import annotations

import json
from collections import Counter, defaultdict
from itertools import combinations

import networkx as nx
import numpy as np
import pandas as pd
from sklearn.cluster import MiniBatchKMeans
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import CountVectorizer, ENGLISH_STOP_WORDS, TfidfVectorizer
from .config import TABLE_DIR, load_search_config, save_json
from .text_processing import parse_pipe_list


RANDOM_STATE = 42


def _analysis_stopwords(stopwords: set[str]) -> list[str]:
    return sorted(set(stopwords) | set(ENGLISH_STOP_WORDS))


def load_works(path: str | None = None) -> pd.DataFrame:
    target = path or "data/processed/works.csv.gz"
    return pd.read_csv(target)


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


def build_term_matrices(works: pd.DataFrame, stopwords: set[str]) -> tuple[CountVectorizer, np.ndarray, np.ndarray]:
    vectorizer = CountVectorizer(
        ngram_range=(1, 3),
        token_pattern=r"(?u)\b[a-z][a-z0-9_]{2,}\b",
        min_df=20,
        max_df=0.12,
        binary=True,
        stop_words=_analysis_stopwords(stopwords),
    )
    matrix = vectorizer.fit_transform(works["prepared_text"])
    doc_freq = np.asarray(matrix.sum(axis=0)).ravel()
    keep_mask = doc_freq >= 25
    reduced = matrix[:, keep_mask]
    return vectorizer, matrix, keep_mask


def build_term_evolution(works: pd.DataFrame, stopwords: set[str]) -> pd.DataFrame:
    vectorizer = CountVectorizer(
        ngram_range=(1, 3),
        token_pattern=r"(?u)\b[a-z][a-z0-9_]{2,}\b",
        min_df=25,
        max_df=0.1,
        binary=True,
        stop_words=_analysis_stopwords(stopwords),
    )
    matrix = vectorizer.fit_transform(works["prepared_text"])
    features = np.array(vectorizer.get_feature_names_out())
    rows = []
    for period, subset in works.groupby("time_slice"):
        period_idx = subset.index.to_numpy()
        period_matrix = matrix[period_idx]
        prevalence = np.asarray(period_matrix.mean(axis=0)).ravel()
        for term, value in zip(features, prevalence, strict=True):
            rows.append({"period": period, "term": term, "prevalence": float(value)})
    evolution = pd.DataFrame(rows)
    pivot = evolution.pivot(index="term", columns="period", values="prevalence").fillna(0)
    config = load_search_config()
    labels = [item["label"] for item in config["time_slices"]]
    pivot["delta_recent_vs_early"] = pivot[labels[-1]] - pivot[labels[0]]
    pivot["overall"] = pivot[labels].mean(axis=1)
    selected = pd.concat(
        [
            pivot.sort_values("delta_recent_vs_early", ascending=False).head(8),
            pivot.sort_values("delta_recent_vs_early", ascending=True).head(8),
        ]
    )
    selected = selected.reset_index()
    return selected.melt(
        id_vars=["term", "delta_recent_vs_early", "overall"],
        value_vars=labels,
        var_name="period",
        value_name="prevalence",
    )


def _subset_mask(works: pd.DataFrame, subset_name: str) -> pd.Series:
    if subset_name == "all":
        return pd.Series(True, index=works.index)
    return works["focus_tags"].fillna("").str.contains("immune|microbiome|barrier|inflammation|gut|intestinal")


def build_network_tables(works: pd.DataFrame, stopwords: set[str], subset_name: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    subset = works.loc[_subset_mask(works, subset_name)].copy()
    vectorizer = CountVectorizer(
        ngram_range=(1, 3),
        token_pattern=r"(?u)\b[a-z][a-z0-9_]{2,}\b",
        min_df=35 if subset_name == "all" else 15,
        max_df=0.12,
        binary=True,
        stop_words=_analysis_stopwords(stopwords),
    )
    matrix = vectorizer.fit_transform(subset["prepared_text"])
    features = np.array(vectorizer.get_feature_names_out())
    doc_freq = np.asarray(matrix.sum(axis=0)).ravel()
    top_n_terms = 65 if subset_name == "all" else 55
    ranked_idx = np.argsort(doc_freq)[::-1][:top_n_terms]
    matrix = matrix[:, ranked_idx]
    features = features[ranked_idx]
    doc_freq = doc_freq[ranked_idx]

    cooc = (matrix.T @ matrix).toarray()
    np.fill_diagonal(cooc, 0)
    edges = []
    for i in range(len(features)):
        for j in range(i + 1, len(features)):
            count = int(cooc[i, j])
            if count < (30 if subset_name == "all" else 12):
                continue
            weight = count / float(np.sqrt(doc_freq[i] * doc_freq[j]))
            if weight < 0.09:
                continue
            edges.append({"source": features[i], "target": features[j], "count": count, "weight": weight})

    edges_df = pd.DataFrame(edges).sort_values(["weight", "count"], ascending=[False, False]).head(160)
    graph = nx.Graph()
    for _, row in edges_df.iterrows():
        graph.add_edge(row["source"], row["target"], weight=row["weight"], count=row["count"])
    if graph.number_of_nodes() == 0:
        return pd.DataFrame(columns=["term", "x", "y", "frequency", "cluster"]), pd.DataFrame(columns=["source", "target", "count", "weight"])

    keep_nodes = set()
    for component in nx.connected_components(graph):
        if len(component) >= 4:
            keep_nodes.update(component)
    graph = graph.subgraph(keep_nodes).copy()
    if graph.number_of_nodes() == 0:
        graph = nx.Graph()
        for _, row in edges_df.head(80).iterrows():
            graph.add_edge(row["source"], row["target"], weight=row["weight"], count=row["count"])
    edges_df = nx.to_pandas_edgelist(graph)
    edges_df = edges_df.rename(columns={"source": "source", "target": "target"})

    communities = list(nx.community.louvain_communities(graph, weight="weight", seed=RANDOM_STATE))
    cluster_map = {}
    for idx, community in enumerate(communities, start=1):
        for node in community:
            cluster_map[node] = idx
    layout = nx.spring_layout(graph, weight="weight", seed=RANDOM_STATE, k=1.1 / np.sqrt(graph.number_of_nodes()))
    nodes = []
    feature_freq = dict(zip(features, doc_freq, strict=False))
    for node, (x, y) in layout.items():
        nodes.append(
            {
                "term": node,
                "x": x,
                "y": y,
                "frequency": int(feature_freq.get(node, 0)),
                "cluster": cluster_map.get(node, 0),
                "degree": graph.degree(node),
            }
        )
    nodes_df = pd.DataFrame(nodes).sort_values("frequency", ascending=False)
    if "count" not in edges_df.columns:
        edges_df["count"] = np.nan
    return nodes_df, edges_df


def build_cluster_summary(works: pd.DataFrame, stopwords: set[str]) -> tuple[pd.DataFrame, pd.DataFrame]:
    vectorizer = TfidfVectorizer(
        ngram_range=(1, 3),
        token_pattern=r"(?u)\b[a-z][a-z0-9_]{2,}\b",
        min_df=20,
        max_df=0.12,
        max_features=900,
        stop_words=_analysis_stopwords(stopwords),
        sublinear_tf=True,
    )
    matrix = vectorizer.fit_transform(works["prepared_text"])
    n_clusters = 7
    km = MiniBatchKMeans(n_clusters=n_clusters, random_state=RANDOM_STATE, batch_size=512, n_init="auto")
    labels = km.fit_predict(matrix)
    works_clustered = works[["id", "publication_year", "source_title"]].copy()
    works_clustered["cluster"] = labels + 1

    centroids = km.cluster_centers_
    coords = TruncatedSVD(n_components=2, random_state=RANDOM_STATE).fit_transform(centroids)
    features = np.array(vectorizer.get_feature_names_out())
    rows = []
    for idx in range(n_clusters):
        mask = labels == idx
        top_terms = ", ".join(features[np.argsort(centroids[idx])[::-1][:5]].tolist())
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
                "x": coords[idx, 0],
                "y": coords[idx, 1],
                "n_papers": int(mask.sum()),
                "top_terms": top_terms,
                "dominant_sources": " | ".join(dominant_sources),
                "median_year": int(np.median(works.loc[mask, "publication_year"])),
            }
        )
    return pd.DataFrame(rows), works_clustered


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

    term_evolution = build_term_evolution(works, stopwords)
    term_evolution.to_csv(TABLE_DIR / "term_evolution.csv", index=False)

    network_all_nodes, network_all_edges = build_network_tables(works, stopwords, subset_name="all")
    network_all_nodes.to_csv(TABLE_DIR / "network_all_nodes.csv", index=False)
    network_all_edges.to_csv(TABLE_DIR / "network_all_edges.csv", index=False)

    network_focus_nodes, network_focus_edges = build_network_tables(works, stopwords, subset_name="immune_barrier_microbiome")
    network_focus_nodes.to_csv(TABLE_DIR / "network_focus_nodes.csv", index=False)
    network_focus_edges.to_csv(TABLE_DIR / "network_focus_edges.csv", index=False)

    cluster_summary, cluster_assignments = build_cluster_summary(works, stopwords)
    cluster_summary.to_csv(TABLE_DIR / "cluster_summary.csv", index=False)
    cluster_assignments.to_csv(TABLE_DIR / "cluster_assignments.csv", index=False)

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
