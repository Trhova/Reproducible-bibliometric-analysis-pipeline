# Figure 07. Thematic cluster map of the AhR literature

## Figure purpose
Provides a reduced thematic overview of the AhR field by clustering papers on their normalized term profiles.

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
- TF-IDF vectors were built from normalized document text.
- MiniBatchKMeans partitioned papers into seven thematic clusters.
- Cluster centroids were projected into two dimensions using MDS on cosine distance between centroids.
- Each bubble is labeled by the top weighted centroid terms and sized by the number of papers in the cluster.

## Thresholds and filters
- Seven clusters were used as a pragmatic overview scale rather than a claim of the field's true discrete structure.
- TF-IDF features were frequency-filtered to suppress sparse one-off phrases.

## Plotting settings
- Bubble size encodes cluster size, while label text encodes centroid-defining terms.
- The map emphasizes interpretable thematic neighborhoods instead of precise geometric meaning.

## Interpretation notes
- This figure helps identify major AhR subfields and the relative size of each thematic branch.
- Distances are projection-based and should be read qualitatively rather than as exact semantic metrics.

## Caveats
- The corpus favors precision over total recall because ambiguous plain-AHR abstracts were not retrieved exhaustively.
- OpenAlex abstract coverage is incomplete, so title-only records remain in the corpus when they pass conservative validation.
- Dictionary-tagged disease/application assignments are approximate, multi-label, and sensitive to the editable regex dictionary.
