from __future__ import annotations

from datetime import date
import json
from pathlib import Path as FilePath
from urllib.request import Request, urlopen
from matplotlib.collections import PatchCollection
from matplotlib.lines import Line2D
from matplotlib.patches import Ellipse, PathPatch, Polygon, Rectangle
from matplotlib.path import Path
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter
import numpy as np
import pandas as pd
import seaborn as sns

from .config import FIGURE_DIR, METHODS_DIR, RAW_DIR, TABLE_DIR, load_project_config
from .methods import write_methods_file
from .reporting import build_corpus_flow_steps, draw_corpus_flow_diagram, load_report_inputs


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
GEOGRAPHY_THEME_PALETTE = {
    "Toxicology / xenobiotics": "#A44A3F",
    "Cancer": "#C08A3E",
    "Immune / inflammation": "#377D86",
    "Microbiome / barrier": "#5F8F7A",
    "Liver / metabolism": "#60708B",
}
WORLD_GEOJSON_URL = "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/ne_110m_admin_0_countries.geojson"
COUNTRY_LABEL_OFFSETS = {
    "US": (0, -4),
    "CN": (8, -2),
    "JP": (10, 0),
    "DE": (2, -2),
    "CA": (-8, 6),
    "KR": (10, -1),
    "TW": (12, -2),
    "GB": (-8, 2),
    "FR": (-4, -4),
    "SE": (6, 4),
}
COUNTRY_LABEL_OFFSETS_PER_CAPITA = {
    "US": (0, -4),
    "CA": (-8, 6),
    "SE": (8, 8),
    "FI": (18, 2),
    "NO": (0, -6),
    "CZ": (0, 12),
    "CH": (0, -10),
    "TW": (12, -2),
}
COUNTRY_NAME_OVERRIDES = {
    "US": "United States",
    "GB": "United Kingdom",
    "KR": "South Korea",
    "TW": "Taiwan",
    "CZ": "Czech Republic",
}


