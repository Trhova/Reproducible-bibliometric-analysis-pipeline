from __future__ import annotations

import argparse

from .pipeline import analyze_data, fetch_data, preprocess_data, render_figures, run_all


def main() -> None:
    parser = argparse.ArgumentParser(description="Reproducible AhR bibliometric analysis pipeline.")
    parser.add_argument(
        "command",
        choices=["fetch", "preprocess", "analyze", "figures", "all"],
        help="Pipeline stage to run.",
    )
    args = parser.parse_args()

    if args.command == "fetch":
        fetch_data()
    elif args.command == "preprocess":
        preprocess_data()
    elif args.command == "analyze":
        analyze_data()
    elif args.command == "figures":
        render_figures()
    elif args.command == "all":
        run_all()


if __name__ == "__main__":
    main()
