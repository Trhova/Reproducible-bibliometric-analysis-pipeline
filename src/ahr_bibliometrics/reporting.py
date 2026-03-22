from __future__ import annotations

import gzip
import json
from pathlib import Path
import re

from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import pandas as pd

from .config import FIGURE_DIR, METHODS_DIR, TABLE_DIR, load_project_config, project_paths


def _pretty_subset_name(name: str) -> str:
    return name.replace("_", " ").title()


def _load_report_inputs() -> dict:
    config = load_project_config()
    paths = project_paths(config)
    corpus_summary = json.loads(paths.corpus_summary.read_text(encoding="utf-8"))
    analysis_summary = json.loads((TABLE_DIR / "analysis_summary.json").read_text(encoding="utf-8"))
    geography_summary = json.loads((TABLE_DIR / "geography_summary.json").read_text(encoding="utf-8"))
    works = pd.read_csv(paths.works)
    fetch_summary = pd.read_csv(paths.fetch_summary) if paths.fetch_summary.exists() else pd.DataFrame()

    subset_counts = {}
    for subset_name, subset_terms in config.get("analysis", {}).get("focus_subsets", {}).items():
        pattern = "|".join(re.escape(term) for term in subset_terms)
        subset_counts[subset_name] = int(works["focus_tags"].fillna("").str.contains(pattern, regex=True).sum()) if pattern else 0

    return {
        "config": config,
        "paths": paths,
        "corpus_summary": corpus_summary,
        "analysis_summary": analysis_summary,
        "geography_summary": geography_summary,
        "works": works,
        "fetch_summary": fetch_summary,
        "subset_counts": subset_counts,
    }


def _count_jsonl_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def _build_flow_steps(inputs: dict) -> list[tuple[str, int]]:
    corpus = inputs["corpus_summary"]
    fetch_summary = inputs["fetch_summary"]
    subset_counts = inputs["subset_counts"]
    total_retrieved = int(fetch_summary["retrieved_rows_before_dedup"].sum()) if not fetch_summary.empty else corpus.get("n_records_retrieved_before_dedup", 0)
    steps = [
        ("OpenAlex records retrieved", total_retrieved),
        ("Unique candidates after deduplication", int(corpus.get("n_unique_candidates_after_dedup", _count_jsonl_rows(inputs["paths"].raw_records)))),
        ("Validated corpus", int(corpus["n_papers"])),
        ("Papers with abstracts", int(corpus["n_with_abstract"])),
        ("Papers with country metadata", int(inputs["analysis_summary"]["n_papers_with_country_metadata"])),
        ("Papers tagged by disease/application dictionary", int(corpus["n_with_disease_tags"])),
    ]
    for subset_name, count in subset_counts.items():
        steps.append((f"{_pretty_subset_name(subset_name)} subset", int(count)))
    return steps


def _flow_mermaid(steps: list[tuple[str, int]]) -> str:
    lines = ["flowchart TD"]
    for idx, (label, count) in enumerate(steps):
        node_id = f"N{idx + 1}"
        lines.append(f'    {node_id}["{label}<br/>N = {count:,}"]')
    if len(steps) >= 2:
        lines.append("    N1 --> N2")
    if len(steps) >= 3:
        lines.append("    N2 --> N3")
    for idx in range(4, len(steps) + 1):
        lines.append(f"    N3 --> N{idx}")
    return "\n".join(lines) + "\n"


def _write_mermaid_assets(inputs: dict, steps: list[tuple[str, int]]) -> None:
    paths = inputs["paths"]
    mermaid = _flow_mermaid(steps)
    paths.mermaid_flow.write_text(mermaid, encoding="utf-8")
    paths.mermaid_markdown.write_text(
        "\n".join(
            [
                f"# {inputs['config']['project']['short_name']} Corpus Flow",
                "",
                "```mermaid",
                mermaid.rstrip(),
                "```",
                "",
            ]
        ),
        encoding="utf-8",
    )


def _figure_title(stem: str) -> str:
    methods_path = METHODS_DIR / f"{stem}.md"
    if methods_path.exists():
        first_line = methods_path.read_text(encoding="utf-8").splitlines()[0].strip()
        return first_line.lstrip("# ").strip() or stem
    return stem.replace("_", " ").title()


