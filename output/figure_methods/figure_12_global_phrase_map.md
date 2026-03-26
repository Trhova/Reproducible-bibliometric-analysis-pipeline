# Paired-Topic Phrase Map of AhR Research

## Figure purpose
Maps the phrase-level topics most commonly paired with AhR across the full validated corpus using title-and-abstract phrase markers rather than metadata concepts.

## Changes from previous version
- This is a new optional figure designed to answer what topics are most commonly paired with AhR in the literature.
- Unlike Figures 04 and 05, the phrase map is driven by recurring title-and-abstract phrases rather than the broader keyword/MeSH concept layer.

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
- Phrase labels were built from configured title-and-abstract marker patterns designed to capture recurring AhR-paired topics in human-readable phrase form.
- The full validated AhR corpus was used, but only title-and-abstract phrase hits were allowed to enter the map.
- Concept co-occurrence was computed at the paper level and weighted by association strength using co-occurrence divided by the geometric mean of individual concept frequencies.
- Louvain community detection defined thematic clusters, and a cluster-aware force layout positioned nodes to emphasize the separation of conceptual regions.

## Thresholds and filters
- Generic or non-informative index terms, demographic labels, and method-heavy concepts were excluded before map construction.
- Only configured phrase markers observed in at least the configured minimum number of papers were eligible for display.
- Edges were retained only when phrase pairs passed the configured minimum co-occurrence count and association-strength threshold.

## Plotting settings
- Node size encodes document frequency.
- Node color encodes cluster assignment.
- Edge width encodes retained co-occurrence strength.
- Translucent cluster envelopes and a dedicated side legend panel were added to make the map legible without referring back to the methods.

## Interpretation notes
- This figure should be read as a literature-derived map of the topics most often paired with AhR, not as a map of real search-engine behavior.
- Clusters summarize high-salience thematic neighborhoods and the bridging edges between them.

## Caveats
- The corpus favors precision over total recall because ambiguous plain-acronym records were not retrieved exhaustively.
- OpenAlex abstract coverage is incomplete, so concept-map coverage partly depends on keyword and MeSH richness rather than abstract availability alone.
- Dictionary-tagged disease/application assignments are approximate, multi-label, and sensitive to the editable regex dictionary.
