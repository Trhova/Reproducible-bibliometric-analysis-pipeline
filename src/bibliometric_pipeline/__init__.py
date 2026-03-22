"""Config-driven reproducible bibliometric analysis pipeline."""

from ahr_bibliometrics.pipeline import analyze_data, fetch_data, generate_report, preprocess_data, render_figures, run_all

__all__ = [
    "analyze_data",
    "fetch_data",
    "generate_report",
    "preprocess_data",
    "render_figures",
    "run_all",
]
