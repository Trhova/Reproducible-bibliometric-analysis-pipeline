from __future__ import annotations

import unittest

from ahr_bibliometrics.optional_analyses import classify_stance_text, extract_phrase_hits


class OptionalAnalysesTests(unittest.TestCase):
    def test_classify_pro_tumor_language(self) -> None:
        result = classify_stance_text(
            title_text="",
            abstract_text="AHR promotes tumor growth and metastasis in colorectal cancer cells.",
        )
        self.assertEqual(result["rule_label"], "pro_tumor")

    def test_classify_anti_tumor_language(self) -> None:
        result = classify_stance_text(
            title_text="",
            abstract_text="AHR suppresses tumor growth and enhances anti tumor immunity in melanoma.",
        )
        self.assertEqual(result["rule_label"], "anti_tumor")

    def test_classify_mixed_context_language(self) -> None:
        result = classify_stance_text(
            title_text="",
            abstract_text="AHR has a context dependent dual role in cancer and can be either pro tumor or anti tumor.",
        )
        self.assertEqual(result["rule_label"], "mixed_context")

    def test_title_fallback_when_abstract_unclear(self) -> None:
        result = classify_stance_text(
            title_text="AHR suppresses tumor growth in breast cancer",
            abstract_text="We discuss AHR in cancer.",
        )
        self.assertEqual(result["rule_label"], "anti_tumor")
        self.assertEqual(result["rule_source"], "title_fallback")

    def test_extract_phrase_hits_returns_curated_phrases(self) -> None:
        phrase_patterns = {
            "microbiome": [r"\bmicrobiome\b", r"\bmicrobiota\b"],
            "CYP1A1": [r"\bcyp1a1\b"],
            "tumor immunity": [r"\btumou?r immunity\b"],
        }
        hits = extract_phrase_hits(
            "the microbiota regulates cyp1a1 and tumor immunity in ahr biology",
            phrase_patterns,
        )
        self.assertEqual(hits, ["CYP1A1", "microbiome", "tumor immunity"])


if __name__ == "__main__":
    unittest.main()
