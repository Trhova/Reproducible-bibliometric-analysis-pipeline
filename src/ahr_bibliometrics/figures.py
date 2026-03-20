from __future__ import annotations

from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
import seaborn as sns

from .config import FIGURE_DIR, METHODS_DIR, TABLE_DIR
from .methods import write_methods_file


FIGURE_FORMATS = ("png", "pdf", "svg")
BASE_COLORS = {
    "ink": "#1C2331",
    "brick": "#A44A3F",
    "ochre": "#C08A3E",
    "sage": "#5F8F7A",
    "teal": "#377D86",
    "slate": "#60708B",
    "plum": "#8A5E7B",
    "sand": "#D8CCB4",
}
NETWORK_PALETTE = ["#A44A3F", "#C08A3E", "#5F8F7A", "#377D86", "#60708B", "#8A5E7B", "#B9C0C9", "#4E5A65"]
NETWORK_LABEL_SKIP = {
    "helix",
    "loop_helix",
    "helix_loop",
    "helix_loop_helix",
    "basic_helix",
    "basic_helix_loop",
    "activated_transcription",
    "ligand_activated_transcription",
    "activated_transcription_factor",
    "translocator",
    "nuclear_translocator",
    "compared",
    "shown",
    "abstract",
    "binding",
}
NETWORK_LABEL_PREFERENCES = [
    "dioxin",
    "tcdd",
    "cytochrome",
    "p450",
    "arnt",
    "translocator",
    "benzo",
    "pyrene",
    "formylindolo",
    "cyp1a1",
    "cancer",
    "tumor",
    "breast",
    "microbiome",
    "gut",
    "intestinal",
    "inflammation",
    "inflammatory",
    "tryptophan",
    "kynurenine",
    "indole",
    "fatty",
    "acetic",
    "oxygen",
    "skin",
    "homeostasis",
    "host",
    "metabolic",
]


def set_plot_style() -> None:
    sns.set_theme(style="whitegrid")
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Serif",
            "axes.facecolor": "#FBF9F4",
            "figure.facecolor": "#FBF9F4",
            "axes.edgecolor": "#D6D2C4",
            "axes.labelcolor": BASE_COLORS["ink"],
            "text.color": BASE_COLORS["ink"],
            "xtick.color": BASE_COLORS["ink"],
            "ytick.color": BASE_COLORS["ink"],
            "axes.titleweight": "semibold",
            "axes.titlesize": 15,
            "axes.labelsize": 11,
            "legend.frameon": False,
            "grid.color": "#E2DDD2",
            "grid.linewidth": 0.8,
        }
    )


def save_figure(fig: plt.Figure, stem: str) -> None:
    FIGURE_DIR.mkdir(parents=True, exist_ok=True)
    for ext in FIGURE_FORMATS:
        fig.savefig(FIGURE_DIR / f"{stem}.{ext}", dpi=400, bbox_inches="tight")
    plt.close(fig)


def _methods_common(summary: dict) -> dict:
    return {
        "corpus_name": "Validated AhR OpenAlex corpus",
        "n_papers": summary["n_papers"],
        "time_window": f"{summary['year_min']} to {summary['year_max']}",
        "query_summary": (
            'OpenAlex exact-match title/abstract retrieval for "aryl hydrocarbon receptor", '
            '"ah receptor", and "dioxin receptor", plus title-level "AHR" hits; local regex validation '
            "retained records with explicit AhR naming in the title or abstract-phrase hits supported by biologically relevant title language."
        ),
        "preprocessing": [
            "English-language articles and reviews were retained.",
            "Titles, available abstracts, OpenAlex keywords, and MeSH descriptors were normalized after corpus retrieval.",
            "Title-plus-abstract text was used for the main term-network and clustering analyses after broader metadata trials produced noisier concept maps.",
            "Text was lowercased, punctuation-normalized, and harmonized with editable synonym mappings in configs/synonyms.yaml.",
            "Generic bibliometric and non-informative scientific terms from configs/stopwords_terms.txt were removed from term-heavy analyses.",
        ],
        "caveats": [
            "The corpus favors precision over total recall because ambiguous plain-AHR abstracts were not retrieved exhaustively.",
            "OpenAlex abstract coverage is incomplete, so title-only records remain in the corpus when they pass conservative validation.",
            "Dictionary-tagged disease/application assignments are approximate, multi-label, and sensitive to the editable regex dictionary.",
        ],
    }


