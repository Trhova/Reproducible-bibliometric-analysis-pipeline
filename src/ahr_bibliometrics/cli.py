from __future__ import annotations

import argparse

from .config import set_active_project_config
from .pipeline import analyze_data, fetch_data, generate_report, preprocess_data, render_figures, run_all


def main() -> None:
    parser = argparse.ArgumentParser(description="Config-driven reproducible bibliometric analysis pipeline.")
    parser.add_argument(
        "command",
        choices=["fetch", "preprocess", "analyze", "figures", "report", "all"],
        help="Pipeline stage to run.",
    )
    parser.add_argument(
        "--include",
        nargs="*",
        help="Optional figure stems to render when command=figures.",
    )
    parser.add_argument(
        "--config",
        help="Optional path to the active project configuration YAML. Defaults to configs/project.yaml.",
    )
    args = parser.parse_args()
    set_active_project_config(args.config)

    if args.command == "fetch":
        fetch_data()
    elif args.command == "preprocess":
        preprocess_data()
    elif args.command == "analyze":
        analyze_data()
    elif args.command == "figures":
        include = set(args.include) if args.include else None
        render_figures(include=include)
    elif args.command == "report":
        generate_report()
    elif args.command == "all":
        run_all()


if __name__ == "__main__":
    main()
