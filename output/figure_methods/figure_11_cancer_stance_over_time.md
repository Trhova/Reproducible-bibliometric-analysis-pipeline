# Figure 11. Local-LLM framing of AhR in cancer-focused literature over time

## Figure purpose
Summarizes how a local open-source LLM classifies cancer-focused AhR papers as pro-tumor, anti-tumor, mixed/context-dependent, or unclear, and how that framing shifts over time.

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
- Cancer-focused papers with sufficient title/abstract text were sent to a local Ollama model (`qwen2.5:3b`) with a fixed four-class JSON prompt.
- The LLM was asked to classify how each paper framed AhR in cancer as pro-tumor, anti-tumor, mixed/context-dependent, or unclear.
- Model outputs were cached to disk so the long-running inference step could be resumed without rescoring completed papers.
- Counts were aggregated in fixed five-year bins and converted to within-bin shares for plotting.
- Rule-based labels were retained only as an audit/comparison table and were not used to draw the plotted lines.

## Thresholds and filters
- The cancer-focused subset contained 2,993 papers, of which 2,993 were scored by the local LLM.
- Abstracts were available for 2,162 papers (72%); title fallback was used only when the abstract text was missing or too short.
- Agreement between the rule-based and LLM labels excluding rule-`Unclear` papers was 22.3%.

## Plotting settings
- Colored lines show the within-bin share of LLM-assigned stance classes across the cancer-focused subset.
- A lower bar panel shows the number of LLM-scored cancer-focused papers in each bin so denominator changes remain visible.
- Anti-tumor and pro-tumor classes use contrasting teal and brick colors, while mixed/context-dependent and unclear are de-emphasized with ochre and gray.

## Interpretation notes
- This figure should be read as an LLM-assisted literature-framing analysis of abstracts and titles, not a direct vote on the true biological role of AhR in cancer.
- A high mixed/context-dependent share indicates that the model frequently interprets the cancer literature as emphasizing conditional or dual roles rather than a single directional effect.

## Caveats
- The corpus favors precision over total recall because ambiguous plain-acronym records were not retrieved exhaustively.
- OpenAlex abstract coverage is incomplete, so concept-map coverage partly depends on keyword and MeSH richness rather than abstract availability alone.
- Dictionary-tagged disease/application assignments are approximate, multi-label, and sensitive to the editable regex dictionary.
- The LLM labels are not a gold standard and should be treated as machine-assisted interpretations that require manual spot-checking in the exported review table.
- The relatively low rule-versus-LLM agreement indicates that the model often reads the same papers more cautiously or more context-dependently than the rule-based system.
- Abstract coverage is incomplete, so some cancer-focused papers were classified using title fallback rather than full abstract text.
