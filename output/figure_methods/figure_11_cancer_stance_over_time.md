# Figure 11. How AhR is framed in cancer-focused literature over time

## Figure purpose
Summarizes whether cancer-focused AhR papers frame the receptor as pro-tumor, anti-tumor, mixed/context-dependent, or unclear, and how that framing shifts over time.

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
- The validated corpus was filtered to papers carrying either the `Cancer` disease tag or the `cancer` focus tag.
- Rule-based stance assignment used normalized abstracts as the primary evidence source, with title fallback only when the abstract did not provide a directional signal.
- Explicit marker sets captured pro-tumor language, anti-tumor language, and mixed/context-dependent framing.
- Papers with no interpretable directional language were left as `Unclear` rather than forcing a polarity label.
- For a secondary sensitivity check, an open-source sentence-transformer compared abstract/title text against prototype stance descriptions and the agreement rate was summarized against the rule-based labels.
- Counts were aggregated in fixed five-year bins and converted to within-bin shares for plotting.

## Thresholds and filters
- The cancer-focused subset contained 2,993 papers, of which 2,162 (72%) had abstracts.
- The primary figure uses the rule-based labels only; the model-assisted layer is exploratory and is included as a sensitivity check rather than the thesis-default claim.
- Papers with model text shorter than the configured threshold were not scored by the embedding model.

## Plotting settings
- Colored lines show the within-bin share of cancer-focused papers assigned to each stance class.
- A lower bar panel shows the number of cancer-focused papers in each bin so denominator changes remain visible.
- Anti-tumor and pro-tumor classes use contrasting teal and brick colors, while mixed/context-dependent and unclear are de-emphasized with ochre and gray.

## Interpretation notes
- This figure should be read as a literature-framing analysis of abstracts and titles, not a direct vote on the true biological role of AhR in cancer.
- Rising `mixed / context-dependent` share would indicate that the literature increasingly emphasizes tumor-type, ligand, or immune-context specificity rather than a single universal role.

## Caveats
- The corpus favors precision over total recall because ambiguous plain-acronym records were not retrieved exhaustively.
- OpenAlex abstract coverage is incomplete, so concept-map coverage partly depends on keyword and MeSH richness rather than abstract availability alone.
- Dictionary-tagged disease/application assignments are approximate, multi-label, and sensitive to the editable regex dictionary.
- Stance labels are based on explicit language in titles and abstracts, so papers that imply a directional role without stating it clearly can remain `Unclear`.
- The model-assisted comparison is not a manually validated gold standard; it is a semantic sensitivity analysis intended to show whether a local open-source model broadly agrees with the rule-based calls.
- Abstract coverage is incomplete, so some cancer-focused papers can only be classified from titles or not scored by the model layer at all.
