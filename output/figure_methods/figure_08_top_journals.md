# Figure 08. Journals most frequently publishing AhR papers

## Figure purpose
Offers a lightweight publishing-landscape view without letting citation metrics dominate the analysis.

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
- Primary source titles were counted across the validated corpus.
- The fifteen most frequent journals were retained for visualization.

## Thresholds and filters
- Only the top fifteen sources by paper count are shown.

## Plotting settings
- A lollipop-style layout was used to keep long journal names legible in thesis format.

## Interpretation notes
- This figure is a contextual companion, useful for understanding where AhR work tends to concentrate institutionally.
- It is descriptive only and should not be read as a quality ranking of journals.

## Caveats
- The corpus favors precision over total recall because ambiguous plain-AHR abstracts were not retrieved exhaustively.
- OpenAlex abstract coverage is incomplete, so title-only records remain in the corpus when they pass conservative validation.
- Dictionary-tagged disease/application assignments are approximate, multi-label, and sensitive to the editable regex dictionary.
