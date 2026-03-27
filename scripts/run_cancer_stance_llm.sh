#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."
export PYTHONPATH=src

python3 -m bibliometric_pipeline.cli cancer-stance
python3 -m bibliometric_pipeline.cli figures --include figure_11_cancer_stance_over_time