def _report_markdown(inputs: dict, steps: list[tuple[str, int]], figure_stems: list[str]) -> str:
    corpus = inputs["corpus_summary"]
    geography = inputs["geography_summary"]
    lines = [
        f"# {inputs['config']['project']['name']} Report",
        "",
        f"- Corpus name: {corpus.get('corpus_name', inputs['config']['project']['corpus_name'])}",
        f"- Time window: {corpus['year_min']} to {corpus['year_max']}",
        f"- Validated papers: {corpus['n_papers']:,}",
        f"- Abstract coverage: {corpus['n_with_abstract']:,} papers ({corpus['abstract_coverage']:.1%})",
        f"- Country metadata coverage: {geography['n_papers_with_country_metadata']:,} papers ({geography['country_metadata_coverage']:.1%})",
        f"- Disease/application tag coverage: {corpus.get('n_with_disease_tags', int((inputs['works']['disease_tags'].fillna('') != '').sum())):,} papers ({corpus.get('disease_tag_coverage', float((inputs['works']['disease_tags'].fillna('') != '').mean())):.1%})",
        "",
        "## Corpus flow",
        "",
        "```mermaid",
        _flow_mermaid(steps).rstrip(),
        "```",
        "",
        "## Included figures",
    ]
    lines.extend(f"- {stem}: {_figure_title(stem)}" for stem in figure_stems)
    lines.append("")
    return "\n".join(lines)


