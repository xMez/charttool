"""Functions for interacting with YouTube."""

import logging
from pathlib import Path
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
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(downloaded_file),
            "-af",
            "loudnorm=I=-8:TP=-1.5:LRA=7",
            "-c:a",
            "libvorbis",
            "-q:a",
            "7",
            str(output_path),
        ]
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
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
