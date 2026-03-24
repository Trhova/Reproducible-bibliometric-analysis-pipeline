# Document Landscape of AhR Research Themes

## Figure purpose
Provides a document-level thematic landscape complementary to the term co-occurrence concept map.

## Changes from previous version
- This figure replaces the earlier bubble-only cluster summary with a true document landscape.
- The redesign is intentionally complementary to Figure 04: Figure 04 maps concept co-occurrence, whereas Figure 07 maps papers in concept-profile space.

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
- Each paper was represented by a TF-IDF concept profile derived from normalized keyword, MeSH, and targeted title/abstract concept labels.
- The document concept matrix retained terms with min_df=20, max_df=0.25, and max_features=700; 12 latent components were used for clustering and a separate 2D TruncatedSVD projection was used for plotting.
- MiniBatchKMeans partitioned papers into seven thematic clusters.
- A 2D TruncatedSVD embedding was used for visualization, and cluster centroids plus envelopes summarize the dominant regions of concept space.

## Thresholds and filters
- Seven clusters were retained as a pragmatic thesis-scale compromise between detail and readability.
- Concept terms entered the document space only if they appeared in at least 20 papers and in no more than 25% of the corpus.

## Plotting settings
- Each point represents one paper.
- Point color and the translucent cluster envelope encode thematic cluster membership.
- Cluster labels show the cluster theme plus leading representative concepts.

## Interpretation notes
- Papers that occupy the same island share similar AhR-associated concept profiles.
- This figure is a field-structure view rather than a citation or chronology map, so distances should be read qualitatively.

## Caveats
- The corpus favors precision over total recall because ambiguous plain-acronym records were not retrieved exhaustively.
- OpenAlex abstract coverage is incomplete, so concept-map coverage partly depends on keyword and MeSH richness rather than abstract availability alone.
- Dictionary-tagged disease/application assignments are approximate, multi-label, and sensitive to the editable regex dictionary.