def _draw_summary_page(pdf: PdfPages, inputs: dict) -> None:
    corpus = inputs["corpus_summary"]
    geography = inputs["geography_summary"]
    analysis = inputs["analysis_summary"]
    config = inputs["config"]
    fig = plt.figure(figsize=(8.27, 11.69), facecolor="#FBF9F4")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")

    ax.text(0.06, 0.94, config["project"]["name"], fontsize=24, fontweight="semibold", color="#1C2331")
    ax.text(0.06, 0.905, config["reporting"]["report_title"], fontsize=13, color="#60708B")
    ax.text(0.06, 0.865, config["project"]["description"], fontsize=10.5, color="#1C2331", wrap=True)
    ax.text(0.06, 0.815, "Query definition", fontsize=13, fontweight="semibold", color="#1C2331")
    ax.text(0.06, 0.785, corpus.get("query_summary", config["project"]["query_summary"]), fontsize=9.8, color="#1C2331", wrap=True)

    stats = [
        ("Validated papers", f"{corpus['n_papers']:,}"),
        ("Time window", f"{corpus['year_min']} to {corpus['year_max']}"),
        ("Abstract coverage", f"{corpus['n_with_abstract']:,} ({corpus['abstract_coverage']:.1%})"),
        ("Country metadata", f"{analysis['n_papers_with_country_metadata']:,} ({geography['country_metadata_coverage']:.1%})"),
        (
            "Disease/application tagged",
            f"{corpus.get('n_with_disease_tags', int((inputs['works']['disease_tags'].fillna('') != '').sum())):,} "
            f"({corpus.get('disease_tag_coverage', float((inputs['works']['disease_tags'].fillna('') != '').mean())):.1%})",
        ),
        (
            "Focus-tagged papers",
            f"{corpus.get('n_with_focus_tags', int((inputs['works']['focus_tags'].fillna('') != '').sum())):,} "
            f"({corpus.get('focus_tag_coverage', float((inputs['works']['focus_tags'].fillna('') != '').mean())):.1%})",
        ),
        ("Journals represented", f"{analysis['n_journals']:,}"),
        ("Countries represented", f"{analysis['n_countries']:,}"),
    ]

    ax.text(0.06, 0.70, "Key corpus statistics", fontsize=13, fontweight="semibold", color="#1C2331")
    start_y = 0.665
    row_h = 0.048
    for idx, (label, value) in enumerate(stats):
        y = start_y - idx * row_h
        ax.add_patch(
            FancyBboxPatch(
                (0.06, y - 0.025),
                0.88,
                0.036,
                boxstyle="round,pad=0.005,rounding_size=0.008",
                linewidth=0.6,
                edgecolor="#D8D0C2",
                facecolor="#F6F1E8" if idx % 2 == 0 else "#FBF9F4",
            )
        )
        ax.text(0.08, y - 0.002, label, fontsize=10.5, color="#1C2331", va="center")
        ax.text(0.92, y - 0.002, value, fontsize=10.5, color="#1C2331", va="center", ha="right")

    ax.text(0.06, 0.22, "Report scope", fontsize=13, fontweight="semibold", color="#1C2331")
    ax.text(
        0.06,
        0.185,
        "The following pages reproduce the generated thesis figures in order. This report is assembled from the current figure files without altering their styling or content.",
        fontsize=10.0,
        color="#1C2331",
        wrap=True,
    )
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def _draw_flow_page(pdf: PdfPages, inputs: dict, steps: list[tuple[str, int]]) -> None:
    fig = plt.figure(figsize=(8.27, 11.69), facecolor="#FBF9F4")
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    ax.text(0.06, 0.94, "Corpus Filtering and Retention Flow", fontsize=20, fontweight="semibold", color="#1C2331")
    ax.text(0.06, 0.905, "Mermaid source is written alongside this PDF so the flow can be reused in thesis documentation.", fontsize=10.5, color="#60708B")

    anchor_x = 0.5
    top_y = 0.82
    box_w = 0.42
    box_h = 0.08
    branch_x = [0.18, 0.5, 0.82]
    branch_y = [0.50, 0.35, 0.20]

    def box(center_x: float, center_y: float, label: str, count: int) -> None:
        ax.add_patch(
            FancyBboxPatch(
                (center_x - box_w / 2, center_y - box_h / 2),
                box_w,
                box_h,
                boxstyle="round,pad=0.01,rounding_size=0.02",
                linewidth=1.0,
                edgecolor="#C8B79A",
                facecolor="#F6E7CF",
            )
        )
        ax.text(center_x, center_y + 0.012, label, fontsize=11.2, color="#1C2331", ha="center", va="center")
        ax.text(center_x, center_y - 0.018, f"N = {count:,}", fontsize=12.2, fontweight="semibold", color="#A44A3F", ha="center", va="center")

    def arrow(start: tuple[float, float], end: tuple[float, float]) -> None:
        ax.add_patch(
            FancyArrowPatch(
                start,
                end,
                arrowstyle="-|>",
                mutation_scale=12,
                linewidth=1.1,
                color="#9B8A73",
                connectionstyle="arc3,rad=0.0",
            )
        )

    box(anchor_x, top_y, steps[0][0], steps[0][1])
    box(anchor_x, top_y - 0.15, steps[1][0], steps[1][1])
    box(anchor_x, top_y - 0.30, steps[2][0], steps[2][1])
    arrow((anchor_x, top_y - box_h / 2), (anchor_x, top_y - 0.15 + box_h / 2))
    arrow((anchor_x, top_y - 0.15 - box_h / 2), (anchor_x, top_y - 0.30 + box_h / 2))

    downstream = steps[3:]
    for idx, step in enumerate(downstream):
        x = branch_x[idx % len(branch_x)]
        y = branch_y[idx // len(branch_x)] if idx // len(branch_x) < len(branch_y) else 0.08
        box(x, y, step[0], step[1])
        arrow((anchor_x, top_y - 0.30 - box_h / 2), (x, y + box_h / 2))

    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def _draw_figure_page(pdf: PdfPages, stem: str) -> None:
    image_path = FIGURE_DIR / f"{stem}.png"
    if not image_path.exists():
        return
    image = mpimg.imread(image_path)
    fig = plt.figure(figsize=(8.27, 11.69), facecolor="#FBF9F4")
    ax = fig.add_axes([0.04, 0.05, 0.92, 0.90])
    ax.imshow(image)
    ax.axis("off")
    fig.suptitle(_figure_title(stem), x=0.05, y=0.975, ha="left", fontsize=14, fontweight="semibold", color="#1C2331")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def build_summary_report() -> Path:
    inputs = _load_report_inputs()
    steps = _build_flow_steps(inputs)
    _write_mermaid_assets(inputs, steps)

    figure_stems = [
        stem
        for stem in inputs["config"]["reporting"].get("figure_order", [])
        if (FIGURE_DIR / f"{stem}.png").exists()
    ]

    inputs["paths"].report_markdown.write_text(_report_markdown(inputs, steps, figure_stems), encoding="utf-8")
    with PdfPages(inputs["paths"].report_pdf) as pdf:
        _draw_summary_page(pdf, inputs)
        _draw_flow_page(pdf, inputs, steps)
        for stem in figure_stems:
            _draw_figure_page(pdf, stem)
    return inputs["paths"].report_pdf