def set_plot_style() -> None:
    sns.set_theme(style="whitegrid")
    mpl.rcParams.update(
        {
            "font.family": "DejaVu Serif",
            "axes.facecolor": "#FFFFFF",
            "figure.facecolor": "#FFFFFF",
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


def _world_geojson_path() -> FilePath:
    return RAW_DIR / "reference" / "ne_110m_admin_0_countries.geojson"


def _ensure_world_geojson() -> FilePath:
    path = _world_geojson_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        return path
    request = Request(WORLD_GEOJSON_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urlopen(request, timeout=60) as response:
        payload = response.read().decode("utf-8")
    path.write_text(payload, encoding="utf-8")
    return path


def _load_world_features() -> list[dict]:
    path = _ensure_world_geojson()
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["features"]


def _feature_iso2(properties: dict) -> str | None:
    for key in ["ISO_A2", "ISO_A2_EH", "WB_A2", "POSTAL"]:
        value = str(properties.get(key) or "").strip()
        if len(value) == 2 and value != "-99":
            return value
    return None


def _feature_name(properties: dict, iso2: str | None) -> str:
    if iso2 and iso2 in COUNTRY_NAME_OVERRIDES:
        return COUNTRY_NAME_OVERRIDES[iso2]
    return str(properties.get("NAME_LONG") or properties.get("ADMIN") or properties.get("NAME") or iso2 or "Unknown")


def _iter_feature_polygons(geometry: dict) -> list[np.ndarray]:
    polygons: list[np.ndarray] = []
    if not geometry:
        return polygons
    if geometry.get("type") == "Polygon":
        if geometry.get("coordinates"):
            polygons.append(np.asarray(geometry["coordinates"][0], dtype=float))
    elif geometry.get("type") == "MultiPolygon":
        for polygon in geometry.get("coordinates", []):
            if polygon:
                polygons.append(np.asarray(polygon[0], dtype=float))
    return polygons


def _methods_common(summary: dict) -> dict:
    short_name = summary.get("project_short_name", "AhR")
    return {
        "corpus_name": summary.get("corpus_name", f"Validated {short_name} OpenAlex corpus"),
        "n_papers": summary["n_papers"],
        "time_window": f"{summary['year_min']} to {summary['year_max']}",
        "query_summary": summary.get("query_summary", ""),
        "preprocessing": [
            "English-language articles and reviews were retained.",
            "Titles, available abstracts, OpenAlex keywords, and MeSH descriptors were normalized after corpus retrieval.",
            "Disease/application tagging still uses broad metadata support, but the upgraded landscape figures use curated concept labels derived from normalized OpenAlex keywords, MeSH descriptors, and targeted title/abstract marker matching.",
            "Text was lowercased, punctuation-normalized, and harmonized with synonym mappings from the active project config.",
            "Generic bibliometric and non-informative scientific terms from the active project config plus figure-specific concept exclusions were removed from map-style analyses.",
        ],
        "caveats": [
            "The corpus favors precision over total recall because ambiguous plain-acronym records were not retrieved exhaustively.",
            "OpenAlex abstract coverage is incomplete, so concept-map coverage partly depends on keyword and MeSH richness rather than abstract availability alone.",
            "Dictionary-tagged disease/application assignments are approximate, multi-label, and sensitive to the editable regex dictionary.",
        ],
    }


def render_corpus_flow(summary: dict) -> dict:
    inputs = load_report_inputs()
    steps = build_corpus_flow_steps(inputs)
    set_plot_style()
    fig, ax = plt.subplots(figsize=(11.2, 7.8))
    draw_corpus_flow_diagram(
        ax,
        steps,
        title="Corpus Filtering and Retention Flow",
        subtitle="Technical overview of retrieval, deduplication, validation, and metadata availability.",
        footnote="Counts are drawn from the current cached retrieval, validated corpus table, and downstream metadata coverage summaries.",
    )
    save_figure(fig, "figure_00_corpus_flow_summary")

    metadata = _methods_common(summary) | {
        "title": "Figure 00. Corpus filtering and metadata retention flow",
        "purpose": "Summarizes the technical corpus funnel from OpenAlex retrieval through deduplication, validation, and key metadata availability checks.",
        "analysis_steps": [
            "The figure uses the raw OpenAlex query summary, the deduplicated raw candidate cache, the validated corpus summary, and downstream metadata coverage counts.",
            "Retrieved records are counted as the sum of query-level hits before deduplication.",
            "Unique candidates are counted after merging duplicate OpenAlex works across the configured query set.",
            "Validated corpus size is taken from the processed corpus after local topic validation.",
            "Abstract coverage, country-metadata coverage, and disease/application tagging coverage are shown as separate branches from the validated corpus.",
        ],
        "thresholds": [
            "No analytical thresholding was applied beyond the project-level validation rules already used to construct the corpus.",
            "The diagram reports technical record counts only and intentionally omits thematic subset branches to preserve readability.",
        ],
        "plotting": [
            "The figure is a static box-and-arrow flow diagram with a restrained thesis-style palette and explicit `N = ...` counts in each node.",
            "The same underlying count structure is also written to Mermaid source in the report assets so the flow can be reused in documentation.",
            "The figure was exported as PNG, PDF, and SVG at 400 dpi for thesis use.",
        ],
        "interpretation": [
            "This figure is meant as a technical provenance summary rather than a scientific result figure.",
            "It clarifies how many records were retrieved, retained, and metadata-complete enough for downstream analyses.",
        ],
        "caveats": _methods_common(summary)["caveats"] + [
            "The retrieved-record count sums query hits before deduplication, so one paper can contribute to more than one query-specific retrieval bucket before merging.",
            "Metadata availability counts are downstream completeness checks, not additional exclusion filters on the validated corpus as a whole.",
        ],
    }
    write_methods_file(METHODS_DIR / "figure_00_corpus_flow_summary.md", metadata)
    return metadata


def render_publications_over_time(summary: dict) -> dict:
    short_name = summary.get("project_short_name", "AhR")
    annual = pd.read_csv(TABLE_DIR / "publication_counts.csv")
    annual_display = annual.copy()
    today = date.today()
    projected_label = None
    projection_note = None
    projected_total = None
    observed_total = None
    current_year = int(today.year)
    if current_year in annual_display["publication_year"].values and today < date(current_year, 12, 31):
        observed_total = int(annual_display.loc[annual_display["publication_year"] == current_year, "publications"].iloc[0])
        days_elapsed = today.timetuple().tm_yday
        days_in_year = 366 if date(current_year, 12, 31).timetuple().tm_yday == 366 else 365
        year_fraction = max(days_elapsed / days_in_year, 1 / days_in_year)
        projected_total = int(round(observed_total / year_fraction))
        annual_display.loc[annual_display["publication_year"] == current_year, "publications"] = projected_total
        annual_display["rolling_mean_3y"] = annual_display["publications"].rolling(3, min_periods=1).mean()
        annual_display["cumulative_publications"] = annual_display["publications"].cumsum()
        projected_label = f"{current_year} projected from Jan 1-{today.strftime('%b %d, %Y')}"
        projection_note = (
            f"{current_year} observed: {observed_total} papers by {today.strftime('%B %-d, %Y')}; "
            f"year-end projection: {projected_total}"
        )

    set_plot_style()
    fig, axes = plt.subplots(2, 1, figsize=(11.5, 8), sharex=True, gridspec_kw={"height_ratios": [2.3, 1]})

    axes[0].bar(annual["publication_year"], annual["publications"], color=BASE_COLORS["teal"], alpha=0.85, width=0.8)
    if projected_total is not None and observed_total is not None and projected_total > observed_total:
        axes[0].bar(
            [current_year],
            [projected_total - observed_total],
            bottom=[observed_total],
            color=BASE_COLORS["teal"],
            alpha=0.20,
            width=0.8,
            hatch="///",
            edgecolor=BASE_COLORS["teal"],
            linewidth=0.0,
        )
    axes[0].plot(annual_display["publication_year"], annual_display["rolling_mean_3y"], color=BASE_COLORS["brick"], linewidth=2.4)
    axes[0].set_ylabel("Publications")
    axes[0].set_title(f"{short_name} Literature Growth")
    axes[0].text(
        0.01,
        0.93,
        f"Validated corpus: {summary['n_papers']:,} papers",
        transform=axes[0].transAxes,
        fontsize=10.5,
        color=BASE_COLORS["ink"],
    )
    if projection_note:
        axes[0].text(
            0.99,
            0.93,
            projection_note,
            transform=axes[0].transAxes,
            fontsize=9.4,
            color=BASE_COLORS["slate"],
            ha="right",
        )
        legend_items = [
            Rectangle((0, 0), 1, 1, facecolor=BASE_COLORS["teal"], alpha=0.85, edgecolor="none", label="Observed annual count"),
            Rectangle((0, 0), 1, 1, facecolor=BASE_COLORS["teal"], alpha=0.20, edgecolor=BASE_COLORS["teal"], hatch="///", label="Projected remainder"),
            Line2D([0], [0], color=BASE_COLORS["brick"], linewidth=2.4, label="3-year rolling mean"),
        ]
        axes[0].legend(handles=legend_items, loc="upper left", bbox_to_anchor=(0.01, 0.84), fontsize=9.2)

    axes[1].fill_between(
        annual["publication_year"],
        annual["cumulative_publications"],
        color=BASE_COLORS["ochre"],
        alpha=0.35,
    )
    axes[1].plot(annual["publication_year"], annual["cumulative_publications"], color=BASE_COLORS["ochre"], linewidth=2.2)
    if projected_total is not None and observed_total is not None:
        prior_mask = annual["publication_year"] < current_year
        if prior_mask.any():
            prior_cumulative = float(annual.loc[prior_mask, "cumulative_publications"].iloc[-1])
            axes[1].plot(
                [current_year - 1, current_year],
                [prior_cumulative, prior_cumulative + projected_total],
                color=BASE_COLORS["ochre"],
                linewidth=2.2,
                linestyle=(0, (4, 3)),
            )
    axes[1].set_ylabel("Cumulative")
    axes[1].set_xlabel("Publication year")
    axes[1].text(
        0.99,
        0.08,
        projected_label or "2026 is a partial year",
        transform=axes[1].transAxes,
        ha="right",
        fontsize=9.5,
        color=BASE_COLORS["ink"],
    )

    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)

    save_figure(fig, "figure_01_publications_over_time")
    metadata = _methods_common(summary) | {
        "title": f"Figure 01. {short_name} literature growth over time",
        "purpose": f"Shows annual publication counts and the cumulative growth trajectory of the validated {short_name} literature.",
        "analysis_steps": [
            "Papers were grouped by publication year.",
            "For 2026, the observed year-to-date count was annualized from the pipeline run date to estimate a year-end total, and the projected remainder was drawn as a hatched bar segment.",
            "A three-year rolling mean was calculated for a smoothed annual trend line.",
            "A cumulative count curve was derived from the annual counts.",
        ],
        "thresholds": [
            "No per-year smoothing beyond a centered three-year rolling mean.",
            "Corpus restricted to validated English-language articles and reviews.",
        ],
        "plotting": [
            "Top panel uses muted teal bars plus a contrasting brick trend line; the observed 2026 count remains solid while the projected remainder is hatched.",
            "Bottom panel uses a cumulative area-and-line treatment for thesis-friendly readability, with a dashed extension for the projected 2026 year-end total.",
            "Exports were saved as PNG, PDF, and SVG at 400 dpi.",
        ],
        "interpretation": [
            f"This figure is suited to framing {short_name} as a mature but still expanding field.",
            "Inflection points can be compared against historical shifts from toxicology-centric work toward immunity, microbiome, and cancer themes.",
        ],
        "caveats": _methods_common(summary)["caveats"] + [
            f"The {current_year} year-end estimate is a simple projection from papers indexed through {today.strftime('%B %-d, %Y')} and assumes roughly steady within-year accrual.",
            "OpenAlex indexing and validation timing are not uniform within a year, so the projected segment is intended to prevent a misleading visual dip rather than to serve as a forecast claim.",
        ],
    }
    write_methods_file(METHODS_DIR / "figure_01_publications_over_time.md", metadata)
    return metadata


def render_disease_distribution(summary: dict) -> dict:
    short_name = summary.get("project_short_name", "AhR")
    disease = pd.read_csv(TABLE_DIR / "disease_distribution.csv").head(10)
    set_plot_style()
    fig, ax = plt.subplots(figsize=(11, 6.8))
    disease = disease.sort_values("n_papers", ascending=True)
    colors = sns.color_palette("crest", n_colors=len(disease))
    ax.barh(disease["category"], disease["n_papers"], color=colors)
    for y, (_, row) in enumerate(disease.iterrows()):
        ax.text(row["n_papers"] + 10, y, f"{row['n_papers']:,} ({row['share']:.0%})", va="center", fontsize=10)
    ax.set_xlabel("Tagged papers")
    ax.set_title(f"Disease and Application Landscape of {short_name} Research")
    ax.spines[["top", "right"]].set_visible(False)
    save_figure(fig, "figure_02_disease_application_distribution")
    metadata = _methods_common(summary) | {
        "title": f"Figure 02. Disease and application distribution across the {short_name} corpus",
        "purpose": f"Summarizes which disease and translational application areas appear most often in the {short_name} literature.",
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
            f"It is useful for arguing whether thesis-relevant application areas are niche or mainstream branches within the wider {short_name} field.",
        ],
    }
    write_methods_file(METHODS_DIR / "figure_02_disease_application_distribution.md", metadata)
    return metadata


def render_disease_trends(summary: dict) -> dict:
    short_name = summary.get("project_short_name", "AhR")
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
    ax.set_title(f"How {short_name} Application Areas Shifted Across Time")
    ax.set_xlabel("Time period")
    ax.set_ylabel("")
    save_figure(fig, "figure_03_disease_application_trends")
    metadata = _methods_common(summary) | {
        "title": f"Figure 03. Disease and application trends across {short_name} field eras",
        "purpose": f"Shows how major {short_name} application areas changed in prominence from early to recent literature.",
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
            f"This figure is suited to discussing whether toxicology-led {short_name} work has broadened toward immune, barrier, microbiome, and cancer contexts over time.",
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
        edgecolors="#FFFFFF",
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
            bbox={"boxstyle": "round,pad=0.18", "fc": "#FFFFFF", "ec": "none", "alpha": 0.84},
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


def _draw_network_side_panel(
    ax: plt.Axes,
    nodes: pd.DataFrame,
    edges: pd.DataFrame,
    clusters: pd.DataFrame,
    *,
    node_size_label: str = "number of papers carrying the concept",
    edge_label: str = "co-occurrence strength between concept labels",
) -> None:
    ax.axis("off")
    color_map = _cluster_color_map(clusters)
    ax.text(0.0, 0.98, "How to read this map", fontsize=12.2, fontweight="semibold", va="top")
    ax.text(0.0, 0.92, f"Node size: {node_size_label}", fontsize=9.8, va="top")
    ax.text(0.0, 0.88, "Node color: thematic cluster from Louvain community detection", fontsize=9.8, va="top")
    ax.text(0.0, 0.84, f"Edge width: {edge_label}", fontsize=9.8, va="top")

    size_samples = np.percentile(nodes["frequency"], [35, 65, 90]).astype(int)
    y_base = 0.74
    for idx, freq in enumerate(size_samples):
        size = 40 + 16 * np.sqrt(freq) + 90 * np.percentile(nodes["weighted_degree"], 60)
        ax.scatter(0.12 + idx * 0.17, y_base, s=size, color="#AEB7C2", edgecolors="#FFFFFF", linewidths=0.9)
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
    node_size_label: str = "number of papers carrying the concept",
    edge_label: str = "co-occurrence strength between concept labels",
    analysis_intro: str = "Concept labels were built from normalized OpenAlex keywords, MeSH descriptors, and targeted title/abstract marker matching rather than raw free-text tokens.",
    interpretation_lead: str | None = None,
) -> dict:
    short_name = summary.get("project_short_name", "AhR")
    nodes = pd.read_csv(TABLE_DIR / nodes_file)
    edges = pd.read_csv(TABLE_DIR / edges_file)
    clusters = pd.read_csv(TABLE_DIR / clusters_file)
    set_plot_style()
    fig = plt.figure(figsize=(14.2, 8.6))
    gs = fig.add_gridspec(1, 2, width_ratios=[4.4, 1.45], wspace=0.06)
    ax_map = fig.add_subplot(gs[0, 0])
    ax_side = fig.add_subplot(gs[0, 1])
    _draw_network_map(ax_map, nodes, edges, clusters, title, subtitle)
    _draw_network_side_panel(
        ax_side,
        nodes,
        edges,
        clusters,
        node_size_label=node_size_label,
        edge_label=edge_label,
    )
    save_figure(fig, stem)

    metadata = _methods_common(summary) | {
        "title": title,
        "purpose": purpose,
        "changes": changes,
        "analysis_steps": [
            analysis_intro,
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
            interpretation_lead or f"This figure should be read as a conceptual landscape of the {short_name} field rather than as a comprehensive display of every detectable term.",
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


def _ordered_periods(values: pd.Series) -> list[str]:
    return list(dict.fromkeys(values.tolist()))


def _alluvial_palette(n: int) -> list[str]:
    base = [
        "#2F6C8F",
        "#C65C3B",
        "#5E8F5B",
        "#A87A2A",
        "#7A5EA6",
        "#C06C84",
        "#3E9A94",
        "#8C4F3D",
        "#4B6FA8",
        "#9A8C3C",
    ]
    if n <= len(base):
        return base[:n]
    extra = sns.color_palette("tab10", n_colors=n - len(base)).as_hex()
    return base + extra


def _build_alluvial_positions(
    data: pd.DataFrame,
    *,
    period_col: str,
    category_col: str,
    share_col: str,
    order: list,
    gap: float = 0.012,
) -> dict[tuple[str, object], tuple[float, float]]:
    positions: dict[tuple[str, object], tuple[float, float]] = {}
    periods = _ordered_periods(data[period_col])
    for period in periods:
        period_df = (
            data[data[period_col] == period]
            .set_index(category_col)
            .reindex(order)
            .fillna({share_col: 0.0})
            .reset_index()
        )
        y_top = 1.0
        for _, row in period_df.iterrows():
            share = float(row[share_col])
            y_bottom = y_top - share
            positions[(period, row[category_col])] = (y_bottom, y_top)
            y_top = y_bottom - gap
    return positions


def _render_alluvial(
    *,
    data: pd.DataFrame,
    summary: dict,
    stem: str,
    title: str,
    subtitle: str,
    period_col: str,
    category_col: str,
    share_col: str,
    total_col: str,
    category_order: list,
    label_lookup: dict,
    color_map: dict,
    side_subtitle_lines: list[str],
    recent_note_fmt: str,
    methods_title: str,
    methods_purpose: str,
    methods_changes: list[str],
    methods_analysis_steps: list[str],
    methods_thresholds: list[str],
    methods_plotting: list[str],
    methods_interpretation: list[str],
    methods_caveats: list[str],
) -> dict:
    periods = _ordered_periods(data[period_col])
    positions = _build_alluvial_positions(
        data,
        period_col=period_col,
        category_col=category_col,
        share_col=share_col,
        order=category_order,
    )

    set_plot_style()
    fig = plt.figure(figsize=(14.0, 8.0))
    gs = fig.add_gridspec(1, 2, width_ratios=[4.0, 1.55], wspace=0.04)
    ax = fig.add_subplot(gs[0, 0])
    side = fig.add_subplot(gs[0, 1])
    xs = np.linspace(0, 2, len(periods))

    for i in range(len(periods) - 1):
        p0 = periods[i]
        p1 = periods[i + 1]
        for category in category_order:
            _draw_alluvial_ribbon(ax, xs[i], xs[i + 1], positions[(p0, category)], positions[(p1, category)], color_map[category])

    for x, period in zip(xs, periods, strict=True):
        period_total = int(data.loc[data[period_col] == period, total_col].iloc[0])
        ax.text(x, 1.03, period, ha="center", fontsize=12.2, fontweight="semibold")
        ax.text(x, 0.995, f"{period_total:,} papers", ha="center", fontsize=9.4, color=BASE_COLORS["slate"])
        ax.add_patch(Rectangle((x - 0.03, 0), 0.06, 1.0, facecolor="#F5F5F5", edgecolor="#D8D0C2", linewidth=0.8, zorder=0))

    ax.set_xlim(-0.25, 2.9)
    ax.set_ylim(0, 1.08)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.set_title(title, loc="left", pad=14)
    ax.text(0.0, 1.01, subtitle, transform=ax.transAxes, fontsize=10.2, color=BASE_COLORS["slate"])
    for spine in ax.spines.values():
        spine.set_visible(False)

    side.axis("off")
    side.text(0.0, 0.98, "How to read this map", fontsize=12.2, fontweight="semibold", va="top")
    y = 0.92
    for line in side_subtitle_lines:
        side.text(0.0, y, line, fontsize=9.8, va="top")
        y -= 0.04
    side.text(0.0, 0.76, "Themes tracked across time", fontsize=12.0, fontweight="semibold", va="top")
    y = 0.71
    recent_period = periods[-1]
    recent = data[data[period_col] == recent_period].set_index(category_col)
    for category in category_order:
        side.add_patch(Rectangle((0.0, y - 0.018), 0.04, 0.028, facecolor=color_map[category], edgecolor="none"))
        side.text(0.055, y, label_lookup[category], fontsize=9.5, va="center")
        share = float(recent.loc[category, share_col]) if category in recent.index else 0.0
        side.text(0.055, y - 0.036, recent_note_fmt.format(share=share), fontsize=8.6, color=BASE_COLORS["slate"])
        y -= 0.09

    save_figure(fig, stem)
    metadata = _methods_common(summary) | {
        "title": methods_title,
        "purpose": methods_purpose,
        "changes": methods_changes,
        "analysis_steps": methods_analysis_steps,
        "thresholds": methods_thresholds,
        "plotting": methods_plotting,
        "interpretation": methods_interpretation,
        "caveats": _methods_common(summary)["caveats"] + methods_caveats,
    }
    write_methods_file(METHODS_DIR / f"{stem}.md", metadata)
    return metadata


def render_thematic_evolution(summary: dict) -> dict:
    short_name = summary.get("project_short_name", "AhR")
    cluster_period = pd.read_csv(TABLE_DIR / "cluster_period_shares.csv")
    merge_map = {
        "Environmental toxicology and liver response": "Environmental toxicology and liver response",
        "Cancer and hormone signaling": "Cancer and hormone signaling",
        "Immune-microbiome signaling": "Immune-microbiome signaling",
        "T cell and cytokine regulation": "T cell and cytokine regulation",
        "CYP1 enzyme induction and toxicology": "CYP1-centered toxicology and transcription",
        "CYP1 toxicology and carcinogenesis": "CYP1-centered toxicology and transcription",
        "ARNT-CYP1 transcriptional response": "CYP1-centered toxicology and transcription",
    }
    cluster_period["display_theme"] = cluster_period["cluster_label"].map(merge_map).fillna(cluster_period["cluster_label"])
    display_period = (
        cluster_period.groupby(["time_slice", "display_theme"], as_index=False)
        .agg(
            share=("share", "sum"),
            n_papers=("n_papers", "sum"),
            period_total=("period_total", "first"),
        )
    )
    periods = _ordered_periods(display_period["time_slice"])
    recent_period = periods[-1]
    order = (
        display_period[display_period["time_slice"] == recent_period]
        .sort_values("share", ascending=False)["display_theme"]
        .tolist()
    )
    palette = _alluvial_palette(len(order))
    color_map = {theme: palette[idx] for idx, theme in enumerate(order)}
    label_lookup = {theme: theme for theme in order}

    return _render_alluvial(
        data=display_period,
        summary=summary,
        stem="figure_06_thematic_evolution",
        title=f"Thematic Evolution of {short_name} Research",
        subtitle="Ribbon width shows the share of papers assigned to each displayed theme within each era.",
        period_col="time_slice",
        category_col="display_theme",
        share_col="share",
        total_col="period_total",
        category_order=order,
        label_lookup=label_lookup,
        color_map=color_map,
        side_subtitle_lines=[
            "Ribbon color: displayed theme",
            "Ribbon width: within-period theme share",
            "Columns: 1980-1999, 2000-2012, 2013-2026",
        ],
        recent_note_fmt="Recent-era share: {share:.0%}",
        methods_title=f"Thematic Evolution of {short_name} Research",
        methods_purpose=f"Shows how the major thematic clusters of the {short_name} field changed across early, middle, and recent eras.",
        methods_changes=[
            "This figure replaces the earlier heatmap-style evolution view with an alluvial-style cluster-flow map.",
            f"The redesign makes the rise of microbiome, barrier, immune, and cancer-linked {short_name} themes easier to compare against older toxicology-centered themes.",
            "Three closely related CYP1-centered unsupervised clusters were collapsed into one displayed super-theme to remove redundant toxicology labels and improve interpretability.",
        ],
        methods_analysis_steps=[
            "Papers were clustered on TF-IDF concept profiles derived from normalized keyword, MeSH, and targeted title/abstract marker labels.",
            "The concept-profile matrix retained terms with min_df=20, max_df=0.25, and max_features=700 before TruncatedSVD reduction and MiniBatchKMeans clustering.",
            "Cluster assignments were counted within each of the three configured time slices.",
            "For visualization, three related CYP1-oriented clusters were merged into one displayed super-theme after clustering because they represented adjacent toxicology/transcriptional neighborhoods with redundant labels.",
            "Displayed theme counts were normalized by the number of papers in each period so ribbon widths represent within-period share rather than raw volume only.",
        ],
        methods_thresholds=[
            "The underlying unsupervised document clustering retained seven clusters.",
            "The displayed alluvial summary collapses those seven clusters into five readable super-themes by merging the three CYP1-centered clusters.",
            "The alluvial order was fixed from the recent era so changes in ribbon width reflect thematic growth or contraction rather than re-sorting artifacts.",
        ],
        methods_plotting=[
            "Ribbon color encodes displayed thematic identity using a categorical palette chosen to maximize separation between themes.",
            "Ribbon width encodes the share of papers assigned to that displayed theme within a given period.",
            "Period headers include the number of papers in each era to make denominator changes explicit.",
            "A side legend lists displayed theme labels and their share in the most recent era.",
        ],
        methods_interpretation=[
            "Expanding ribbons in the recent era indicate displayed themes that gained relative prominence, such as microbiome, barrier, immune, and tryptophan-linked work.",
            "Narrowing ribbons point to displayed themes that became relatively less dominant as the field diversified.",
        ],
        methods_caveats=[
            "Displayed theme labels are heuristic summaries assigned after unsupervised document clustering and should be interpreted as approximate thematic handles rather than fixed ontology classes.",
            "The alluvial diagram tracks relative share within each era, so a ribbon can narrow even if the absolute number of papers in that theme still rose.",
            "The CYP1 merge is a presentation-layer simplification intended to reduce redundant labels, not a rerun of the underlying clustering model.",
        ],
    )


def render_disease_sankey(summary: dict) -> dict:
    short_name = summary.get("project_short_name", "AhR")
    trends = pd.read_csv(TABLE_DIR / "disease_trends.csv")
    if trends.empty:
        return {}
    top_categories = (
        trends.groupby("category")["n_papers"]
        .sum()
        .sort_values(ascending=False)
        .head(8)
        .index
        .tolist()
    )
    display = trends[trends["category"].isin(top_categories)].copy()
    display["display_total"] = display.groupby("period")["share_within_period"].transform("sum")
    display["display_share"] = display["share_within_period"] / display["display_total"]
    periods = _ordered_periods(display["period"])
    order = (
        display[display["period"] == periods[-1]]
        .sort_values("share_within_period", ascending=False)["category"]
        .tolist()
    )
    palette = _alluvial_palette(len(order))
    color_map = {category: palette[idx] for idx, category in enumerate(order)}
    label_lookup = {category: category for category in order}
    return _render_alluvial(
        data=display,
        summary=summary,
        stem="figure_06_1_disease_sankey",
        title=f"Disease and Application Evolution of {short_name} Research",
        subtitle="Ribbon width shows the relative composition of the most prevalent disease/application categories within each era.",
        period_col="period",
        category_col="category",
        share_col="display_share",
        total_col="period_total",
        category_order=order,
        label_lookup=label_lookup,
        color_map=color_map,
        side_subtitle_lines=[
            "Ribbon color: disease/application category",
            "Ribbon width: relative share among displayed categories",
            "Same category framework as Figure 03",
        ],
        recent_note_fmt="Recent displayed share: {share:.0%}",
        methods_title=f"Disease and Application Evolution of {short_name} Research",
        methods_purpose=f"Shows how the most prevalent disease and application categories in the {short_name} corpus changed across early, middle, and recent eras using the same dictionary framework as Figure 03.",
        methods_changes=[
            "This is an added companion to Figure 03, using an alluvial-style display instead of a heatmap.",
            "The figure reuses the disease/application dictionary framework so the temporal shifts are visually easier to compare as flowing category shares across eras.",
        ],
        methods_analysis_steps=[
            "The same dictionary-based disease/application tags used for Figure 03 were counted within each configured time slice.",
            "Papers could contribute to multiple categories because disease/application tagging is multi-label.",
            "Within each period, category counts were first normalized by the number of validated papers in that period, as in Figure 03.",
            "Because the retained categories are multi-label and can overlap, the selected categories were then renormalized within each era so the alluvial widths sum to a readable composition across the displayed categories.",
            "The eight largest categories by total tagged volume were retained for the alluvial view.",
        ],
        methods_thresholds=[
            "Only the eight categories with the largest total tagged volume are shown to keep the alluvial readable.",
            "The underlying category counts are period-normalized, but the displayed ribbon widths are renormalized across the retained categories within each era because multi-label categories do not form a strict partition.",
            "The order was fixed from the recent era so ribbon-width changes are easier to compare.",
        ],
        methods_plotting=[
            "Ribbon color encodes disease/application category identity using a categorical palette chosen to maximize separation between categories.",
            "Ribbon width encodes the relative share of the displayed categories within a given period rather than the raw multi-label share from Figure 03.",
            "A side legend lists the retained categories and their recent-era shares.",
            "The figure was exported as PNG, PDF, and SVG at 400 dpi.",
        ],
        methods_interpretation=[
            "This figure is a dictionary-based application-landscape companion to the unsupervised thematic evolution map in Figure 06.",
            "It makes the relative rise of immune/inflammation, microbiome/barrier, and other translational categories easier to compare directly against classic toxicology-heavy eras.",
        ],
        methods_caveats=[
            "Because disease/application tags are multi-label, the raw shares from Figure 03 overlap and do not sum to 100% within a period.",
            "This alluvial therefore shows the relative composition of the retained displayed categories, not the raw within-period paper share values printed in Figure 03.",
            "This figure captures application framing rather than latent mechanistic document structure.",
        ],
    )


def render_cluster_map(summary: dict) -> dict:
    short_name = summary.get("project_short_name", "AhR")
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
            bbox={"boxstyle": "round,pad=0.24", "fc": "#FFFFFF", "ec": "none", "alpha": 0.88},
            zorder=2,
        )

    ax.set_title(f"Document Landscape of {short_name} Research Themes", loc="left", pad=14)
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
        "title": f"Document Landscape of {short_name} Research Themes",
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
            f"Papers that occupy the same island share similar {short_name}-associated concept profiles.",
            "This figure is a field-structure view rather than a citation or chronology map, so distances should be read qualitatively.",
        ],
    }
    write_methods_file(METHODS_DIR / "figure_07_thematic_cluster_map.md", metadata)
    return metadata