def render_publications_over_time(summary: dict) -> dict:
    annual = pd.read_csv(TABLE_DIR / "publication_counts.csv")
    theme = pd.read_csv(TABLE_DIR / "publication_theme_counts.csv")
    set_plot_style()
    fig, axes = plt.subplots(2, 1, figsize=(11.5, 8), sharex=True, gridspec_kw={"height_ratios": [2.3, 1]})

    axes[0].bar(annual["publication_year"], annual["publications"], color=BASE_COLORS["teal"], alpha=0.85, width=0.8)
    axes[0].plot(annual["publication_year"], annual["rolling_mean_3y"], color=BASE_COLORS["brick"], linewidth=2.4)
    axes[0].set_ylabel("Publications")
    axes[0].set_title("AhR Literature Growth")
    axes[0].text(
        0.01,
        0.93,
        f"Validated corpus: {summary['n_papers']:,} papers",
        transform=axes[0].transAxes,
        fontsize=10.5,
        color=BASE_COLORS["ink"],
    )

    axes[1].fill_between(
        annual["publication_year"],
        annual["cumulative_publications"],
        color=BASE_COLORS["ochre"],
        alpha=0.35,
    )
    axes[1].plot(annual["publication_year"], annual["cumulative_publications"], color=BASE_COLORS["ochre"], linewidth=2.2)
    axes[1].set_ylabel("Cumulative")
    axes[1].set_xlabel("Publication year")
    axes[1].text(
        0.99,
        0.08,
        "2026 is a partial year",
        transform=axes[1].transAxes,
        ha="right",
        fontsize=9.5,
        color=BASE_COLORS["ink"],
    )

    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)

    save_figure(fig, "figure_01_publications_over_time")
    metadata = _methods_common(summary) | {
        "title": "Figure 01. AhR literature growth over time",
        "purpose": "Shows annual publication counts and the cumulative growth trajectory of the validated AhR literature.",
        "analysis_steps": [
            "Papers were grouped by publication year.",
            "A three-year rolling mean was calculated for a smoothed annual trend line.",
            "A cumulative count curve was derived from the annual counts.",
        ],
        "thresholds": [
            "No per-year smoothing beyond a centered three-year rolling mean.",
            "Corpus restricted to validated English-language articles and reviews.",
        ],
        "plotting": [
            "Top panel uses muted teal bars plus a contrasting brick trend line.",
            "Bottom panel uses a cumulative area-and-line treatment for thesis-friendly readability.",
            "Exports were saved as PNG, PDF, and SVG at 400 dpi.",
        ],
        "interpretation": [
            "This figure is suited to framing AhR as a mature but still expanding field.",
            "Inflection points can be compared against historical shifts from toxicology-centric work toward immunity, microbiome, and cancer themes.",
        ],
        "caveats": _methods_common(summary)["caveats"] + [
            "The 2026 bar reflects a partial year because the pipeline was run during 2026 rather than after year-end indexing closed.",
        ],
    }
    write_methods_file(METHODS_DIR / "figure_01_publications_over_time.md", metadata)
    return metadata


