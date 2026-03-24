# Disease and Application Evolution of AhR Research

## Figure purpose
Shows how the most prevalent disease and application categories in the AhR corpus changed across early, middle, and recent eras using the same dictionary framework as Figure 03.

## Changes from previous version
- This is an added companion to Figure 03, using an alluvial-style display instead of a heatmap.
- The figure reuses the disease/application dictionary framework so the temporal shifts are visually easier to compare as flowing category shares across eras.

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
- The same dictionary-based disease/application tags used for Figure 03 were counted within each configured time slice.
- Papers could contribute to multiple categories because disease/application tagging is multi-label.
- Within each period, category counts were first normalized by the number of validated papers in that period, as in Figure 03.
- Because the retained categories are multi-label and can overlap, the selected categories were then renormalized within each era so the alluvial widths sum to a readable composition across the displayed categories.
- The eight largest categories by total tagged volume were retained for the alluvial view.

## Thresholds and filters
- Only the eight categories with the largest total tagged volume are shown to keep the alluvial readable.
- The underlying category counts are period-normalized, but the displayed ribbon widths are renormalized across the retained categories within each era because multi-label categories do not form a strict partition.
- The order was fixed from the recent era so ribbon-width changes are easier to compare.

## Plotting settings
- Ribbon color encodes disease/application category identity.
- Ribbon width encodes the relative share of the displayed categories within a given period rather than the raw multi-label share from Figure 03.
- A side legend lists the retained categories and their recent-era shares.
- The figure was exported as PNG, PDF, and SVG at 400 dpi.

## Interpretation notes
- This figure is a dictionary-based application-landscape companion to the unsupervised thematic evolution map in Figure 06.
- It makes the relative rise of immune/inflammation, microbiome/barrier, and other translational categories easier to compare directly against classic toxicology-heavy eras.

## Caveats
- The corpus favors precision over total recall because ambiguous plain-acronym records were not retrieved exhaustively.
- OpenAlex abstract coverage is incomplete, so concept-map coverage partly depends on keyword and MeSH richness rather than abstract availability alone.
- Dictionary-tagged disease/application assignments are approximate, multi-label, and sensitive to the editable regex dictionary.
- Because disease/application tags are multi-label, the raw shares from Figure 03 overlap and do not sum to 100% within a period.
- This alluvial therefore shows the relative composition of the retained displayed categories, not the raw within-period paper share values printed in Figure 03.
- This figure captures application framing rather than latent mechanistic document structure.
