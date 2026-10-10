"""Exercise user-facing flows without downloads or launching an editor."""

from pathlib import Path
from unittest.mock import patch

from typer.testing import CliRunner

from charttool.cli import Config, app, load_config
from support import OfflineTestCase


class CliTests(OfflineTestCase):
    def setUp(self):
        super().setUp()
        self.runner = CliRunner()

    def test_config_defaults_and_round_trip(self):
        self.assertEqual(load_config(), Config())
        path = self.root / "config.ini"
        self.assertTrue(path.exists())
        path.write_text(
            "[charttool]\npump_dir = pump\ndance_dir = dance\ncreator = Tester\n"
        )
        config = load_config()
        self.assertEqual(config.creator, "Tester")
        self.assertEqual(config.get_output_dir("pump-double"), "pump")
        self.assertEqual(config.get_output_dir("dance-single"), "dance")

    def test_help_is_side_effect_free(self):
        result = self.runner.invoke(app, ["--help"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn("--output", result.output)
        self.assertFalse((self.root / "config.ini").exists())

    def test_show_config(self):
        result = self.runner.invoke(app, ["--config"])
        self.assertEqual(result.exit_code, 0, result.output)
        self.assertIn(str(self.root / "config.ini"), result.output)
        self.assertIn("Anonymous", result.output)

    def test_unsupported_url(self):
        result = self.runner.invoke(app, ["https://example.com/song"])
        self.assertEqual(result.exit_code, 1)
        self.assertIn("Non supported URL", result.output)

    def test_create_writes_chart_with_selected_metadata(self):
        for step_choice, step_type in (
            ("1", "dance-single"),
            ("2", "pump-single"),
            ("3", "pump-double"),
        ):
            with self.subTest(step_type=step_type):
                output = self.root / step_type
                with (
                    patch(
                        "charttool.youtube.get_title",
                        return_value=[{"title": "Jóga", "artist": "Björk"}],
                    ) as title,
                    patch(
                        "charttool.youtube.download_audio", return_value=True
                    ) as audio,
                    patch(
                        "charttool.youtube.download_bg", return_value=True
                    ) as background,
                    patch("charttool.cli.platform.system", return_value="Linux"),
                    patch("charttool.cli.subprocess.run") as launch,
                ):
                    result = self.runner.invoke(
                        app,
                        [
                            "https://www.youtube.com/watch?v=test&list=ignored",
                            "-o",
                            str(output),
                        ],
                        input=f"1\n\n\n{step_choice}\n5\n",
                    )
                self.assertEqual(result.exit_code, 0, (result.output, result.exception))
                content = (output / "Joga.ssc").read_text()
                for field in (
                    "#TITLE:Jóga;",
                    "#ARTIST:Björk;",
                    "#MUSIC:Joga.ogg;",
                    f"#STEPSTYPE:{step_type};",
                    "#DIFFICULTY:Challenge;",
                    "#CREDIT:Anonymous;",
                ):
                    self.assertIn(field, content)
                title.assert_called_once_with("https://www.youtube.com/watch?v=test")
                audio.assert_called_once_with(
                    "https://www.youtube.com/watch?v=test", output / "Joga.ogg"
                )
                background.assert_called_once_with(
                    "https://www.youtube.com/watch?v=test", output / "bg.jpg"
                )
                launch.assert_called_once_with(["xdg-open", output / "Joga.ssc"])

    def test_failed_audio_stops_before_chart_or_editor(self):
        with (
            patch(
                "charttool.youtube.get_title",
                return_value=[{"title": "Song", "artist": "Artist"}],
            ),
            patch("charttool.youtube.download_audio", return_value=False),
            patch("charttool.youtube.download_bg") as background,
        ):
            result = self.runner.invoke(
                app, ["https://youtu.be/test", "-o", "out"], input="1\n\n\n1\n5\n"
            )
        self.assertEqual(result.exit_code, 1, result.output)
        self.assertIn("Failed to download audio", result.output)
        background.assert_not_called()
        self.assertFalse(Path("out/Song.ssc").exists())