def render_top_journals(summary: dict) -> dict:
    short_name = summary.get("project_short_name", "AhR")
    journals = pd.read_csv(TABLE_DIR / "top_journals.csv").sort_values("n_papers")
    set_plot_style()
    fig, ax = plt.subplots(figsize=(11, 6.8))
    ax.hlines(journals["journal"], 0, journals["n_papers"], color="#CFC8B8", linewidth=2.4)
    ax.scatter(journals["n_papers"], journals["journal"], s=80, color=BASE_COLORS["plum"])
    ax.set_xlabel(f"Validated {short_name} papers")
    ax.set_title(f"Journals Most Frequently Publishing {short_name} Research")
    ax.spines[["top", "right"]].set_visible(False)
    save_figure(fig, "figure_08_top_journals")
    metadata = _methods_common(summary) | {
        "title": f"Figure 08. Journals most frequently publishing {short_name} papers",
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
            f"This figure is a contextual companion, useful for understanding where {short_name} work tends to concentrate institutionally.",
            "It is descriptive only and should not be read as a quality ranking of journals.",
        ],
    }
    write_methods_file(METHODS_DIR / "figure_08_top_journals.md", metadata)
    return metadata


def _prepare_global_geography_inputs() -> tuple[pd.DataFrame, list[np.ndarray], dict, list[str], list[str]]:
    country_activity = pd.read_csv(TABLE_DIR / "country_activity.csv")
    geography_summary = json.loads((TABLE_DIR / "geography_summary.json").read_text(encoding="utf-8"))
    features = _load_world_features()
    counts = dict(zip(country_activity["country"], country_activity["fractional_papers"], strict=False))

    feature_records = []
    for feature in features:
        properties = feature.get("properties", {})
        geometry = feature.get("geometry", {})
        iso2 = _feature_iso2(properties)
        name = _feature_name(properties, iso2)
        if name == "Antarctica":
            continue
        polygons = _iter_feature_polygons(geometry)
        if not polygons:
            continue
        area_score = float(
            sum((coords[:, 0].max() - coords[:, 0].min()) * (coords[:, 1].max() - coords[:, 1].min()) for coords in polygons)
        )
        label_x = properties.get("LABEL_X")
        label_y = properties.get("LABEL_Y")
        if label_x is not None and label_y is not None:
            label_point = (float(label_x), float(label_y))
        else:
            coords = np.vstack(polygons)
            label_point = (float(np.nanmean(coords[:, 0])), float(np.nanmean(coords[:, 1])))
        feature_records.append(
            {
                "iso2": iso2,
                "name": name,
                "properties": properties,
                "polygons": polygons,
                "area_score": area_score,
                "label_point": label_point,
            }
        )

    selected_by_code: dict[str, dict] = {}
    for record in feature_records:
        iso2 = record["iso2"]
        if not iso2:
            continue
        if iso2 not in selected_by_code or record["area_score"] > selected_by_code[iso2]["area_score"]:
            selected_by_code[iso2] = record

    basemap_coords = [coords for record in selected_by_code.values() for coords in record["polygons"]]
    country_rows = []
    for iso2, record in selected_by_code.items():
        if iso2 not in counts:
            continue
        label_x, label_y = record["label_point"]
        country_rows.append(
            {
                "country": iso2,
                "country_name": record["name"],
                "label_x": label_x,
                "label_y": label_y,
                "fractional_papers": float(counts[iso2]),
                "population": float(record["properties"]["POP_EST"]) if record["properties"].get("POP_EST") else np.nan,
            }
        )
    country_points = pd.DataFrame(country_rows)
    country_points["per_million"] = country_points["fractional_papers"] / (country_points["population"] / 1_000_000)
    country_points = country_points.replace([np.inf, -np.inf], np.nan)
    raw_codes = country_points.sort_values("fractional_papers", ascending=False).head(12)["country"].tolist()
    per_capita_codes = (
        country_points[country_points["fractional_papers"] >= 25]
        .sort_values("per_million", ascending=False)
        .head(8)["country"]
        .tolist()
    )
    return country_points, basemap_coords, geography_summary, raw_codes, per_capita_codes


