# Figure 03. Disease and application trends across AhR field eras

## Figure purpose
Shows how major AhR application areas changed in prominence from early to recent literature.

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
- The corpus was sliced into 1970-1999, 2000-2012, and 2013-2026 using the editable config file.
- Multi-label dictionary tags were counted within each period.
- Counts were normalized by the number of papers in each period to plot within-period share rather than raw volume alone.

## Thresholds and filters
- Only the ten categories with the largest total tagged volume are shown.
- Percentages are period-normalized to support comparison despite uneven corpus size across eras.

## Plotting settings
- A heatmap was chosen over stacked bars to keep the cross-period comparison readable with many categories.
- Cell annotations are shown directly on the map for methods-ready interpretation.

## Interpretation notes
- This figure is suited to discussing whether toxicology-led AhR work has broadened toward immune, barrier, microbiome, and cancer contexts over time.
- Because categories are multi-label, increases can reflect expansion in overlap between domains rather than replacement of one area by another.

## Caveats
- The corpus favors precision over total recall because ambiguous plain-AHR abstracts were not retrieved exhaustively.
- OpenAlex abstract coverage is incomplete, so title-only records remain in the corpus when they pass conservative validation.
- Dictionary-tagged disease/application assignments are approximate, multi-label, and sensitive to the editable regex dictionary.
