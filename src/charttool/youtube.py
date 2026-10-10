"""Functions for interacting with YouTube."""

import logging
import math
from pathlib import Path
import re
import subprocess

import requests
import typer
import yt_dlp

from charttool.parsing import parse_title

LOG = logging.getLogger(__name__)


def get_title(url: str) -> list[dict] | None:
    """Extract video information from a YouTube URL."""
    ydl_opts = {"quiet": True, "no_warnings": True, "extract_flat": True}

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            title = info.get("title", "")
            channel = info.get("uploader", "")

            results = parse_title(title)
            if channel:
                results.insert(-1, {"title": title, "artist": channel})
        except Exception as e:
            LOG.exception("Failed to extract video info")
            typer.echo(f"Error extracting video info: {e}", err=True)
            raise typer.Exit(1) from e
        else:
            return results


def download_audio(url: str, output_path: Path) -> bool:
    """Download highest quality audio from YouTube and convert to OGG Vorbis."""
    if output_path.exists():
        msg = f"Audio file already exists at {output_path}, skipping download"
        LOG.info(msg)
        typer.echo(msg)
        return True

    # Temporary download path (original format)
    temp_path = output_path.with_suffix(".%(ext)s")

    ydl_opts = {
        "format": "bestaudio",
        "outtmpl": str(temp_path),
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=True)
            downloaded_file = Path(ydl.prepare_filename(info))
        except Exception as e:
            LOG.exception("Failed to download audio")
            typer.echo(f"Error downloading audio: {e}", err=True)
            return False

    # Convert to OGG Vorbis with quality 7
    try:
        typer.echo("Converting audio!")
        measurement = subprocess.run(
            [
                "ffmpeg",
                "-hide_banner",
                "-nostats",
                "-i",
                str(downloaded_file),
                "-af",
                "ebur128=framelog=verbose",
                "-f",
                "null",
                "-",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        readings = re.findall(r"I:\s*([-+\d.inf]+)\s+LUFS", measurement.stderr)
        if not readings:
            raise ValueError("ffmpeg did not report integrated loudness")
        integrated_loudness = float(readings[-1])
        # Apply only constant gain; no peak limiting or loudness-range processing.
        # Silence has no finite loudness and should retain its original gain.
        gain = -6 - integrated_loudness if math.isfinite(integrated_loudness) else 0
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(downloaded_file),
            "-af",
            f"volume={gain:g}dB",
            "-c:a",
            "libvorbis",
            "-q:a",
            "7",
            str(output_path),
        ]
        subprocess.run(cmd, check=True)
    except (subprocess.CalledProcessError, ValueError) as e:
        LOG.exception("Failed to convert audio to OGG Vorbis")
        typer.echo(f"Error converting audio: {e}", err=True)
        return False
    else:
        # Optionally remove the original downloaded file
        if downloaded_file.exists() and downloaded_file != output_path:
            downloaded_file.unlink()
        return True


def download_bg(url: str, output_path: Path) -> bool:
    """Download thumbnail from YouTube URL."""
    if output_path.exists():
        msg = f"Thumbnail already exists at {output_path}, skipping download"
        LOG.info(msg)
        typer.echo(msg)
        return True

    video_id = url.split("v=")[1]
    maxres_url = f"https://i.ytimg.com/vi/{video_id}/maxresdefault.jpg"
    standard_url = f"https://i.ytimg.com/vi/{video_id}/sddefault.jpg"

    response = requests.get(maxres_url, timeout=10)
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        response = requests.get(standard_url, timeout=10)
        try:
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            LOG.exception("Failed to download thumbnail")
            typer.echo(f"Error downloading thumbnail: {e}", err=True)
            return False
        else:
            with output_path.open("wb") as f:
                f.write(response.content)
            return True
    else:
        with output_path.open("wb") as f:
            f.write(response.content)
        return True
