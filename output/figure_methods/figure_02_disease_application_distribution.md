# Figure 02. Disease and application distribution across the AhR corpus

## Figure purpose
Summarizes which disease and translational application areas appear most often in the AhR literature.

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
- Dictionary-based category tags were applied to each paper using normalized titles, available abstracts, keywords, MeSH descriptors, and topic labels.
- Papers could receive multiple categories if multiple pattern groups matched.
- Counts were summarized as unique papers per category across the full corpus.

## Thresholds and filters
- Only the ten largest categories are plotted.
- Categories are multi-label and therefore counts can sum to more than the total number of papers.

## Plotting settings
- A horizontal ranking format was used to maximize label readability in thesis layout.
- Counts and corpus-share annotations are printed directly on the figure to reduce legend dependence.

## Interpretation notes
- This figure helps position cancer, barrier, microbiome, toxicology, and immune themes relative to one another.
- It is useful for arguing whether thesis-relevant application areas are niche or mainstream branches within the wider AhR field.

## Caveats
- The corpus favors precision over total recall because ambiguous plain-AHR abstracts were not retrieved exhaustively.
- OpenAlex abstract coverage is incomplete, so title-only records remain in the corpus when they pass conservative validation.
- Dictionary-tagged disease/application assignments are approximate, multi-label, and sensitive to the editable regex dictionary.
