# Figure 00. Corpus filtering and metadata retention flow

## Figure purpose
Summarizes the technical corpus funnel from OpenAlex retrieval through deduplication, validation, and key metadata availability checks.

## Input data
- Corpus: Validated AhR OpenAlex corpus
- Number of papers: 8291
- Time window: 1980 to 2026
- Query strategy: OpenAlex exact-match title/abstract retrieval for "aryl hydrocarbon receptor", "ah receptor", and "dioxin receptor", plus title-level "AHR" hits; local regex validation retained records with explicit AhR naming in the title or abstract-phrase hits supported by biologically relevant title language.

## Preprocessing
- English-language articles and reviews were retained.
- Titles, available abstracts, OpenAlex keywords, and MeSH descriptors were normalized after corpus retrieval.
- Disease/application tagging still uses broad metadata support, but the upgraded landscape figures use curated concept labels derived from normalized OpenAlex keywords, MeSH descriptors, and targeted title/abstract marker matching.
- Text was lowercased, punctuation-normalized, and harmonized with synonym mappings from the active project config.
- Generic bibliometric and non-informative scientific terms from the active project config plus figure-specific concept exclusions were removed from map-style analyses.

## Analysis steps
- The figure uses the raw OpenAlex query summary, the deduplicated raw candidate cache, the validated corpus summary, and downstream metadata coverage counts.
- Retrieved records are counted as the sum of query-level hits before deduplication.
- Unique candidates are counted after merging duplicate OpenAlex works across the configured query set.
- Validated corpus size is taken from the processed corpus after local topic validation.
- Abstract coverage, country-metadata coverage, and disease/application tagging coverage are shown as separate branches from the validated corpus.

## Thresholds and filters
- No analytical thresholding was applied beyond the project-level validation rules already used to construct the corpus.
- The diagram reports technical record counts only and intentionally omits thematic subset branches to preserve readability.

## Plotting settings
- The figure is a static box-and-arrow flow diagram with a restrained thesis-style palette and explicit `N = ...` counts in each node.
- The same underlying count structure is also written to Mermaid source in the report assets so the flow can be reused in documentation.
- The figure was exported as PNG, PDF, and SVG at 400 dpi for thesis use.

## Interpretation notes
- This figure is meant as a technical provenance summary rather than a scientific result figure.
- It clarifies how many records were retrieved, retained, and metadata-complete enough for downstream analyses.

## Caveats
- The corpus favors precision over total recall because ambiguous plain-acronym records were not retrieved exhaustively.
- OpenAlex abstract coverage is incomplete, so concept-map coverage partly depends on keyword and MeSH richness rather than abstract availability alone.
- Dictionary-tagged disease/application assignments are approximate, multi-label, and sensitive to the editable regex dictionary.
- The retrieved-record count sums query hits before deduplication, so one paper can contribute to more than one query-specific retrieval bucket before merging.
- Metadata availability counts are downstream completeness checks, not additional exclusion filters on the validated corpus as a whole.