def _bubble_sizes(values: pd.Series, min_size: float = 8.0, max_size: float = 1700.0) -> np.ndarray:
    arr = values.to_numpy(dtype=float)
    arr = np.clip(arr, a_min=0, a_max=None)
    if len(arr) == 0 or np.nanmax(arr) <= 0:
        return np.asarray([])
    root = np.sqrt(arr)
    low = float(np.nanmin(root))
    high = float(np.nanmax(root))
    if np.isclose(low, high):
        return np.full_like(arr, (min_size + max_size) / 2.0)
    return np.interp(root, [low, high], [min_size, max_size])


def _size_handles(values: list[float], series: pd.Series) -> list:
    scaled = _bubble_sizes(pd.Series(values + series.tolist()))
    handle_sizes = scaled[: len(values)]
    return [
        plt.scatter([], [], s=size, facecolor=BASE_COLORS["ochre"], edgecolor=BASE_COLORS["brick"], alpha=0.42, linewidth=0.6)
        for size in handle_sizes
    ]


def _draw_geography_basemap(ax: plt.Axes, basemap_coords: list[np.ndarray]) -> None:
    ax.add_collection(
        PatchCollection(
            [Polygon(coords, closed=True) for coords in basemap_coords],
            facecolor="#ECE8E0",
            edgecolor="#D8D0C2",
            linewidths=0.35,
            zorder=0,
        )
    )
    ax.set_xlim(-170, 190)
    ax.set_ylim(-58, 85)
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)


