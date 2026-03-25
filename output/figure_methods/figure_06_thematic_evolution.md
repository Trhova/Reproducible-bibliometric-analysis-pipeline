# Thematic Evolution of AhR Research

## Figure purpose
Shows how the major thematic clusters of the AhR field changed across early, middle, and recent eras.

## Changes from previous version
- This figure replaces the earlier heatmap-style evolution view with an alluvial-style cluster-flow map.
- The redesign makes the rise of microbiome, barrier, immune, and cancer-linked AhR themes easier to compare against older toxicology-centered themes.
- Three closely related CYP1-centered unsupervised clusters were collapsed into one displayed super-theme to remove redundant toxicology labels and improve interpretability.

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
- Papers were clustered on TF-IDF concept profiles derived from normalized keyword, MeSH, and targeted title/abstract marker labels.
- The concept-profile matrix retained terms with min_df=20, max_df=0.25, and max_features=700 before TruncatedSVD reduction and MiniBatchKMeans clustering.
- Cluster assignments were counted within each of the three configured time slices.
- For visualization, three related CYP1-oriented clusters were merged into one displayed super-theme after clustering because they represented adjacent toxicology/transcriptional neighborhoods with redundant labels.
- Displayed theme counts were normalized by the number of papers in each period so ribbon widths represent within-period share rather than raw volume only.

## Thresholds and filters
- The underlying unsupervised document clustering retained seven clusters.
- The displayed alluvial summary collapses those seven clusters into five readable super-themes by merging the three CYP1-centered clusters.
- The alluvial order was fixed from the recent era so changes in ribbon width reflect thematic growth or contraction rather than re-sorting artifacts.

## Plotting settings
- Ribbon color encodes displayed thematic identity using a categorical palette chosen to maximize separation between themes.
- Ribbon width encodes the share of papers assigned to that displayed theme within a given period.
- Period headers include the number of papers in each era to make denominator changes explicit.
- A side legend lists displayed theme labels and their share in the most recent era.

## Interpretation notes
- Expanding ribbons in the recent era indicate displayed themes that gained relative prominence, such as microbiome, barrier, immune, and tryptophan-linked work.
- Narrowing ribbons point to displayed themes that became relatively less dominant as the field diversified.

## Caveats
- The corpus favors precision over total recall because ambiguous plain-acronym records were not retrieved exhaustively.
- OpenAlex abstract coverage is incomplete, so concept-map coverage partly depends on keyword and MeSH richness rather than abstract availability alone.
- Dictionary-tagged disease/application assignments are approximate, multi-label, and sensitive to the editable regex dictionary.
- Displayed theme labels are heuristic summaries assigned after unsupervised document clustering and should be interpreted as approximate thematic handles rather than fixed ontology classes.
- The alluvial diagram tracks relative share within each era, so a ribbon can narrow even if the absolute number of papers in that theme still rose.
- The CYP1 merge is a presentation-layer simplification intended to reduce redundant labels, not a rerun of the underlying clustering model.
