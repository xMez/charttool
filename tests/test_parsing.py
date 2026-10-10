"""Regression checks for title selection and filename handling."""

import unittest

from charttool.cli import sanitize_filename
from charttool.parsing import clean_title, parse_title


class ParsingTests(unittest.TestCase):
    def test_cleanup_uses_first_delimiter(self):
        for suffix in (
            " | official",
            " - official",
            " ~ official",
            " [live]",
            " (live)",
            " 【live】",
            " 「live」",
        ):
            with self.subTest(suffix=suffix):
                self.assertEqual(clean_title(f"  Song{suffix}  "), "Song")

    def test_artist_title_options_and_fallback(self):
        for dash in (" - ", " – ", " — "):
            with self.subTest(dash=dash):
                options = parse_title(f"Artist{dash}Song (Official Video)")
                self.assertEqual(
                    options[:2],
                    [
                        {"title": "Song", "artist": "Artist"},
                        {"title": "Artist", "artist": "Song"},
                    ],
                )
                self.assertEqual(options[-1]["artist"], "")

    def test_plain_and_empty_titles(self):
        self.assertEqual(parse_title("  Song  "), [{"title": "Song", "artist": ""}])
        self.assertEqual(parse_title(""), [{"title": "", "artist": ""}])

    def test_filename_transliteration_and_reserved_characters(self):
        self.assertEqual(
            sanitize_filename('Björk: "Jóga" / live\\<>|?*'), "Bjork Joga  live"
        )