def _render_geography_bubble_map(
    summary: dict,
    *,
    stem: str,
    title: str,
    subtitle: str,
    value_col: str,
    label_codes: list[str],
    legend_values: list[float],
    legend_title: str,
    label_offsets: dict[str, tuple[int, int]],
    purpose: str,
    interpretation: list[str],
    thresholds: list[str],
    analysis_steps: list[str],
    caveats: list[str],
) -> dict:
    country_points, basemap_coords, geography_summary, _, _ = _prepare_global_geography_inputs()
    panel_df = country_points.dropna(subset=[value_col]).copy()

    set_plot_style()
    fig, ax = plt.subplots(figsize=(10.6, 7.4))
    _draw_geography_basemap(ax, basemap_coords)
    sizes = _bubble_sizes(panel_df[value_col], min_size=10, max_size=1850)
    ax.scatter(
        panel_df["label_x"],
        panel_df["label_y"],
        s=sizes,
        facecolor=BASE_COLORS["ochre"],
        edgecolor=BASE_COLORS["brick"],
        linewidth=0.6,
        alpha=0.42,
        zorder=2,
    )
    ax.set_title(title, loc="left", pad=12)
    ax.text(0.0, 1.01, subtitle, transform=ax.transAxes, fontsize=10.0, color=BASE_COLORS["slate"])
    for _, row in panel_df[panel_df["country"].isin(label_codes)].iterrows():
        dx, dy = label_offsets.get(row["country"], (0, 0))
        ax.text(
            row["label_x"] + dx,
            row["label_y"] + dy,
            row["country_name"],
            fontsize=8.6,
            ha="center",
            va="center",
            bbox={"boxstyle": "round,pad=0.15", "fc": "#FFFFFF", "ec": "none", "alpha": 0.85},
            zorder=3,
        )
    handles = _size_handles(legend_values, panel_df[value_col])
    labels = [f"{value:,.0f}" if value >= 10 else f"{value:.1f}" for value in legend_values]
    ax.legend(
        handles,
        labels,
        title=legend_title,
        loc="lower left",
        bbox_to_anchor=(0.01, 0.02),
        frameon=False,
        labelspacing=1.2,
        handletextpad=1.1,
        fontsize=8.8,
        title_fontsize=9.1,
    )
    fig.text(
        0.015,
        0.03,
        f"Fractional counting distributes each paper across all represented author-affiliation countries. Country metadata available for {geography_summary['n_papers_with_country_metadata']:,} of {summary['n_papers']:,} papers ({geography_summary['country_metadata_coverage']:.0%}).",
        fontsize=9.2,
        color=BASE_COLORS["slate"],
    )
    save_figure(fig, stem)

    metadata = _methods_common(summary) | {
        "title": title,
        "purpose": purpose,
        "analysis_steps": analysis_steps,
        "thresholds": thresholds,
        "plotting": [
            "The figure uses a light gray world basemap with minimal borders and semi-transparent single-color bubbles.",
            "Bubble area, not color, carries the quantitative encoding.",
            "A bubble-size legend was added directly on the map to make the scale explicit.",
            "The figure was exported as PNG, PDF, and SVG at 400 dpi for thesis use.",
        ],
        "interpretation": interpretation,
        "caveats": _methods_common(summary)["caveats"] + caveats,
    }
    write_methods_file(METHODS_DIR / f"{stem}.md", metadata)
    return metadata


