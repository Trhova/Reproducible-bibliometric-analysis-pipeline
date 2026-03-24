# Immune-Microbiome-Barrier AhR Sublandscape

## Figure purpose
Highlights the thesis-relevant AhR sublandscape spanning microbiome, barrier biology, inflammation, and immune regulation.

## Changes from previous version
- This figure replaces the earlier weak subnetwork graph with a focused concept map built from a targeted AhR immune-microbiome-barrier subset.
- The updated version removes low-value verbs and uses curated concept labels, explicit legend text, and stronger cluster structure so the figure reads as a coherent subfield map.

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
- Concept labels were built from normalized OpenAlex keywords, MeSH descriptors, and targeted title/abstract marker matching rather than raw free-text tokens.
- Only papers carrying immune, microbiome, barrier, inflammation, gut, or intestinal focus tags were used.
- Concept co-occurrence was computed at the paper level and weighted by association strength using co-occurrence divided by the geometric mean of individual concept frequencies.
- Louvain community detection defined thematic clusters, and a cluster-aware force layout positioned nodes to emphasize the separation of conceptual regions.

## Thresholds and filters
- Generic or non-informative index terms, demographic labels, and method-heavy concepts were excluded before map construction.
- Concept labels had to appear in at least 45 papers within the focus subset, and the map was capped at the 36 most prevalent retained concepts.
- Edges were retained only when at least 12 papers carried the concept pair and the association-strength weight was at least 0.11.

## Plotting settings
- Node size encodes document frequency.
- Node color encodes cluster assignment.
- Edge width encodes retained co-occurrence strength.
- Translucent cluster envelopes and a dedicated side legend panel were added to make the map legible without referring back to the methods.

## Interpretation notes
- This figure should be read as a conceptual landscape of the AhR field rather than as a comprehensive display of every detectable term.
- Clusters summarize high-salience thematic neighborhoods and the bridging edges between them.

## Caveats
- The corpus favors precision over total recall because ambiguous plain-acronym records were not retrieved exhaustively.
- OpenAlex abstract coverage is incomplete, so concept-map coverage partly depends on keyword and MeSH richness rather than abstract availability alone.
- Dictionary-tagged disease/application assignments are approximate, multi-label, and sensitive to the editable regex dictionary.
