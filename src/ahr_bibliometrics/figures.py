from __future__ import annotations

from matplotlib.lines import Line2D
from matplotlib.patches import Ellipse, PathPatch, Rectangle
from matplotlib.path import Path
import matplotlib as mpl
import matplotlib.pyplot as plt
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
NETWORK_PALETTE = ["#A44A3F", "#C08A3E", "#5F8F7A", "#377D86", "#60708B", "#8A5E7B", "#8290A4", "#A3B18A"]


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
            "Disease/application tagging still uses broad metadata support, but the upgraded landscape figures use curated concept labels derived from normalized OpenAlex keywords, MeSH descriptors, and targeted title/abstract marker matching.",
            "Text was lowercased, punctuation-normalized, and harmonized with editable synonym mappings in configs/synonyms.yaml.",
            "Generic bibliometric and non-informative scientific terms from configs/stopwords_terms.txt plus figure-specific concept exclusions were removed from map-style analyses.",
        ],
        "caveats": [
            "The corpus favors precision over total recall because ambiguous plain-AHR abstracts were not retrieved exhaustively.",
            "OpenAlex abstract coverage is incomplete, so concept-map coverage partly depends on keyword and MeSH richness rather than abstract availability alone.",
            "Dictionary-tagged disease/application assignments are approximate, multi-label, and sensitive to the editable regex dictionary.",
        ],
    }


def render_publications_over_time(summary: dict) -> dict:
    annual = pd.read_csv(TABLE_DIR / "publication_counts.csv")
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
            "The corpus was sliced into 1980-1999, 2000-2012, and 2013-2026 using the editable config file.",
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


def _cluster_color_map(clusters: pd.DataFrame) -> dict[int, str]:
    return {int(cluster): NETWORK_PALETTE[idx % len(NETWORK_PALETTE)] for idx, cluster in enumerate(sorted(clusters["cluster"].unique()))}


def _node_sizes(nodes: pd.DataFrame) -> np.ndarray:
    return 40 + 16 * np.sqrt(nodes["frequency"].to_numpy()) + 90 * nodes["weighted_degree"].to_numpy()


def _draw_cluster_envelopes(ax: plt.Axes, nodes: pd.DataFrame, color_map: dict[int, str]) -> None:
    for cluster_id, cluster_nodes in nodes.groupby("cluster"):
        points = cluster_nodes[["x", "y"]].to_numpy()
        center = points.mean(axis=0)
        if len(points) == 1:
            width = height = 0.7
            angle = 0.0
        else:
            cov = np.cov(points.T)
            eigvals, eigvecs = np.linalg.eigh(cov)
            order = np.argsort(eigvals)[::-1]
            eigvals = eigvals[order]
            eigvecs = eigvecs[:, order]
            angle = np.degrees(np.arctan2(eigvecs[1, 0], eigvecs[0, 0]))
            width = 3.8 * np.sqrt(max(eigvals[0], 0.02)) + 0.8
            height = 3.2 * np.sqrt(max(eigvals[-1], 0.02)) + 0.6
        patch = Ellipse(
            xy=center,
            width=width,
            height=height,
            angle=angle,
            facecolor=color_map[int(cluster_id)],
            edgecolor="none",
            alpha=0.12,
            zorder=0,
        )
        ax.add_patch(patch)