def render_global_geography(summary: dict) -> dict:
    short_name = summary.get("project_short_name", "AhR")
    _, _, _, raw_codes, _ = _prepare_global_geography_inputs()
    return _render_geography_bubble_map(
        summary,
        stem="figure_09_global_geography_of_ahr_research",
        title=f"Global {short_name} Research Output",
        subtitle=f"Bubble area shows fractional {short_name} paper count by country.",
        value_col="fractional_papers",
        label_codes=raw_codes,
        legend_values=[50, 250, 1000],
        legend_title=f"Fractional {short_name} papers\n(all-country counting)",
        label_offsets=COUNTRY_LABEL_OFFSETS,
        purpose=f"Shows where {short_name} research is produced globally using a clean bubble map of raw fractional country output.",
        analysis_steps=[
            "Country attribution used the OpenAlex `authorships.countries` metadata already captured in the processed `countries` field.",
            "Each paper was fractionally counted across all unique countries represented on the paper, so a paper with authors from four countries contributed 0.25 to each country.",
            f"The map plots total fractional {short_name} paper output per country.",
            "Country names and map positions were normalized by joining ISO alpha-2 country codes to the cached Natural Earth 1:110m country boundary file.",
        ],
        thresholds=[
            "All countries with valid metadata were eligible for display in the bubble map.",
            "Only the top 12 countries by raw output were labeled directly on the map to avoid crowding.",
        ],
        interpretation=[
            f"This map emphasizes absolute country output in the {short_name} field.",
            f"Large bubbles indicate countries that dominate the validated {short_name} literature in total volume.",
        ],
        caveats=[
            "Geographic attribution depends on country metadata being present in OpenAlex authorships; papers lacking country metadata are excluded from the geography figure.",
            "Fractional counting reduces collaboration-driven overcounting, but it does not distinguish first-author, corresponding-author, or senior-author leadership.",
        ],
    )


