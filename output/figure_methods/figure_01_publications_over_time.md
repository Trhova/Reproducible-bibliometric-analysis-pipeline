# Figure 01. AhR literature growth over time

## Figure purpose
Shows annual publication counts and the cumulative growth trajectory of the validated AhR literature.

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
- Papers were grouped by publication year.
- For 2026, the observed year-to-date count was annualized from the pipeline run date to estimate a year-end total, and the projected remainder was drawn as a hatched bar segment.
- A three-year rolling mean was calculated for a smoothed annual trend line.
- A cumulative count curve was derived from the annual counts.

## Thresholds and filters
- No per-year smoothing beyond a centered three-year rolling mean.
- Corpus restricted to validated English-language articles and reviews.

## Plotting settings
- Top panel uses muted teal bars plus a contrasting brick trend line; the observed 2026 count remains solid while the projected remainder is hatched.
- Bottom panel uses a cumulative area-and-line treatment for thesis-friendly readability, with a dashed extension for the projected 2026 year-end total.
- Exports were saved as PNG, PDF, and SVG at 400 dpi.

## Interpretation notes
- This figure is suited to framing AhR as a mature but still expanding field.
- Inflection points can be compared against historical shifts from toxicology-centric work toward immunity, microbiome, and cancer themes.

## Caveats
- The corpus favors precision over total recall because ambiguous plain-acronym records were not retrieved exhaustively.
- OpenAlex abstract coverage is incomplete, so concept-map coverage partly depends on keyword and MeSH richness rather than abstract availability alone.
- Dictionary-tagged disease/application assignments are approximate, multi-label, and sensitive to the editable regex dictionary.
- The 2026 year-end estimate is a simple projection from papers indexed through March 24, 2026 and assumes roughly steady within-year accrual.
- OpenAlex indexing and validation timing are not uniform within a year, so the projected segment is intended to prevent a misleading visual dip rather than to serve as a forecast claim.