def _select_network_labels(nodes: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, cluster_nodes in nodes.groupby("cluster"):
        rows.append(cluster_nodes.sort_values(["weighted_degree", "frequency"], ascending=False).head(3))
    label_nodes = pd.concat(rows).drop_duplicates(subset="term")
    return label_nodes.sort_values(["weighted_degree", "frequency"], ascending=False).head(16)


def _draw_network_map(ax: plt.Axes, nodes: pd.DataFrame, edges: pd.DataFrame, clusters: pd.DataFrame, title: str, subtitle: str) -> None:
    color_map = _cluster_color_map(clusters)
    _draw_cluster_envelopes(ax, nodes, color_map)

    edge_width = 0.4 + 4.2 * (edges["weight"] / edges["weight"].max())
    for (_, edge), width in zip(edges.iterrows(), edge_width, strict=False):
        source = nodes.loc[nodes["term"] == edge["source"]].iloc[0]
        target = nodes.loc[nodes["term"] == edge["target"]].iloc[0]
        alpha = 0.12 if edge["source_cluster"] != edge["target_cluster"] else 0.26
        ax.plot(
            [source["x"], target["x"]],
            [source["y"], target["y"]],
            color="#B7B0A2",
            linewidth=width,
            alpha=alpha,
            zorder=1,
        )

    sizes = _node_sizes(nodes)
    ax.scatter(
        nodes["x"],
        nodes["y"],
        s=sizes,
        c=[color_map[int(cluster)] for cluster in nodes["cluster"]],
        edgecolors="#FBF9F4",
        linewidths=0.9,
        alpha=0.95,
        zorder=2,
    )

    label_nodes = _select_network_labels(nodes)
    cluster_centers = nodes.groupby("cluster")[["x", "y"]].mean()
    for _, row in label_nodes.iterrows():
        center = cluster_centers.loc[row["cluster"]]
        dx = row["x"] - center["x"]
        dy = row["y"] - center["y"]
        norm = np.hypot(dx, dy) or 1.0
        ax.text(
            row["x"] + 0.08 * dx / norm,
            row["y"] + 0.08 * dy / norm,
            row["term"],
            fontsize=10.2,
            ha="center",
            va="center",
            zorder=3,
            bbox={"boxstyle": "round,pad=0.18", "fc": "#FBF9F4", "ec": "none", "alpha": 0.84},
        )

    ax.set_title(title, loc="left", pad=14)
    ax.text(0.0, 0.98, subtitle, transform=ax.transAxes, va="top", fontsize=10.2, color=BASE_COLORS["slate"])
    x_pad = max((nodes["x"].max() - nodes["x"].min()) * 0.08, 0.55)
    y_pad = max((nodes["y"].max() - nodes["y"].min()) * 0.12, 0.55)
    ax.set_xlim(nodes["x"].min() - x_pad, nodes["x"].max() + x_pad)
    ax.set_ylim(nodes["y"].min() - y_pad, nodes["y"].max() + y_pad)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)


def _draw_network_side_panel(ax: plt.Axes, nodes: pd.DataFrame, edges: pd.DataFrame, clusters: pd.DataFrame) -> None:
    ax.axis("off")
    color_map = _cluster_color_map(clusters)
    ax.text(0.0, 0.98, "How to read this map", fontsize=12.2, fontweight="semibold", va="top")
    ax.text(0.0, 0.92, "Node size: number of papers carrying the concept", fontsize=9.8, va="top")
    ax.text(0.0, 0.88, "Node color: thematic cluster from Louvain community detection", fontsize=9.8, va="top")
    ax.text(0.0, 0.84, "Edge width: co-occurrence strength between concept labels", fontsize=9.8, va="top")

    size_samples = np.percentile(nodes["frequency"], [35, 65, 90]).astype(int)
    y_base = 0.74
    for idx, freq in enumerate(size_samples):
        size = 40 + 16 * np.sqrt(freq) + 90 * np.percentile(nodes["weighted_degree"], 60)
        ax.scatter(0.12 + idx * 0.17, y_base, s=size, color="#AEB7C2", edgecolors="#FBF9F4", linewidths=0.9)
        ax.text(0.12 + idx * 0.17, y_base - 0.09, f"{freq} papers", ha="center", fontsize=8.9)

    ax.text(0.0, 0.63, "Thematic clusters", fontsize=12.0, fontweight="semibold", va="top")
    y = 0.59
    for _, row in clusters.sort_values("total_frequency", ascending=False).iterrows():
        ax.add_patch(Rectangle((0.0, y - 0.018), 0.04, 0.028, facecolor=color_map[int(row["cluster"])], edgecolor="none"))
        ax.text(0.055, y, f"Cluster {int(row['cluster'])}: {row['cluster_label']}", fontsize=9.9, va="center")
        ax.text(0.055, y - 0.038, row["top_terms"].replace(" | ", ", "), fontsize=8.7, color=BASE_COLORS["slate"], va="center")
        y -= 0.095

    ax.text(0.0, 0.05, f"Displayed concepts: {len(nodes)}\nDisplayed edges: {len(edges)}", fontsize=9.2, color=BASE_COLORS["slate"])