def render_disease_distribution(summary: dict) -> dict:
    disease = pd.read_csv(TABLE_DIR / "disease_distribution.csv").head(10)
    set_plot_style()
    fig, ax = plt.subplots(figsize=(11, 6.8))
    disease = disease.sort_values("n_papers", ascending=True)
    colors = sns.color_palette("crest", n_colors=len(disease))
    ax.barh(disease["category"], disease["n_papers"], color=colors)
    for y, (_, row) in enumerate(disease.iterrows()):
        ax.text(row["n_papers"] + 10, y, f"{row['n_papers']:,} ({row['share']:.0%})", va="center", fontsize=10)
    ax.set_xlabel("Tagged papers")
    ax.set_title("Disease and Application Landscape of AhR Research")
    ax.spines[["top", "right"]].set_visible(False)
    save_figure(fig, "figure_02_disease_application_distribution")
    metadata = _methods_common(summary) | {
        "title": "Figure 02. Disease and application distribution across the AhR corpus",
        "purpose": "Summarizes which disease and translational application areas appear most often in the AhR literature.",
        "analysis_steps": [
            "Dictionary-based category tags were applied to each paper using normalized titles, available abstracts, keywords, MeSH descriptors, and topic labels.",
            "Papers could receive multiple categories if multiple pattern groups matched.",
            "Counts were summarized as unique papers per category across the full corpus.",
        ],
        "thresholds": [
            "Only the ten largest categories are plotted.",
            "Categories are multi-label and therefore counts can sum to more than the total number of papers.",
        ],
        "plotting": [
            "A horizontal ranking format was used to maximize label readability in thesis layout.",
            "Counts and corpus-share annotations are printed directly on the figure to reduce legend dependence.",
        ],
        "interpretation": [
            "This figure helps position cancer, barrier, microbiome, toxicology, and immune themes relative to one another.",
            "It is useful for arguing whether thesis-relevant application areas are niche or mainstream branches within the wider AhR field.",
        ],
    }
    write_methods_file(METHODS_DIR / "figure_02_disease_application_distribution.md", metadata)
    return metadata


def render_disease_trends(summary: dict) -> dict:
    trends = pd.read_csv(TABLE_DIR / "disease_trends.csv")
    if trends.empty:
        return {}
    top_categories = trends.groupby("category")["n_papers"].sum().sort_values(ascending=False).head(10).index
    heat = (
        trends[trends["category"].isin(top_categories)]
        .pivot(index="category", columns="period", values="share_within_period")
        .fillna(0)
    )
    set_plot_style()
    fig, ax = plt.subplots(figsize=(10.5, 7))
    sns.heatmap(
        heat.loc[heat.sum(axis=1).sort_values().index],
        cmap=sns.light_palette(BASE_COLORS["teal"], as_cmap=True),
        linewidths=0.7,
        annot=True,
        fmt=".0%",
        cbar_kws={"label": "Share of papers within period"},
        ax=ax,
    )
    ax.set_title("How AhR Application Areas Shifted Across Time")
    ax.set_xlabel("Time period")
    ax.set_ylabel("")
    save_figure(fig, "figure_03_disease_application_trends")
    metadata = _methods_common(summary) | {
        "title": "Figure 03. Disease and application trends across AhR field eras",
        "purpose": "Shows how major AhR application areas changed in prominence from early to recent literature.",
        "analysis_steps": [
            "The corpus was sliced into 1970-1999, 2000-2012, and 2013-2026 using the editable config file.",
            "Multi-label dictionary tags were counted within each period.",
            "Counts were normalized by the number of papers in each period to plot within-period share rather than raw volume alone.",
        ],
        "thresholds": [
            "Only the ten categories with the largest total tagged volume are shown.",
            "Percentages are period-normalized to support comparison despite uneven corpus size across eras.",
        ],
        "plotting": [
            "A heatmap was chosen over stacked bars to keep the cross-period comparison readable with many categories.",
            "Cell annotations are shown directly on the map for methods-ready interpretation.",
        ],
        "interpretation": [
            "This figure is suited to discussing whether toxicology-led AhR work has broadened toward immune, barrier, microbiome, and cancer contexts over time.",
            "Because categories are multi-label, increases can reflect expansion in overlap between domains rather than replacement of one area by another.",
        ],
    }
    write_methods_file(METHODS_DIR / "figure_03_disease_application_trends.md", metadata)
    return metadata