def render_global_geography_per_capita(summary: dict) -> dict:
    short_name = summary.get("project_short_name", "AhR")
    _, _, _, _, per_capita_codes = _prepare_global_geography_inputs()
    return _render_geography_bubble_map(
        summary,
        stem="figure_10_global_geography_of_ahr_research_per_capita",
        title=f"Global {short_name} Research Output Per Capita",
        subtitle=f"Bubble area shows fractional {short_name} papers per million inhabitants.",
        value_col="per_million",
        label_codes=per_capita_codes,
        legend_values=[2, 6, 12],
        legend_title=f"Fractional {short_name} papers\nper million inhabitants",
        label_offsets=COUNTRY_LABEL_OFFSETS_PER_CAPITA,
        purpose=f"Shows where {short_name} research is relatively concentrated after normalizing fractional country output by population size.",
        analysis_steps=[
            "Country attribution used the OpenAlex `authorships.countries` metadata already captured in the processed `countries` field.",
            "Each paper was fractionally counted across all unique countries represented on the paper, so a paper with authors from four countries contributed 0.25 to each country.",
            f"The map normalizes fractional {short_name} paper counts by country population using the Natural Earth `POP_EST` value and expresses the result as fractional {short_name} papers per million inhabitants.",
            "Country names and map positions were normalized by joining ISO alpha-2 country codes to the cached Natural Earth 1:110m country boundary file.",
        ],
        thresholds=[
            "Countries with missing or non-positive Natural Earth population estimates were omitted from the per-capita normalization map.",
            "Only the top 8 countries by per-capita output among countries with at least 25 fractional papers were labeled directly on the map to avoid crowding.",
        ],
        interpretation=[
            "This map emphasizes relative research intensity after population normalization.",
            f"Large bubbles can elevate smaller countries with disproportionately strong {short_name} activity compared with raw output alone.",
        ],
        caveats=[
            "Geographic attribution depends on country metadata being present in OpenAlex authorships; papers lacking country metadata are excluded from the geography figure.",
            "Fractional counting reduces collaboration-driven overcounting, but it does not distinguish first-author, corresponding-author, or senior-author leadership.",
            "Per-capita normalization uses Natural Earth population estimates and can be unstable for very small countries, which is why direct labeling is restricted to countries with at least 25 fractional papers.",
        ],
    )


def render_cancer_stance(summary: dict) -> dict:
    short_name = summary.get("project_short_name", "AhR")
    trends = pd.read_csv(TABLE_DIR / "cancer_stance_trends.csv")
    labels = pd.read_csv(TABLE_DIR / "cancer_stance_labels.csv")
    stance_summary = json.loads((TABLE_DIR / "cancer_stance_summary.json").read_text(encoding="utf-8"))
    if trends.empty:
        return {}

    trends["bin_start"] = trends["time_bin"].str.split("-").str[0].astype(int)
    trends = trends.sort_values(["bin_start", "rule_label"])
    order = ["anti_tumor", "pro_tumor", "mixed_context", "unclear"]
    label_lookup = {
        "anti_tumor": "Anti-tumor framing",
        "pro_tumor": "Pro-tumor framing",
        "mixed_context": "Mixed / context-dependent",
        "unclear": "Unclear",
    }
    color_map = {
        "anti_tumor": BASE_COLORS["teal"],
        "pro_tumor": BASE_COLORS["brick"],
        "mixed_context": BASE_COLORS["ochre"],
        "unclear": "#A8AFBA",
    }
    totals = trends[["time_bin", "bin_total", "bin_start"]].drop_duplicates().sort_values("bin_start")

    set_plot_style()
    fig, axes = plt.subplots(
        2,
        1,
        figsize=(11.8, 8.1),
        sharex=True,
        gridspec_kw={"height_ratios": [3.0, 1.0], "hspace": 0.08},
    )
    for label in order:
        subset = trends[trends["rule_label"] == label].copy()
        subset = totals[["time_bin", "bin_start"]].merge(
            subset[["time_bin", "share"]],
            on="time_bin",
            how="left",
        ).fillna({"share": 0.0})
        axes[0].plot(
            subset["bin_start"],
            subset["share"],
            color=color_map[label],
            linewidth=2.6,
            marker="o",
            markersize=4.8,
            label=label_lookup[label],
        )
    axes[0].set_ylim(0, 1.0)
    axes[0].yaxis.set_major_formatter(PercentFormatter(1.0))
    axes[0].set_ylabel("Share of cancer subset")
    axes[0].set_title(f"How {short_name} Is Framed in Cancer-Focused Literature", loc="left", pad=12)
    axes[0].text(
        0.0,
        1.01,
        f"Cancer-related subset: {stance_summary['n_cancer_subset']:,} papers; abstracts available for {stance_summary['n_with_abstract']:,} ({stance_summary['abstract_coverage']:.0%}).",
        transform=axes[0].transAxes,
        fontsize=10.1,
        color=BASE_COLORS["slate"],
    )
    axes[0].legend(ncol=2, loc="upper left", fontsize=9.1, frameon=False)

    axes[1].bar(totals["bin_start"], totals["bin_total"], width=3.7, color=BASE_COLORS["slate"], alpha=0.82)
    axes[1].set_ylabel("Papers")
    axes[1].set_xlabel("Publication period (5-year bins)")
    axes[1].set_xticks(totals["bin_start"])
    axes[1].set_xticklabels(totals["time_bin"], rotation=40, ha="right")

    for ax in axes:
        ax.spines[["top", "right"]].set_visible(False)
        ax.grid(axis="y")

    save_figure(fig, "figure_11_cancer_stance_over_time")
    metadata = _methods_common(summary) | {
        "title": f"Figure 11. How {short_name} is framed in cancer-focused literature over time",
        "purpose": f"Summarizes whether cancer-focused {short_name} papers frame the receptor as pro-tumor, anti-tumor, mixed/context-dependent, or unclear, and how that framing shifts over time.",
        "analysis_steps": [
            "The validated corpus was filtered to papers carrying either the `Cancer` disease tag or the `cancer` focus tag.",
            "Rule-based stance assignment used normalized abstracts as the primary evidence source, with title fallback only when the abstract did not provide a directional signal.",
            "Explicit marker sets captured pro-tumor language, anti-tumor language, and mixed/context-dependent framing.",
            "Papers with no interpretable directional language were left as `Unclear` rather than forcing a polarity label.",
            "For a secondary sensitivity check, an open-source sentence-transformer compared abstract/title text against prototype stance descriptions and the agreement rate was summarized against the rule-based labels.",
            "Counts were aggregated in fixed five-year bins and converted to within-bin shares for plotting.",
        ],
        "thresholds": [
            f"The cancer-focused subset contained {stance_summary['n_cancer_subset']:,} papers, of which {stance_summary['n_with_abstract']:,} ({stance_summary['abstract_coverage']:.0%}) had abstracts.",
            "The primary figure uses the rule-based labels only; the model-assisted layer is exploratory and is included as a sensitivity check rather than the thesis-default claim.",
            "Papers with model text shorter than the configured threshold were not scored by the embedding model.",
        ],
        "plotting": [
            "Colored lines show the within-bin share of cancer-focused papers assigned to each stance class.",
            "A lower bar panel shows the number of cancer-focused papers in each bin so denominator changes remain visible.",
            "Anti-tumor and pro-tumor classes use contrasting teal and brick colors, while mixed/context-dependent and unclear are de-emphasized with ochre and gray.",
        ],
        "interpretation": [
            "This figure should be read as a literature-framing analysis of abstracts and titles, not a direct vote on the true biological role of AhR in cancer.",
            "Rising `mixed / context-dependent` share would indicate that the literature increasingly emphasizes tumor-type, ligand, or immune-context specificity rather than a single universal role.",
        ],
        "caveats": _methods_common(summary)["caveats"] + [
            "Stance labels are based on explicit language in titles and abstracts, so papers that imply a directional role without stating it clearly can remain `Unclear`.",
            "The model-assisted comparison is not a manually validated gold standard; it is a semantic sensitivity analysis intended to show whether a local open-source model broadly agrees with the rule-based calls.",
            "Abstract coverage is incomplete, so some cancer-focused papers can only be classified from titles or not scored by the model layer at all.",
        ],
    }
    write_methods_file(METHODS_DIR / "figure_11_cancer_stance_over_time.md", metadata)
    return metadata


