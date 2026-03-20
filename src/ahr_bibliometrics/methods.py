from __future__ import annotations

from pathlib import Path


def write_methods_file(path: Path, metadata: dict) -> None:
    lines = [
        f"# {metadata['title']}",
        "",
        "## Figure purpose",
        metadata["purpose"],
        "",
        "## Input data",
        f"- Corpus: {metadata['corpus_name']}",
        f"- Number of papers: {metadata['n_papers']}",
        f"- Time window: {metadata['time_window']}",
        f"- Query strategy: {metadata['query_summary']}",
        "",
        "## Preprocessing",
    ]
    lines.extend(f"- {item}" for item in metadata["preprocessing"])
    lines.extend(["", "## Analysis steps"])
    lines.extend(f"- {item}" for item in metadata["analysis_steps"])
    lines.extend(["", "## Thresholds and filters"])
    lines.extend(f"- {item}" for item in metadata["thresholds"])
    lines.extend(["", "## Plotting settings"])
    lines.extend(f"- {item}" for item in metadata["plotting"])
    lines.extend(["", "## Interpretation notes"])
    lines.extend(f"- {item}" for item in metadata["interpretation"])
    lines.extend(["", "## Caveats"])
    lines.extend(f"- {item}" for item in metadata["caveats"])
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