def _draw_network(ax: plt.Axes, nodes: pd.DataFrame, edges: pd.DataFrame, title: str) -> None:
    graph = nx.Graph()
    for _, row in edges.iterrows():
        graph.add_edge(row["source"], row["target"], weight=row["weight"])
    pos = {row["term"]: (row["x"], row["y"]) for _, row in nodes.iterrows()}
    cluster_colors = {cluster: NETWORK_PALETTE[(cluster - 1) % len(NETWORK_PALETTE)] for cluster in nodes["cluster"].unique()}
    for _, edge in edges.iterrows():
        x0, y0 = pos[edge["source"]]
        x1, y1 = pos[edge["target"]]
        ax.plot([x0, x1], [y0, y1], color="#B8B3A7", linewidth=0.5 + edge["weight"] * 2.0, alpha=0.24, zorder=1)
    sizes = 18 + nodes["frequency"].to_numpy() * 0.7
    ax.scatter(
        nodes["x"],
        nodes["y"],
        s=sizes,
        c=[cluster_colors[c] for c in nodes["cluster"]],
        alpha=0.92,
        linewidth=0.6,
        edgecolors="#FBF9F4",
        zorder=3,
    )
    label_pool = nodes.loc[~nodes["term"].isin(NETWORK_LABEL_SKIP)].sort_values(["degree", "frequency"], ascending=False)
    preferred = label_pool[label_pool["term"].apply(lambda term: any(token in term for token in NETWORK_LABEL_PREFERENCES))]
    fallback = label_pool[~label_pool["term"].isin(preferred["term"])]
    label_nodes = pd.concat([preferred, fallback]).drop_duplicates(subset="term").head(14)
    for _, row in label_nodes.iterrows():
        ax.text(
            row["x"],
            row["y"],
            row["term"].replace("_", " "),
            fontsize=9.5,
            ha="center",
            va="center",
            zorder=4,
            bbox={"boxstyle": "round,pad=0.18", "fc": "#FBF9F4", "ec": "none", "alpha": 0.78},
        )
    ax.set_title(title)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)


def render_network(summary: dict, nodes_file: str, edges_file: str, stem: str, title: str, purpose: str, thresholds: list[str], interpretation: list[str]) -> dict:
    nodes = pd.read_csv(TABLE_DIR / nodes_file)
    edges = pd.read_csv(TABLE_DIR / edges_file)
    set_plot_style()
    fig, ax = plt.subplots(figsize=(11.2, 8.8))
    _draw_network(ax, nodes, edges, title)
    save_figure(fig, stem)
    metadata = _methods_common(summary) | {
        "title": title,
        "purpose": purpose,
        "analysis_steps": [
            "A binary term-document matrix was built from normalized title-plus-abstract text after broader metadata trials produced noisier concept maps.",
            "Pairwise term co-occurrence counts were computed across papers in the relevant corpus subset.",
            "Edges were weighted by an association-strength style normalization using co-occurrence divided by the geometric mean of individual term frequencies.",
            "Louvain community detection was used to assign clusters, and a weighted spring layout positioned the network.",
        ],
        "thresholds": thresholds,
        "plotting": [
            "Edges are rendered as faint weighted strokes to avoid a hairball effect.",
            "Node size scales with document frequency and color indicates Louvain cluster membership.",
            "Only the highest-salience labels are shown directly to preserve readability.",
        ],
        "interpretation": interpretation,
    }
    write_methods_file(METHODS_DIR / f"{stem}.md", metadata)
    return metadata


