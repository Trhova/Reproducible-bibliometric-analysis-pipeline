# Figure 05. Immune-barrier-microbiome AhR term network

## Figure purpose
Focuses the co-occurrence map on the thesis-relevant immune, barrier, gut, and microbiome-oriented subset of AhR papers.

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
- A binary term-document matrix was built from normalized title-plus-abstract text after broader metadata trials produced noisier concept maps.
- Pairwise term co-occurrence counts were computed across papers in the relevant corpus subset.
- Edges were weighted by an association-strength style normalization using co-occurrence divided by the geometric mean of individual term frequencies.
- Louvain community detection was used to assign clusters, and a weighted spring layout positioned the network.

## Thresholds and filters
- Subset defined by immune, inflammation, microbiome, barrier, gut, or intestinal focus tags.
- Lower minimum term and edge thresholds were used than in the all-corpus network to preserve structure within the smaller subset.

## Plotting settings
- Edges are rendered as faint weighted strokes to avoid a hairball effect.
- Node size scales with document frequency and color indicates Louvain cluster membership.
- Only the highest-salience labels are shown directly to preserve readability.

## Interpretation notes
- This view is intended to surface bridges between mucosal biology, host-microbe interactions, inflammation, and immune regulation.
- Because the subset is pattern-based, some relevant papers may be missed if they use unexpected terminology.

## Caveats
- The corpus favors precision over total recall because ambiguous plain-AHR abstracts were not retrieved exhaustively.
- OpenAlex abstract coverage is incomplete, so title-only records remain in the corpus when they pass conservative validation.
- Dictionary-tagged disease/application assignments are approximate, multi-label, and sensitive to the editable regex dictionary.
