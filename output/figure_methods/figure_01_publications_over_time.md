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
- Title-plus-abstract text was used for the main term-network and clustering analyses after broader metadata trials produced noisier concept maps.
- Text was lowercased, punctuation-normalized, and harmonized with editable synonym mappings in configs/synonyms.yaml.
- Generic bibliometric and non-informative scientific terms from configs/stopwords_terms.txt were removed from term-heavy analyses.

## Analysis steps
- Papers were grouped by publication year.
- A three-year rolling mean was calculated for a smoothed annual trend line.
- A cumulative count curve was derived from the annual counts.

## Thresholds and filters
- No per-year smoothing beyond a centered three-year rolling mean.
- Corpus restricted to validated English-language articles and reviews.

## Plotting settings
- Top panel uses muted teal bars plus a contrasting brick trend line.
- Bottom panel uses a cumulative area-and-line treatment for thesis-friendly readability.
- Exports were saved as PNG, PDF, and SVG at 400 dpi.

## Interpretation notes
- This figure is suited to framing AhR as a mature but still expanding field.
- Inflection points can be compared against historical shifts from toxicology-centric work toward immunity, microbiome, and cancer themes.

## Caveats
- The corpus favors precision over total recall because ambiguous plain-AHR abstracts were not retrieved exhaustively.
- OpenAlex abstract coverage is incomplete, so title-only records remain in the corpus when they pass conservative validation.
- Dictionary-tagged disease/application assignments are approximate, multi-label, and sensitive to the editable regex dictionary.
- The 2026 bar reflects a partial year because the pipeline was run during 2026 rather than after year-end indexing closed.