def render_term_evolution(summary: dict) -> dict:
    evolution = pd.read_csv(TABLE_DIR / "term_evolution.csv")
    order = (
        evolution.groupby("term")["prevalence"]
        .max()
        .sort_values(ascending=False)
        .head(16)
        .index
    )
    subset = evolution[evolution["term"].isin(order)].copy()
    subset["display_term"] = subset["term"].str.replace("_", " ")
    set_plot_style()
    fig, ax = plt.subplots(figsize=(12, 8))
    periods = list(dict.fromkeys(subset["period"]))
    x_positions = {period: idx for idx, period in enumerate(periods)}
    term_delta = subset.groupby("display_term")["prevalence"].agg(lambda s: s.iloc[-1] - s.iloc[0]).sort_values()
    color_map = {term: BASE_COLORS["brick"] if delta > 0 else BASE_COLORS["slate"] for term, delta in term_delta.items()}
    for term, group in subset.groupby("display_term"):
        xs = [x_positions[p] for p in group["period"]]
        ys = group["prevalence"].to_numpy()
        ax.plot(xs, ys, marker="o", linewidth=2.2, color=color_map[term], alpha=0.82)
        ax.text(xs[-1] + 0.05, ys[-1], term, va="center", fontsize=9.5)
    ax.set_xticks(range(len(periods)), periods)
    ax.set_ylabel("Document prevalence")
    ax.set_title("Shifting Language Around AhR Across Field Eras")
    ax.spines[["top", "right"]].set_visible(False)
    save_figure(fig, "figure_06_thematic_evolution")
    metadata = _methods_common(summary) | {
        "title": "Figure 06. Thematic evolution of AhR-associated language",
        "purpose": "Highlights terms whose prevalence rose or fell most strongly across early, middle, and recent AhR eras.",
        "analysis_steps": [
            "A document-term matrix was built with conservative frequency thresholds to focus on reusable field-level vocabulary.",
            "Within each time slice, term prevalence was defined as the share of papers containing the term at least once.",
            "The largest positive and negative recent-versus-early changes were selected for plotting.",
        ],
        "thresholds": [
            "Terms had to pass corpus-level document-frequency thresholds embedded in the analysis module.",
            "Only 16 high-change terms were plotted to keep the slope chart readable.",
        ],
        "plotting": [
            "Rising terms are colored in brick and declining terms in slate.",
            "A slope-style layout was chosen to foreground directional change rather than absolute frequency alone.",
        ],
        "interpretation": [
            "This figure is useful for narrating the shift from older toxicology-led terminology toward more recent immune, barrier, microbiome, and cancer language.",
            "Changes reflect metadata language prevalence, not mechanistic causality or the scientific importance of a term.",
        ],
    }
    write_methods_file(METHODS_DIR / "figure_06_thematic_evolution.md", metadata)
    return metadata


def render_cluster_map(summary: dict) -> dict:
    cluster = pd.read_csv(TABLE_DIR / "cluster_summary.csv")
    cluster["x_plot"] = (cluster["x"] - cluster["x"].mean()) / cluster["x"].std(ddof=0)
    cluster["y_plot"] = (cluster["y"] - cluster["y"].mean()) / cluster["y"].std(ddof=0)
    set_plot_style()
    fig, ax = plt.subplots(figsize=(10.8, 8))
    colors = [NETWORK_PALETTE[(c - 1) % len(NETWORK_PALETTE)] for c in cluster["cluster"]]
    ax.scatter(cluster["x_plot"], cluster["y_plot"], s=cluster["n_papers"] * 1.8, color=colors, alpha=0.86, edgecolor="#FBF9F4", linewidth=1.2)
    for _, row in cluster.iterrows():
        terms = row["top_terms"].replace("_", " ").split(", ")
        wrapped = ", ".join(terms[:3]) + "\n" + ", ".join(terms[3:5])
        ax.text(
            row["x_plot"],
            row["y_plot"],
            f"Cluster {row['cluster']}\n{wrapped}",
            ha="center",
            va="center",
            fontsize=9.3,
            bbox={"boxstyle": "round,pad=0.28", "fc": "#FBF9F4", "ec": "none", "alpha": 0.84},
        )
    ax.set_title("Thematic Cluster Map of the AhR Literature")
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_xlim(cluster["x_plot"].min() - 0.7, cluster["x_plot"].max() + 0.7)
    ax.set_ylim(cluster["y_plot"].min() - 0.7, cluster["y_plot"].max() + 0.7)
    for spine in ax.spines.values():
        spine.set_visible(False)
    save_figure(fig, "figure_07_thematic_cluster_map")
    metadata = _methods_common(summary) | {
        "title": "Figure 07. Thematic cluster map of the AhR literature",
        "purpose": "Provides a reduced thematic overview of the AhR field by clustering papers on their normalized term profiles.",
        "analysis_steps": [
            "TF-IDF vectors were built from normalized document text.",
            "MiniBatchKMeans partitioned papers into seven thematic clusters.",
            "Cluster centroids were projected into two dimensions using MDS on cosine distance between centroids.",
            "Each bubble is labeled by the top weighted centroid terms and sized by the number of papers in the cluster.",
        ],
        "thresholds": [
            "Seven clusters were used as a pragmatic overview scale rather than a claim of the field's true discrete structure.",
            "TF-IDF features were frequency-filtered to suppress sparse one-off phrases.",
        ],
        "plotting": [
            "Bubble size encodes cluster size, while label text encodes centroid-defining terms.",
            "The map emphasizes interpretable thematic neighborhoods instead of precise geometric meaning.",
        ],
        "interpretation": [
            "This figure helps identify major AhR subfields and the relative size of each thematic branch.",
            "Distances are projection-based and should be read qualitatively rather than as exact semantic metrics.",
        ],
    }
    write_methods_file(METHODS_DIR / "figure_07_thematic_cluster_map.md", metadata)
    return metadata