def render_concept_map(
    summary: dict,
    nodes_file: str,
    edges_file: str,
    clusters_file: str,
    stem: str,
    title: str,
    subtitle: str,
    purpose: str,
    subset_note: str,
    changes: list[str],
    threshold_notes: list[str],
) -> dict:
    nodes = pd.read_csv(TABLE_DIR / nodes_file)
    edges = pd.read_csv(TABLE_DIR / edges_file)
    clusters = pd.read_csv(TABLE_DIR / clusters_file)
    set_plot_style()
    fig = plt.figure(figsize=(14.2, 8.6))
    gs = fig.add_gridspec(1, 2, width_ratios=[4.4, 1.45], wspace=0.06)
    ax_map = fig.add_subplot(gs[0, 0])
    ax_side = fig.add_subplot(gs[0, 1])
    _draw_network_map(ax_map, nodes, edges, clusters, title, subtitle)
    _draw_network_side_panel(ax_side, nodes, edges, clusters)
    save_figure(fig, stem)

    metadata = _methods_common(summary) | {
        "title": title,
        "purpose": purpose,
        "changes": changes,
        "analysis_steps": [
            "Concept labels were built from normalized OpenAlex keywords, MeSH descriptors, and targeted title/abstract marker matching rather than raw free-text tokens.",
            subset_note,
            "Concept co-occurrence was computed at the paper level and weighted by association strength using co-occurrence divided by the geometric mean of individual concept frequencies.",
            "Louvain community detection defined thematic clusters, and a cluster-aware force layout positioned nodes to emphasize the separation of conceptual regions.",
        ],
        "thresholds": [
            "Generic or non-informative index terms, demographic labels, and method-heavy concepts were excluded before map construction.",
            *threshold_notes,
        ],
        "plotting": [
            "Node size encodes document frequency.",
            "Node color encodes cluster assignment.",
            "Edge width encodes retained co-occurrence strength.",
            "Translucent cluster envelopes and a dedicated side legend panel were added to make the map legible without referring back to the methods.",
        ],
        "interpretation": [
            "This figure should be read as a conceptual landscape of the AhR field rather than as a comprehensive display of every detectable term.",
            "Clusters summarize high-salience thematic neighborhoods and the bridging edges between them.",
        ],
    }
    write_methods_file(METHODS_DIR / f"{stem}.md", metadata)
    return metadata


def _draw_alluvial_ribbon(ax: plt.Axes, x0: float, x1: float, y0: tuple[float, float], y1: tuple[float, float], color: str) -> None:
    ctrl = (x1 - x0) * 0.45
    verts = [
        (x0, y0[0]),
        (x0 + ctrl, y0[0]),
        (x1 - ctrl, y1[0]),
        (x1, y1[0]),
        (x1, y1[1]),
        (x1 - ctrl, y1[1]),
        (x0 + ctrl, y0[1]),
        (x0, y0[1]),
        (x0, y0[0]),
    ]
    codes = [
        Path.MOVETO,
        Path.CURVE4,
        Path.CURVE4,
        Path.CURVE4,
        Path.LINETO,
        Path.CURVE4,
        Path.CURVE4,
        Path.CURVE4,
        Path.CLOSEPOLY,
    ]
    patch = PathPatch(Path(verts, codes), facecolor=color, edgecolor="none", alpha=0.66, zorder=1)
    ax.add_patch(patch)


