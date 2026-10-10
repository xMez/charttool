"""Functions for interacting with YouTube."""

import logging
from pathlib import Path

import requests
import typer
import yt_dlp

from charttool.parsing import parse_title

LOG = logging.getLogger(__name__)


def get_title(url: str) -> list[dict] | None:
    """Extract video information from a YouTube URL.

    Returns a list of possible title/artist combinations.
    Returns None if the video info cannot be extracted.
    """
    ydl_opts = {"quiet": True, "no_warnings": True, "extract_flat": True}

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
            title = info.get("title", "")
            channel = info.get("uploader", "")

            results = parse_title(title)
            # Add channel as potential artist (before the empty artist option)
            if channel:
                results.insert(-1, {"title": title, "artist": channel})
        except Exception as e:
            LOG.exception("Failed to extract video info")
            typer.echo(f"Error extracting video info: {e}", err=True)
            raise typer.Exit(1) from e
        else:
            return results


def download_audio(url: str, output_path: Path) -> bool:
    """Download audio from YouTube URL and save to the specified path.

    Returns True if successful, False otherwise.
    """
    # Check if file already exists
    if output_path.exists():
        msg = f"Audio file already exists at {output_path}, skipping download"
        LOG.info(msg)
        typer.echo(msg)
        return True

    ydl_opts = {
        "format": "bestaudio",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "vorbis",
                "preferredquality": 7,
            },
        ],
        "outtmpl": str(output_path.with_suffix("")),
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            ydl.download([url])
        except Exception as e:
            LOG.exception("Failed to download audio")
            typer.echo(f"Error downloading audio: {e}", err=True)
            return False
        else:
            return True


def download_bg(url: str, output_path: Path) -> bool:
    """Download thumbnail from YouTube URL and save to the specified path.

    Returns True if successful, False otherwise.
    """
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

        LOG.warning("Failed to download maxres thumbnail")
        typer.echo("Error downloading maxres thumbnail")
        return False
    else:
        with output_path.open("wb") as f:
            f.write(response.content)
        return True
