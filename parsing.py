"""Parsing functions for different title formats."""

import re


def clean_title(title: str) -> str:
    """Clean up song title by removing common delimiters and trailing content."""
    # Common delimiters that often precede unnecessary information
    delimiters = r" \|| -| ~| \[| \(| 【| 「"

    cleaned_title = title.strip()
    # Find the earliest occurrence of any delimiter
    positions = [m.start() for m in re.finditer(delimiters, cleaned_title)]
    if positions:
        earliest_pos = min(positions)
        cleaned_title = cleaned_title[:earliest_pos].strip()

    return cleaned_title


def parse_title(title: str) -> list[dict]:
    """Parse different possible title formats and return all possible combinations."""
    results = []

    # Clean the title first
    cleaned_title = clean_title(title)

    # Case 1: "Artist - Title" format (prioritize these)
    # Support different types of dashes (hyphen, en dash, em dash)
    dash_types = [" - ", " – ", " — "]  # noqa: RUF001
    for dash in dash_types:
        if dash in title:
            artist, song_title = title.split(dash, 1)
            # Clean the song title part
            song_title = clean_title(song_title)
            results.append({"title": song_title.strip(), "artist": artist.strip()})
            # Also add reversed in case it's "Title - Artist"
            results.append({"title": artist.strip(), "artist": song_title.strip()})
            break

    # Case 2: Direct from video title (moved to end)
    results.append({"title": cleaned_title, "artist": ""})

    return results
