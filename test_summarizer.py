import unittest

from summarizer import ArticleSummarizer


class HouseStyleTests(unittest.TestCase):
    def setUp(self):
        self.summarizer = ArticleSummarizer.__new__(ArticleSummarizer)

    def test_abbreviates_currency_millions_and_billions(self):
        summary = "Revenue rose from £13 million to $2.5 billions and € 4 billion."

        self.assertEqual(
            self.summarizer._apply_house_style(summary),
            "Revenue rose from £13m to $2.5bn and € 4bn.",
        )

    def test_does_not_abbreviate_non_currency_amounts(self):
        summary = "The service has 13 million users and processed two billion requests."

        self.assertEqual(self.summarizer._apply_house_style(summary), summary)

    def test_replaces_percentage_wording(self):
        summary = "Percent growth hit 13 per cent, then fell 2.5 percent."

        self.assertEqual(
            self.summarizer._apply_house_style(summary),
            "% growth hit 13%, then fell 2.5%.",
        )


if __name__ == "__main__":
    unittest.main()