def render_thematic_evolution(summary: dict) -> dict:
    cluster_period = pd.read_csv(TABLE_DIR / "cluster_period_shares.csv")
    cluster_summary = pd.read_csv(TABLE_DIR / "cluster_summary.csv")
    color_map = _cluster_color_map(cluster_summary)
    periods = list(dict.fromkeys(cluster_period["time_slice"]))
    recent_order = (
        cluster_period[cluster_period["time_slice"] == periods[-1]]
        .sort_values("share", ascending=False)["cluster"]
        .tolist()
    )
    order = recent_order
    gap = 0.012
    positions: dict[tuple[str, int], tuple[float, float]] = {}
    for period in periods:
        period_df = (
            cluster_period[cluster_period["time_slice"] == period]
            .set_index("cluster")
            .reindex(order)
            .fillna({"share": 0.0, "n_papers": 0, "period_total": 1})
            .reset_index()
        )
        y_top = 1.0
        for _, row in period_df.iterrows():
            share = float(row["share"])
            y_bottom = y_top - share
            positions[(period, int(row["cluster"]))] = (y_bottom, y_top)
            y_top = y_bottom - gap

    set_plot_style()
    fig = plt.figure(figsize=(14.0, 8.0))
    gs = fig.add_gridspec(1, 2, width_ratios=[4.0, 1.55], wspace=0.04)
    ax = fig.add_subplot(gs[0, 0])
    side = fig.add_subplot(gs[0, 1])
    xs = np.linspace(0, 2, len(periods))

    for i in range(len(periods) - 1):
        p0 = periods[i]
        p1 = periods[i + 1]
        for cluster in order:
            _draw_alluvial_ribbon(ax, xs[i], xs[i + 1], positions[(p0, cluster)], positions[(p1, cluster)], color_map[int(cluster)])

    for x, period in zip(xs, periods, strict=True):
        period_total = int(cluster_period.loc[cluster_period["time_slice"] == period, "period_total"].iloc[0])
        ax.text(x, 1.03, period, ha="center", fontsize=12.2, fontweight="semibold")
        ax.text(x, 0.995, f"{period_total:,} papers", ha="center", fontsize=9.4, color=BASE_COLORS["slate"])
        ax.add_patch(Rectangle((x - 0.03, 0), 0.06, 1.0, facecolor="#F2ECE0", edgecolor="#D8D0C2", linewidth=0.8, zorder=0))

    ax.set_xlim(-0.25, 2.9)
    ax.set_ylim(0, 1.08)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title("Thematic Evolution of AhR Research", loc="left", pad=14)
    ax.text(
        0.0,
        1.01,
        "Ribbon width shows the share of papers assigned to each thematic cluster within each era.",
        transform=ax.transAxes,
        fontsize=10.2,
        color=BASE_COLORS["slate"],
    )
    for spine in ax.spines.values():
        spine.set_visible(False)

    side.axis("off")
    side.text(0.0, 0.98, "How to read this map", fontsize=12.2, fontweight="semibold", va="top")
    side.text(0.0, 0.92, "Ribbon color: thematic cluster", fontsize=9.8, va="top")
    side.text(0.0, 0.88, "Ribbon width: within-period cluster share", fontsize=9.8, va="top")
    side.text(0.0, 0.84, "Columns: 1980-1999, 2000-2012, 2013-2026", fontsize=9.8, va="top")
    side.text(0.0, 0.76, "Clusters tracked across time", fontsize=12.0, fontweight="semibold", va="top")
    y = 0.71
    recent_period = periods[-1]
    recent = cluster_period[cluster_period["time_slice"] == recent_period].set_index("cluster")
    for _, row in cluster_summary.sort_values("n_papers", ascending=False).iterrows():
        cluster = int(row["cluster"])
        side.add_patch(Rectangle((0.0, y - 0.018), 0.04, 0.028, facecolor=color_map[cluster], edgecolor="none"))
        side.text(0.055, y, f"Cluster {cluster}: {row['cluster_label']}", fontsize=9.5, va="center")
        share = float(recent.loc[cluster, "share"]) if cluster in recent.index else 0.0
        side.text(0.055, y - 0.036, f"Recent-era share: {share:.0%}", fontsize=8.6, color=BASE_COLORS["slate"])
        y -= 0.09

    save_figure(fig, "figure_06_thematic_evolution")
    metadata = _methods_common(summary) | {
        "title": "Thematic Evolution of AhR Research",
        "purpose": "Shows how the major thematic clusters of the AhR field changed across early, middle, and recent eras.",
        "changes": [
            "This figure replaces the earlier heatmap-style evolution view with an alluvial-style cluster-flow map.",
            "The redesign makes the rise of microbiome, barrier, immune, and cancer-linked AhR themes easier to compare against older toxicology-centered themes.",
        ],
        "analysis_steps": [
            "Papers were clustered on TF-IDF concept profiles derived from normalized keyword, MeSH, and targeted title/abstract marker labels.",
            "The concept-profile matrix retained terms with min_df=20, max_df=0.25, and max_features=700 before TruncatedSVD reduction and MiniBatchKMeans clustering.",
            "Cluster assignments were counted within each of the three configured time slices.",
            "Cluster counts were normalized by the number of papers in each period so ribbon widths represent within-period share rather than raw volume only.",
        ],
        "thresholds": [
            "Seven document clusters were retained as a readable thesis-scale thematic summary.",
            "The alluvial order was fixed across periods so changes in ribbon width reflect thematic growth or contraction rather than re-sorting artifacts.",
        ],
        "plotting": [
            "Ribbon color encodes thematic cluster identity.",
            "Ribbon width encodes the share of papers assigned to that cluster within a given period.",
            "Period headers include the number of papers in each era to make denominator changes explicit.",
        ],
        "interpretation": [
            "Expanding ribbons in the recent era indicate themes that gained relative prominence, such as microbiome, barrier, immune, and tryptophan-linked work.",
            "Narrowing ribbons point to themes that became relatively less dominant as the field diversified.",
        ],
    }
    write_methods_file(METHODS_DIR / "figure_06_thematic_evolution.md", metadata)
    return metadata