def render_top_journals(summary: dict) -> dict:
    journals = pd.read_csv(TABLE_DIR / "top_journals.csv").sort_values("n_papers")
    set_plot_style()
    fig, ax = plt.subplots(figsize=(11, 6.8))
    ax.hlines(journals["journal"], 0, journals["n_papers"], color="#CFC8B8", linewidth=2.4)
    ax.scatter(journals["n_papers"], journals["journal"], s=80, color=BASE_COLORS["plum"])
    ax.set_xlabel("Validated AhR papers")
    ax.set_title("Journals Most Frequently Publishing AhR Research")
    ax.spines[["top", "right"]].set_visible(False)
    save_figure(fig, "figure_08_top_journals")
    metadata = _methods_common(summary) | {
        "title": "Figure 08. Journals most frequently publishing AhR papers",
        "purpose": "Offers a lightweight publishing-landscape view without letting citation metrics dominate the analysis.",
        "analysis_steps": [
            "Primary source titles were counted across the validated corpus.",
            "The fifteen most frequent journals were retained for visualization.",
        ],
        "thresholds": [
            "Only the top fifteen sources by paper count are shown.",
        ],
        "plotting": [
            "A lollipop-style layout was used to keep long journal names legible in thesis format.",
        ],
        "interpretation": [
            "This figure is a contextual companion, useful for understanding where AhR work tends to concentrate institutionally.",
            "It is descriptive only and should not be read as a quality ranking of journals.",
        ],
    }
    write_methods_file(METHODS_DIR / "figure_08_top_journals.md", metadata)
    return metadata


def render_all_figures(summary: dict) -> list[dict]:
    outputs = [
        render_publications_over_time(summary),
        render_disease_distribution(summary),
        render_disease_trends(summary),
        render_network(
            summary,
            nodes_file="network_all_nodes.csv",
            edges_file="network_all_edges.csv",
            stem="figure_04_keyword_network_all_corpus",
            title="Figure 04. Term co-occurrence network across the AhR corpus",
            purpose="Maps the main co-occurring concept structure across the full validated AhR literature.",
            thresholds=[
                "Only terms passing minimum document-frequency thresholds were eligible.",
                "Only edges above count and association-strength thresholds were retained.",
                "The graph was truncated to the strongest retained edges among the highest-frequency terms to keep the network readable.",
            ],
            interpretation=[
                "Clusters often represent broad AhR branches such as toxicology, immunology, microbiome/barrier biology, and cancer-related work.",
                "Absence of an edge should not be interpreted as absence of a biological relationship; it only means the term pair did not survive readability-oriented thresholds.",
            ],
        ),
        render_network(
            summary,
            nodes_file="network_focus_nodes.csv",
            edges_file="network_focus_edges.csv",
            stem="figure_05_keyword_network_immune_barrier_microbiome",
            title="Figure 05. Immune-barrier-microbiome AhR term network",
            purpose="Focuses the co-occurrence map on the thesis-relevant immune, barrier, gut, and microbiome-oriented subset of AhR papers.",
            thresholds=[
                "Subset defined by immune, inflammation, microbiome, barrier, gut, or intestinal focus tags.",
                "Lower minimum term and edge thresholds were used than in the all-corpus network to preserve structure within the smaller subset.",
            ],
            interpretation=[
                "This view is intended to surface bridges between mucosal biology, host-microbe interactions, inflammation, and immune regulation.",
                "Because the subset is pattern-based, some relevant papers may be missed if they use unexpected terminology.",
            ],
        ),
        render_term_evolution(summary),
        render_cluster_map(summary),
        render_top_journals(summary),
    ]
    return outputs
