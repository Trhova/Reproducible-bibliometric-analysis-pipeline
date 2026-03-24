from __future__ import annotations

import gzip
import json
from pathlib import Path

from matplotlib.backends.backend_pdf import PdfPages
import matplotlib.image as mpimg
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
import pandas as pd

from .config import FIGURE_DIR, METHODS_DIR, TABLE_DIR, load_project_config, project_paths


def load_report_inputs() -> dict:
    config = load_project_config()
    paths = project_paths(config)
    corpus_summary = json.loads(paths.corpus_summary.read_text(encoding="utf-8"))
    analysis_summary = json.loads((TABLE_DIR / "analysis_summary.json").read_text(encoding="utf-8"))
    geography_summary = json.loads((TABLE_DIR / "geography_summary.json").read_text(encoding="utf-8"))
    works = pd.read_csv(paths.works)
    fetch_summary = pd.read_csv(paths.fetch_summary) if paths.fetch_summary.exists() else pd.DataFrame()
    return {
        "config": config,
        "paths": paths,
        "corpus_summary": corpus_summary,
        "analysis_summary": analysis_summary,
        "geography_summary": geography_summary,
        "works": works,
        "fetch_summary": fetch_summary,
    }


def _count_jsonl_rows(path: Path) -> int:
    if not path.exists():
        return 0
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def build_corpus_flow_steps(inputs: dict) -> list[dict]:
    corpus = inputs["corpus_summary"]
    fetch_summary = inputs["fetch_summary"]
    works = inputs["works"]
    total_retrieved = int(fetch_summary["retrieved_rows_before_dedup"].sum()) if not fetch_summary.empty else corpus.get("n_records_retrieved_before_dedup", 0)
    return [
        {
            "node": "retrieved",
            "plot_label": "OpenAlex records\nretrieved",
            "mermaid_label": "OpenAlex records retrieved",
            "count": total_retrieved,
        },
        {
            "node": "deduplicated",
            "plot_label": "Unique candidates\nafter deduplication",
            "mermaid_label": "Unique candidates after deduplication",
            "count": int(corpus.get("n_unique_candidates_after_dedup", _count_jsonl_rows(inputs["paths"].raw_records))),
        },
        {
            "node": "validated",
            "plot_label": "Validated corpus",
            "mermaid_label": "Validated corpus",
            "count": int(corpus["n_papers"]),
        },
        {
            "node": "abstracts",
            "plot_label": "Papers with\nabstracts",
            "mermaid_label": "Papers with abstracts",
            "count": int(corpus["n_with_abstract"]),
        },
        {
            "node": "countries",
            "plot_label": "Papers with country\nmetadata",
            "mermaid_label": "Papers with country metadata",
            "count": int(inputs["analysis_summary"]["n_papers_with_country_metadata"]),
        },
        {
            "node": "disease_tags",
            "plot_label": "Papers tagged by disease/\napplication dictionary",
            "mermaid_label": "Papers tagged by disease/application dictionary",
            "count": int(corpus.get("n_with_disease_tags", int((works["disease_tags"].fillna("") != "").sum()))),
        },
    ]


def mermaid_corpus_flow(steps: list[dict]) -> str:
    lines = [
        "flowchart TD",
        '    A["OpenAlex records retrieved<br/>N = ' + f"{steps[0]['count']:,}" + '"]',
        '    B["Unique candidates after deduplication<br/>N = ' + f"{steps[1]['count']:,}" + '"]',
        '    C["Validated corpus<br/>N = ' + f"{steps[2]['count']:,}" + '"]',
        '    D["Papers with abstracts<br/>N = ' + f"{steps[3]['count']:,}" + '"]',
        '    E["Papers with country metadata<br/>N = ' + f"{steps[4]['count']:,}" + '"]',
        '    F["Papers tagged by disease/application dictionary<br/>N = ' + f"{steps[5]['count']:,}" + '"]',
        "    A --> B --> C",
        "    C --> D",
        "    C --> E",
        "    C --> F",
        "    classDef stage fill:#FFFFFF,stroke:#C8B79A,color:#1C2331,stroke-width:1px;",
        "    class A,B,C,D,E,F stage;",
        "    linkStyle default stroke:#9B8A73,stroke-width:1.3px;",
    ]
    return "\n".join(lines) + "\n"


def write_mermaid_assets(inputs: dict, steps: list[dict]) -> None:
    paths = inputs["paths"]
    mermaid = mermaid_corpus_flow(steps)
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


def _report_markdown(inputs: dict, steps: list[dict], figure_stems: list[str]) -> str:
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
        f"- Disease/application tag coverage: {steps[5]['count']:,} papers ({steps[5]['count'] / max(corpus['n_papers'], 1):.1%})",
        "",
        "## Corpus flow",
        "",
        "```mermaid",
        mermaid_corpus_flow(steps).rstrip(),
        "```",
        "",
        "## Included figures",
    ]
    lines.extend(f"- {stem}: {_figure_title(stem)}" for stem in figure_stems)
    lines.append("")
    return "\n".join(lines)


