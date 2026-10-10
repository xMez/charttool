"""Shared offline boundaries for tests exercising the CLI and downloads."""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class OfflineTestCase(unittest.TestCase):
    """Keep files in a temporary directory and reject unmocked external effects."""

    def setUp(self):
        super().setUp()
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        previous = Path.cwd()
        os.chdir(self.root)
        self.addCleanup(os.chdir, previous)
        for target in (
            "requests.sessions.Session.request",
            "yt_dlp.YoutubeDL",
            "subprocess.run",
        ):
            boundary = patch(
                target, side_effect=AssertionError(f"Unmocked effect: {target}")
            )
            boundary.start()
            self.addCleanup(boundary.stop)
        if hasattr(os, "startfile"):
            boundary = patch(
                "os.startfile", side_effect=AssertionError("Unmocked GUI launch")
            )
            boundary.start()
            self.addCleanup(boundary.stop)