def render_cluster_map(summary: dict) -> dict:
    docs = pd.read_csv(TABLE_DIR / "cluster_assignments.csv")
    clusters = pd.read_csv(TABLE_DIR / "cluster_summary.csv")
    color_map = _cluster_color_map(clusters)
    docs["x_plot"] = (docs["x"] - docs["x"].median()) / docs["x"].std(ddof=0)
    docs["y_plot"] = (docs["y"] - docs["y"].median()) / docs["y"].std(ddof=0)
    centers = docs.groupby("cluster")[["x_plot", "y_plot"]].median().reset_index().merge(
        clusters[["cluster", "cluster_label", "n_papers", "median_year", "top_terms"]],
        on="cluster",
        how="left",
    )

    set_plot_style()
    fig = plt.figure(figsize=(14.0, 8.4))
    gs = fig.add_gridspec(1, 2, width_ratios=[4.0, 1.55], wspace=0.04)
    ax = fig.add_subplot(gs[0, 0])
    side = fig.add_subplot(gs[0, 1])

    for cluster_id, subset in docs.groupby("cluster"):
        points = subset[["x_plot", "y_plot"]].to_numpy()
        center = points.mean(axis=0)
        if len(points) > 2:
            cov = np.cov(points.T)
            eigvals, eigvecs = np.linalg.eigh(cov)
            order = np.argsort(eigvals)[::-1]
            eigvals = eigvals[order]
            eigvecs = eigvecs[:, order]
            angle = np.degrees(np.arctan2(eigvecs[1, 0], eigvecs[0, 0]))
            width = 4.2 * np.sqrt(max(eigvals[0], 0.03)) + 0.7
            height = 4.2 * np.sqrt(max(eigvals[-1], 0.03)) + 0.55
            ax.add_patch(
                Ellipse(
                    xy=center,
                    width=width,
                    height=height,
                    angle=angle,
                    facecolor=color_map[int(cluster_id)],
                    edgecolor="none",
                    alpha=0.10,
                    zorder=0,
                )
            )
        ax.scatter(
            subset["x_plot"],
            subset["y_plot"],
            s=14,
            color=color_map[int(cluster_id)],
            alpha=0.18,
            edgecolors="none",
            zorder=1,
        )

    label_offsets = {
        1: (-0.42, 0.22),
        2: (-0.26, -0.22),
        3: (0.32, -0.16),
        4: (0.25, 0.20),
        5: (0.35, -0.08),
        6: (-0.35, 0.05),
        7: (0.18, 0.28),
    }
    label_centers = centers.sort_values("n_papers", ascending=False).head(5)
    for _, row in label_centers.iterrows():
        terms = row["top_terms"].split(", ")
        offset_x, offset_y = label_offsets.get(int(row["cluster"]), (0.0, 0.0))
        label = f"Cluster {int(row['cluster'])}\n{row['cluster_label']}\n{', '.join(terms[:3])}"
        ax.text(
            row["x_plot"] + offset_x,
            row["y_plot"] + offset_y,
            label,
            ha="center",
            va="center",
            fontsize=9.6,
            bbox={"boxstyle": "round,pad=0.24", "fc": "#FBF9F4", "ec": "none", "alpha": 0.88},
            zorder=2,
        )

    ax.set_title("Document Landscape of AhR Research Themes", loc="left", pad=14)
    ax.text(
        0.0,
        1.01,
        "Each point is one paper positioned in 2D concept space; colored islands summarize the major thematic clusters.",
        transform=ax.transAxes,
        fontsize=10.2,
        color=BASE_COLORS["slate"],
    )
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)

    side.axis("off")
    side.text(0.0, 0.98, "How to read this map", fontsize=12.2, fontweight="semibold", va="top")
    side.text(0.0, 0.92, "Each point: one paper", fontsize=9.8, va="top")
    side.text(0.0, 0.88, "Color and island envelope: thematic cluster", fontsize=9.8, va="top")
    side.text(0.0, 0.84, "Distances: qualitative similarity in concept-profile space", fontsize=9.8, va="top")
    side.text(0.0, 0.76, "Cluster summaries", fontsize=12.0, fontweight="semibold", va="top")
    y = 0.71
    for _, row in clusters.sort_values("n_papers", ascending=False).iterrows():
        cluster = int(row["cluster"])
        side.add_patch(Rectangle((0.0, y - 0.018), 0.04, 0.028, facecolor=color_map[cluster], edgecolor="none"))
        side.text(0.055, y, f"Cluster {cluster}: {row['cluster_label']}", fontsize=9.5, va="center")
        side.text(0.055, y - 0.036, f"{int(row['n_papers']):,} papers | median year {int(row['median_year'])}", fontsize=8.6, color=BASE_COLORS["slate"])
        y -= 0.09

    save_figure(fig, "figure_07_thematic_cluster_map")
    metadata = _methods_common(summary) | {
        "title": "Document Landscape of AhR Research Themes",
        "purpose": "Provides a document-level thematic landscape complementary to the term co-occurrence concept map.",
        "changes": [
            "This figure replaces the earlier bubble-only cluster summary with a true document landscape.",
            "The redesign is intentionally complementary to Figure 04: Figure 04 maps concept co-occurrence, whereas Figure 07 maps papers in concept-profile space.",
        ],
        "analysis_steps": [
            "Each paper was represented by a TF-IDF concept profile derived from normalized keyword, MeSH, and targeted title/abstract concept labels.",
            "The document concept matrix retained terms with min_df=20, max_df=0.25, and max_features=700; 12 latent components were used for clustering and a separate 2D TruncatedSVD projection was used for plotting.",
            "MiniBatchKMeans partitioned papers into seven thematic clusters.",
            "A 2D TruncatedSVD embedding was used for visualization, and cluster centroids plus envelopes summarize the dominant regions of concept space.",
        ],
        "thresholds": [
            "Seven clusters were retained as a pragmatic thesis-scale compromise between detail and readability.",
            "Concept terms entered the document space only if they appeared in at least 20 papers and in no more than 25% of the corpus.",
        ],
        "plotting": [
            "Each point represents one paper.",
            "Point color and the translucent cluster envelope encode thematic cluster membership.",
            "Cluster labels show the cluster theme plus leading representative concepts.",
        ],
        "interpretation": [
            "Papers that occupy the same island share similar AhR-associated concept profiles.",
            "This figure is a field-structure view rather than a citation or chronology map, so distances should be read qualitatively.",
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


def render_all_figures(summary: dict, include: set[str] | None = None) -> list[dict]:
    renderers = {
        "figure_01_publications_over_time": lambda: render_publications_over_time(summary),
        "figure_02_disease_application_distribution": lambda: render_disease_distribution(summary),
        "figure_03_disease_application_trends": lambda: render_disease_trends(summary),
        "figure_04_keyword_network_all_corpus": lambda: render_concept_map(
            summary,
            nodes_file="network_all_nodes.csv",
            edges_file="network_all_edges.csv",
            clusters_file="network_all_clusters.csv",
            stem="figure_04_keyword_network_all_corpus",
            title="Conceptual Landscape of AhR Research",
            subtitle="Curated concept co-occurrence map across the full validated AhR corpus",
            purpose="Maps the major conceptual regions of the AhR field using curated concept labels rather than raw token fragments.",
            subset_note="The full validated AhR corpus was used.",
            changes=[
                "This figure replaces the earlier generic force-directed NetworkX graph with a curated concept map built from concept labels and cluster-aware positioning.",
                "The updated design adds explicit explanations for node size, node color, and edge meaning, and it uses a side legend plus cluster envelopes to create a more VOSviewer-like field map.",
            ],
            threshold_notes=[
                "Concept labels had to appear in at least 140 papers to be eligible, and the map was capped at the 42 most prevalent retained concepts.",
                "Edges were retained only when at least 26 papers carried the concept pair and the association-strength weight was at least 0.11.",
            ],
        ),
        "figure_05_keyword_network_immune_barrier_microbiome": lambda: render_concept_map(
            summary,
            nodes_file="network_focus_nodes.csv",
            edges_file="network_focus_edges.csv",
            clusters_file="network_focus_clusters.csv",
            stem="figure_05_keyword_network_immune_barrier_microbiome",
            title="Immune-Microbiome-Barrier AhR Sublandscape",
            subtitle="Focused concept map of the microbiome, gut, mucosal, inflammatory, and immunoregulatory AhR literature",
            purpose="Highlights the thesis-relevant AhR sublandscape spanning microbiome, barrier biology, inflammation, and immune regulation.",
            subset_note="Only papers carrying immune, microbiome, barrier, inflammation, gut, or intestinal focus tags were used.",
            changes=[
                "This figure replaces the earlier weak subnetwork graph with a focused concept map built from a targeted AhR immune-microbiome-barrier subset.",
                "The updated version removes low-value verbs and uses curated concept labels, explicit legend text, and stronger cluster structure so the figure reads as a coherent subfield map.",
            ],
            threshold_notes=[
                "Concept labels had to appear in at least 45 papers within the focus subset, and the map was capped at the 36 most prevalent retained concepts.",
                "Edges were retained only when at least 12 papers carried the concept pair and the association-strength weight was at least 0.11.",
            ],
        ),
        "figure_06_thematic_evolution": lambda: render_thematic_evolution(summary),
        "figure_07_thematic_cluster_map": lambda: render_cluster_map(summary),
        "figure_08_top_journals": lambda: render_top_journals(summary),
    }
    outputs = []
    for stem, renderer in renderers.items():
        if include is None or stem in include:
            outputs.append(renderer())
    return outputs