def render_phrase_map(summary: dict) -> dict:
    short_name = summary.get("project_short_name", "AhR")
    return render_concept_map(
        summary,
        nodes_file="phrase_network_nodes.csv",
        edges_file="phrase_network_edges.csv",
        clusters_file="phrase_network_clusters.csv",
        stem="figure_12_global_phrase_map",
        title=f"Paired-Topic Phrase Map of {short_name} Research",
        subtitle=f"Title-and-abstract phrase co-occurrence map showing the major topics most often paired with {short_name}",
        purpose=f"Maps the phrase-level topics most commonly paired with {short_name} across the full validated corpus using title-and-abstract phrase markers rather than metadata concepts.",
        subset_note=f"The full validated {short_name} corpus was used, but only title-and-abstract phrase hits were allowed to enter the map.",
        changes=[
            f"This is a new optional figure designed to answer what topics are most commonly paired with {short_name} in the literature.",
            "Unlike Figures 04 and 05, the phrase map is driven by recurring title-and-abstract phrases rather than the broader keyword/MeSH concept layer.",
        ],
        threshold_notes=[
            "Only configured phrase markers observed in at least the configured minimum number of papers were eligible for display.",
            "Edges were retained only when phrase pairs passed the configured minimum co-occurrence count and association-strength threshold.",
        ],
        node_size_label="number of papers carrying the retained phrase",
        edge_label="co-occurrence strength between retained phrases within the same paper",
        analysis_intro="Phrase labels were built from configured title-and-abstract marker patterns designed to capture recurring AhR-paired topics in human-readable phrase form.",
        interpretation_lead=f"This figure should be read as a literature-derived map of the topics most often paired with {short_name}, not as a map of real search-engine behavior.",
    )


def render_all_figures(summary: dict, include: set[str] | None = None) -> list[dict]:
    short_name = summary.get("project_short_name", "AhR")
    renderers = {
        "figure_00_corpus_flow_summary": lambda: render_corpus_flow(summary),
        "figure_01_publications_over_time": lambda: render_publications_over_time(summary),
        "figure_02_disease_application_distribution": lambda: render_disease_distribution(summary),
        "figure_03_disease_application_trends": lambda: render_disease_trends(summary),
        "figure_04_keyword_network_all_corpus": lambda: render_concept_map(
            summary,
            nodes_file="network_all_nodes.csv",
            edges_file="network_all_edges.csv",
            clusters_file="network_all_clusters.csv",
            stem="figure_04_keyword_network_all_corpus",
            title=f"Conceptual Landscape of {short_name} Research",
            subtitle=f"Curated concept co-occurrence map across the full validated {short_name} corpus",
            purpose=f"Maps the major conceptual regions of the {short_name} field using curated concept labels rather than raw token fragments.",
            subset_note=f"The full validated {short_name} corpus was used.",
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
            title=f"Immune-Microbiome-Barrier {short_name} Sublandscape",
            subtitle=f"Focused concept map of the microbiome, gut, mucosal, inflammatory, and immunoregulatory {short_name} literature",
            purpose=f"Highlights the thesis-relevant {short_name} sublandscape spanning microbiome, barrier biology, inflammation, and immune regulation.",
            subset_note="Only papers carrying immune, microbiome, barrier, inflammation, gut, or intestinal focus tags were used.",
            changes=[
                f"This figure replaces the earlier weak subnetwork graph with a focused concept map built from a targeted {short_name} immune-microbiome-barrier subset.",
                "The updated version removes low-value verbs and uses curated concept labels, explicit legend text, and stronger cluster structure so the figure reads as a coherent subfield map.",
            ],
            threshold_notes=[
                "Concept labels had to appear in at least 45 papers within the focus subset, and the map was capped at the 36 most prevalent retained concepts.",
                "Edges were retained only when at least 12 papers carried the concept pair and the association-strength weight was at least 0.11.",
            ],
        ),
        "figure_06_thematic_evolution": lambda: render_thematic_evolution(summary),
        "figure_06_1_disease_sankey": lambda: render_disease_sankey(summary),
        "figure_07_thematic_cluster_map": lambda: render_cluster_map(summary),
        "figure_08_top_journals": lambda: render_top_journals(summary),
        "figure_09_global_geography_of_ahr_research": lambda: render_global_geography(summary),
        "figure_10_global_geography_of_ahr_research_per_capita": lambda: render_global_geography_per_capita(summary),
        "figure_11_cancer_stance_over_time": lambda: render_cancer_stance(summary),
        "figure_12_global_phrase_map": lambda: render_phrase_map(summary),
    }
    outputs = []
    if include is None:
        stems_to_render = load_project_config().get("reporting", {}).get("figure_order", list(renderers))
    else:
        stems_to_render = [stem for stem in renderers if stem in include]
    for stem in stems_to_render:
        renderer = renderers[stem]
        if include is None or stem in include:
            outputs.append(renderer())
    return outputs
