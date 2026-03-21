# Global Geography of AhR Research

## Figure purpose
Shows where AhR research is produced globally and which broad AhR themes are relatively emphasized in leading countries.

## Input data
- Corpus: Validated AhR OpenAlex corpus
- Number of papers: 8291
- Time window: 1980 to 2026
- Query strategy: OpenAlex exact-match title/abstract retrieval for "aryl hydrocarbon receptor", "ah receptor", and "dioxin receptor", plus title-level "AHR" hits; local regex validation retained records with explicit AhR naming in the title or abstract-phrase hits supported by biologically relevant title language.

## Preprocessing
- English-language articles and reviews were retained.
- Titles, available abstracts, OpenAlex keywords, and MeSH descriptors were normalized after corpus retrieval.
- Disease/application tagging still uses broad metadata support, but the upgraded landscape figures use curated concept labels derived from normalized OpenAlex keywords, MeSH descriptors, and targeted title/abstract marker matching.
- Text was lowercased, punctuation-normalized, and harmonized with editable synonym mappings in configs/synonyms.yaml.
- Generic bibliometric and non-informative scientific terms from configs/stopwords_terms.txt plus figure-specific concept exclusions were removed from map-style analyses.

## Analysis steps
- Country attribution used the OpenAlex `authorships.countries` metadata already captured in the processed `countries` field.
- Each paper was fractionally counted across all unique countries represented on the paper, so a paper with authors from four countries contributed 0.25 to each country.
- Broad geography themes were derived from the existing `focus_tags` and `disease_tags` framework and grouped into Toxicology / xenobiotics, Cancer, Immune / inflammation, Microbiome / barrier, and Liver / metabolism to keep the geography layer aligned with the existing thesis figures while avoiding a fragmented legend.
- Country-level theme shares were computed as the fractional count of papers carrying a theme divided by the country's total fractional AhR paper count.
- Country names were normalized by joining the ISO alpha-2 codes in the corpus to Natural Earth country names, with small display-name overrides for common thesis labels such as United States, United Kingdom, South Korea, Taiwan, and Czech Republic.
- World boundaries were drawn from the cached Natural Earth 1:110m country GeoJSON joined by ISO alpha-2 country code.

## Thresholds and filters
- All countries with valid metadata were included in the choropleth panel.
- The heatmap panel was limited to the twelve countries with the largest fractional AhR output among countries with at least 40 fractional papers.
- Only the eight largest producing countries were labeled directly on the map to avoid crowding.
- Theme shares are non-exclusive because one paper can contribute to more than one broad theme category.

## Plotting settings
- Panel A uses a muted sequential choropleth where country color encodes fractional AhR paper count.
- Panel B uses a side heatmap where color intensity encodes the within-country share of papers assigned to each broad theme.
- Top-producing countries were selectively labeled on the map, with manual offsets for crowded regions.
- The figure was exported as PNG, PDF, and SVG at 400 dpi for thesis use.

## Interpretation notes
- The choropleth shows that AhR research output is globally distributed but strongly concentrated in a limited set of countries.
- The heatmap is intended to show relative thematic emphasis within countries rather than exclusive specialization or absolute volume.

## Caveats
- The corpus favors precision over total recall because ambiguous plain-AHR abstracts were not retrieved exhaustively.
- OpenAlex abstract coverage is incomplete, so concept-map coverage partly depends on keyword and MeSH richness rather than abstract availability alone.
- Dictionary-tagged disease/application assignments are approximate, multi-label, and sensitive to the editable regex dictionary.
- Geographic attribution depends on country metadata being present in OpenAlex authorships; papers lacking country metadata are excluded from the geography figure.
- Fractional counting reduces collaboration-driven overcounting, but it does not distinguish first-author, corresponding-author, or senior-author leadership.
- Country theme shares should not be read as mutually exclusive compositions because the underlying disease and focus tags are multi-label.
