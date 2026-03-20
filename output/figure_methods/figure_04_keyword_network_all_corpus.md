# Figure 04. Term co-occurrence network across the AhR corpus

## Figure purpose
Maps the main co-occurring concept structure across the full validated AhR literature.

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
- Only terms passing minimum document-frequency thresholds were eligible.
- Only edges above count and association-strength thresholds were retained.
- The graph was truncated to the strongest retained edges among the highest-frequency terms to keep the network readable.

## Plotting settings
- Edges are rendered as faint weighted strokes to avoid a hairball effect.
- Node size scales with document frequency and color indicates Louvain cluster membership.
- Only the highest-salience labels are shown directly to preserve readability.

## Interpretation notes
- Clusters often represent broad AhR branches such as toxicology, immunology, microbiome/barrier biology, and cancer-related work.
- Absence of an edge should not be interpreted as absence of a biological relationship; it only means the term pair did not survive readability-oriented thresholds.

## Caveats
- The corpus favors precision over total recall because ambiguous plain-AHR abstracts were not retrieved exhaustively.
- OpenAlex abstract coverage is incomplete, so title-only records remain in the corpus when they pass conservative validation.
- Dictionary-tagged disease/application assignments are approximate, multi-label, and sensitive to the editable regex dictionary.
