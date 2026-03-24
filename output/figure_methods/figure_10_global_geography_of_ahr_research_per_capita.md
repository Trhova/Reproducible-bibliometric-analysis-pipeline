# Global AhR Research Output Per Capita

## Figure purpose
Shows where AhR research is relatively concentrated after normalizing fractional country output by population size.

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
- Country attribution used the OpenAlex `authorships.countries` metadata already captured in the processed `countries` field.
- Each paper was fractionally counted across all unique countries represented on the paper, so a paper with authors from four countries contributed 0.25 to each country.
- The map normalizes fractional AhR paper counts by country population using the Natural Earth `POP_EST` value and expresses the result as fractional AhR papers per million inhabitants.
- Country names and map positions were normalized by joining ISO alpha-2 country codes to the cached Natural Earth 1:110m country boundary file.

## Thresholds and filters
- Countries with missing or non-positive Natural Earth population estimates were omitted from the per-capita normalization map.
- Only the top 8 countries by per-capita output among countries with at least 25 fractional papers were labeled directly on the map to avoid crowding.

## Plotting settings
- The figure uses a light gray world basemap with minimal borders and semi-transparent single-color bubbles.
- Bubble area, not color, carries the quantitative encoding.
- A bubble-size legend was added directly on the map to make the scale explicit.
- The figure was exported as PNG, PDF, and SVG at 400 dpi for thesis use.

## Interpretation notes
- This map emphasizes relative research intensity after population normalization.
- Large bubbles can elevate smaller countries with disproportionately strong AhR activity compared with raw output alone.

## Caveats
- The corpus favors precision over total recall because ambiguous plain-acronym records were not retrieved exhaustively.
- OpenAlex abstract coverage is incomplete, so concept-map coverage partly depends on keyword and MeSH richness rather than abstract availability alone.
- Dictionary-tagged disease/application assignments are approximate, multi-label, and sensitive to the editable regex dictionary.
- Geographic attribution depends on country metadata being present in OpenAlex authorships; papers lacking country metadata are excluded from the geography figure.
- Fractional counting reduces collaboration-driven overcounting, but it does not distinguish first-author, corresponding-author, or senior-author leadership.
- Per-capita normalization uses Natural Earth population estimates and can be unstable for very small countries, which is why direct labeling is restricted to countries with at least 25 fractional papers.