def draw_corpus_flow_diagram(
    ax: plt.Axes,
    steps: list[dict],
    *,
    title: str,
    subtitle: str | None = None,
    footnote: str | None = None,
) -> None:
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    if title:
        ax.text(0.04, 0.95, title, fontsize=18, fontweight="semibold", color="#1C2331", va="top")
    if subtitle:
        ax.text(0.04, 0.905, subtitle, fontsize=10.2, color="#60708B", va="top")

    positions = {
        "retrieved": (0.5, 0.78),
        "deduplicated": (0.5, 0.60),
        "validated": (0.5, 0.42),
        "abstracts": (0.20, 0.17),
        "countries": (0.50, 0.17),
        "disease_tags": (0.80, 0.17),
    }
    box_sizes = {
        "retrieved": (0.34, 0.11),
        "deduplicated": (0.34, 0.11),
        "validated": (0.30, 0.11),
        "abstracts": (0.24, 0.11),
        "countries": (0.24, 0.11),
        "disease_tags": (0.28, 0.11),
    }
    step_map = {step["node"]: step for step in steps}

    def draw_box(node: str) -> None:
        center_x, center_y = positions[node]
        width, height = box_sizes[node]
        ax.add_patch(
            FancyBboxPatch(
                (center_x - width / 2, center_y - height / 2),
                width,
                height,
                boxstyle="round,pad=0.01,rounding_size=0.02",
                linewidth=1.0,
                edgecolor="#C8B79A",
                facecolor="#FFFFFF",
            )
        )
        step = step_map[node]
        ax.text(center_x, center_y + 0.016, step["plot_label"], fontsize=11.4, color="#1C2331", ha="center", va="center")
        ax.text(center_x, center_y - 0.028, f"N = {step['count']:,}", fontsize=13.0, fontweight="semibold", color="#A44A3F", ha="center", va="center")

    def anchor(node: str, direction: str) -> tuple[float, float]:
        center_x, center_y = positions[node]
        width, height = box_sizes[node]
        offsets = {
            "top": (0.0, height / 2),
            "bottom": (0.0, -height / 2),
            "left": (-width / 2, 0.0),
            "right": (width / 2, 0.0),
        }
        dx, dy = offsets[direction]
        return center_x + dx, center_y + dy

    def draw_arrow(start: tuple[float, float], end: tuple[float, float]) -> None:
        ax.add_patch(
            FancyArrowPatch(
                start,
                end,
                arrowstyle="-|>",
                mutation_scale=12,
                linewidth=1.15,
                color="#9B8A73",
                connectionstyle="arc3,rad=0.0",
            )
        )

    for node in positions:
        draw_box(node)

    draw_arrow(anchor("retrieved", "bottom"), anchor("deduplicated", "top"))
    draw_arrow(anchor("deduplicated", "bottom"), anchor("validated", "top"))
    draw_arrow(anchor("validated", "bottom"), anchor("abstracts", "top"))
    draw_arrow(anchor("validated", "bottom"), anchor("countries", "top"))
    draw_arrow(anchor("validated", "bottom"), anchor("disease_tags", "top"))

    if footnote:
        ax.text(0.04, 0.04, footnote, fontsize=9.6, color="#60708B", va="bottom")


def _draw_summary_page(pdf: PdfPages, inputs: dict) -> None:
    corpus = inputs["corpus_summary"]
    geography = inputs["geography_summary"]
    analysis = inputs["analysis_summary"]
    config = inputs["config"]
    works = inputs["works"]
    disease_tagged = int(corpus.get("n_with_disease_tags", int((works["disease_tags"].fillna("") != "").sum())))
    focus_tagged = int(corpus.get("n_with_focus_tags", int((works["focus_tags"].fillna("") != "").sum())))
    fig = plt.figure(figsize=(8.27, 11.69), facecolor="#FFFFFF")
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
        ("Disease/application tagged", f"{disease_tagged:,} ({disease_tagged / max(corpus['n_papers'], 1):.1%})"),
        ("Focus-tagged papers", f"{focus_tagged:,} ({focus_tagged / max(corpus['n_papers'], 1):.1%})"),
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
                facecolor="#F8F8F8" if idx % 2 == 0 else "#FFFFFF",
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


def _draw_flow_page(pdf: PdfPages, inputs: dict, steps: list[dict]) -> None:
    fig = plt.figure(figsize=(8.27, 11.69), facecolor="#FFFFFF")
    ax = fig.add_axes([0.03, 0.05, 0.94, 0.90])
    draw_corpus_flow_diagram(
        ax,
        steps,
        title="Corpus Filtering and Retention Flow",
        subtitle="Technical overview of retrieval, deduplication, validation, and metadata availability.",
        footnote="Editable Mermaid source is written alongside this PDF for reuse in thesis documentation.",
    )
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def _draw_figure_page(pdf: PdfPages, stem: str) -> None:
    image_path = FIGURE_DIR / f"{stem}.png"
    if not image_path.exists():
        return
    image = mpimg.imread(image_path)
    fig = plt.figure(figsize=(8.27, 11.69), facecolor="#FFFFFF")
    ax = fig.add_axes([0.04, 0.05, 0.92, 0.90])
    ax.imshow(image)
    ax.axis("off")
    fig.suptitle(_figure_title(stem), x=0.05, y=0.975, ha="left", fontsize=14, fontweight="semibold", color="#1C2331")
    pdf.savefig(fig, bbox_inches="tight")
    plt.close(fig)


def build_summary_report() -> Path:
    inputs = load_report_inputs()
    steps = build_corpus_flow_steps(inputs)
    write_mermaid_assets(inputs, steps)

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
