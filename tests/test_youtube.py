"""Mock media integrations while verifying conversion and fallback behavior."""

import subprocess
from unittest.mock import Mock, patch

import requests

from charttool.youtube import download_audio, download_bg, get_title
from support import OfflineTestCase


class YoutubeTests(OfflineTestCase):
    def test_metadata_adds_channel_before_plain_fallback(self):
        with patch("charttool.youtube.yt_dlp.YoutubeDL") as downloader:
            downloader.return_value.__enter__.return_value.extract_info.return_value = {
                "title": "Artist - Song",
                "uploader": "Channel",
            }
            options = get_title("https://youtu.be/test")
        self.assertEqual(options[-2], {"title": "Artist - Song", "artist": "Channel"})
        self.assertEqual(options[-1], {"title": "Artist", "artist": ""})

    def test_existing_media_skips_external_calls(self):
        for filename, download in (
            ("Song.ogg", download_audio),
            ("bg.jpg", download_bg),
        ):
            path = self.root / filename
            path.write_bytes(b"existing")
            self.assertTrue(download("unused", path))
            self.assertEqual(path.read_bytes(), b"existing")

    def test_audio_conversion_normalizes_and_removes_original(self):
        source = self.root / "Song.webm"
        source.write_bytes(b"source")
        destination = self.root / "Song.ogg"
        with (
            patch("charttool.youtube.yt_dlp.YoutubeDL") as downloader,
            patch("charttool.youtube.subprocess.run") as convert,
        ):
            downloader.return_value.__enter__.return_value.prepare_filename.return_value = str(
                source
            )
            self.assertTrue(download_audio("https://youtu.be/test", destination))
        convert.assert_called_once_with(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(source),
                "-af",
                "loudnorm=I=-8:TP=-1.5:LRA=7",
                "-c:a",
                "libvorbis",
                "-q:a",
                "7",
                str(destination),
            ],
            check=True,
        )
        self.assertFalse(source.exists())

    def test_failed_conversion_preserves_original(self):
        source = self.root / "Song.webm"
        source.write_bytes(b"source")
        with (
            patch("charttool.youtube.yt_dlp.YoutubeDL") as downloader,
            patch(
                "charttool.youtube.subprocess.run",
                side_effect=subprocess.CalledProcessError(1, "ffmpeg"),
            ),
            self.assertLogs("charttool.youtube", level="ERROR"),
        ):
            downloader.return_value.__enter__.return_value.prepare_filename.return_value = str(
                source
            )
            self.assertFalse(
                download_audio("https://youtu.be/test", self.root / "Song.ogg")
            )
        self.assertTrue(source.exists())

    def test_thumbnail_fallback_writes_standard_image(self):
        missing = Mock()
        missing.raise_for_status.side_effect = requests.exceptions.HTTPError("404")
        standard = Mock(content=b"jpeg")
        path = self.root / "bg.jpg"
        with patch(
            "charttool.youtube.requests.get", side_effect=[missing, standard]
        ) as request:
            self.assertTrue(download_bg("https://www.youtube.com/watch?v=test", path))
        self.assertEqual(path.read_bytes(), b"jpeg")
        self.assertEqual(
            [call.args[0] for call in request.call_args_list],
            [
                "https://i.ytimg.com/vi/test/maxresdefault.jpg",
                "https://i.ytimg.com/vi/test/sddefault.jpg",
            ],
        )
        self.assertTrue(
            all(call.kwargs["timeout"] == 10 for call in request.call_args_list)
        )

    def test_missing_thumbnails_return_failure(self):
        missing = Mock()
        missing.raise_for_status.side_effect = requests.exceptions.HTTPError("404")
        path = self.root / "bg.jpg"
        with (
            patch("charttool.youtube.requests.get", return_value=missing),
            self.assertLogs("charttool.youtube", level="ERROR"),
        ):
            self.assertFalse(download_bg("https://www.youtube.com/watch?v=test", path))
        self.assertFalse(path.exists())
