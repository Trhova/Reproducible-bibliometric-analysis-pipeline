# Reproducible AhR Bibliometric Analysis Pipeline

This repository builds a reproducible bibliometric analysis workflow for the aryl hydrocarbon receptor (AhR) literature using OpenAlex metadata and a conservative local validation layer designed to reduce non-biological `AHR` ambiguity.

When the full pipeline is run, it produces:

- `output/figures/`: thesis-ready candidate figures in `.png`, `.pdf`, and `.svg`
- `output/figure_methods/`: one markdown companion file per figure
- `output/tables/`: reusable analysis tables that support the figures
- `data/raw/` and `data/processed/`: cached metadata and cleaned corpus tables

## Project layout

```text
configs/
  disease_dictionary.yaml
  search_queries.yaml
  stopwords_terms.txt
  synonyms.yaml
data/
  raw/
  processed/
output/
  figure_methods/
  figures/
  tables/
src/
  ahr_bibliometrics/
README.md
Makefile
requirements.txt
```

## What the pipeline does

1. Fetches OpenAlex works using exact title/abstract phrase queries for:
   - `aryl hydrocarbon receptor`
   - `ah receptor`
   - `dioxin receptor`
   - title-level `AHR`
2. Validates each candidate record locally using explicit AhR naming or acronym-plus-biological-context rules.
3. Builds a cleaned corpus table from titles, available abstracts, OpenAlex keywords, and MeSH descriptors.
4. Applies editable text normalization, stopword removal, synonym harmonization, and dictionary-based disease/application tagging.
5. Generates multiple candidate figures:
   - publication growth over time
   - disease/application distribution
   - disease/application trends across time slices
   - full-corpus term co-occurrence network
   - immune-barrier-microbiome subset network
   - thematic term evolution
   - thematic cluster map
   - top journals
6. Writes a methods markdown file for every figure with enough detail for later thesis-methods reuse.

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

Run the full workflow:

```bash
make all
```

Or run stage by stage:

```bash
make fetch
make preprocess
make analyze
make figures
```

You can also call the CLI directly:

```bash
PYTHONPATH=src python3 -m ahr_bibliometrics.cli all
```

## Reproducibility and edit points

- Search logic is stored in [`configs/search_queries.yaml`](/home/trhova/thesis_2026_writing/configs/search_queries.yaml).
- Synonym merging rules are stored in [`configs/synonyms.yaml`](/home/trhova/thesis_2026_writing/configs/synonyms.yaml).
- Domain stopwords are stored in [`configs/stopwords_terms.txt`](/home/trhova/thesis_2026_writing/configs/stopwords_terms.txt).
- Disease/application tagging rules are stored in [`configs/disease_dictionary.yaml`](/home/trhova/thesis_2026_writing/configs/disease_dictionary.yaml).

The default search strategy is intentionally conservative. It is designed to produce an interpretable, defendable AhR corpus rather than the largest possible noisy retrieval. If recall needs to be broadened later, edit the query and validation config rather than changing the downstream analysis code.

## Important caveats

- OpenAlex abstract coverage is incomplete. Disease/application tagging therefore uses titles, available abstracts, OpenAlex keywords, and MeSH descriptors, while the final term-network and clustering analyses rely on title-plus-abstract text for cleaner maps.
- Disease/application tags are dictionary-based approximations and can assign multiple categories to one paper.
- Network views are deliberately pruned for readability; they should be read as high-salience structure rather than exhaustive maps.
