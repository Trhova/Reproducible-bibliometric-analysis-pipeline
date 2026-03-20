# Figure 06. Thematic evolution of AhR-associated language

## Figure purpose
Highlights terms whose prevalence rose or fell most strongly across early, middle, and recent AhR eras.

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
- A document-term matrix was built with conservative frequency thresholds to focus on reusable field-level vocabulary.
- Within each time slice, term prevalence was defined as the share of papers containing the term at least once.
- The largest positive and negative recent-versus-early changes were selected for plotting.

## Thresholds and filters
- Terms had to pass corpus-level document-frequency thresholds embedded in the analysis module.
- Only 16 high-change terms were plotted to keep the slope chart readable.

## Plotting settings
- Rising terms are colored in brick and declining terms in slate.
- A slope-style layout was chosen to foreground directional change rather than absolute frequency alone.

## Interpretation notes
- This figure is useful for narrating the shift from older toxicology-led terminology toward more recent immune, barrier, microbiome, and cancer language.
- Changes reflect metadata language prevalence, not mechanistic causality or the scientific importance of a term.

## Caveats
- The corpus favors precision over total recall because ambiguous plain-AHR abstracts were not retrieved exhaustively.
- OpenAlex abstract coverage is incomplete, so title-only records remain in the corpus when they pass conservative validation.
- Dictionary-tagged disease/application assignments are approximate, multi-label, and sensitive to the editable regex dictionary.
