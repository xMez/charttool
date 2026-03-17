"""Tool for creating StepMania/PIU chart files from YouTube videos."""

import configparser
import os
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

import platformdirs
import typer
from typer.colors import BLUE, CYAN, GREEN, MAGENTA, RED, WHITE, YELLOW
from unidecode import unidecode

SSC_TEMPLATE = """\
#VERSION:0.83;
#TITLE:{title};
#SUBTITLE:;
#ARTIST:{artist};
#TITLETRANSLIT:;
#SUBTITLETRANSLIT:;
#ARTISTTRANSLIT:;
#GENRE:;
#CREDIT:;
#MUSIC:{music_file};
#BANNER:bn.jpg;
#BACKGROUND:bg.jpg;
#CDTITLE:cdtitle.png;
#SAMPLESTART:;
#SAMPLELENGTH:;
#SELECTABLE:YES;
#OFFSET:;
#BPMS:0.000=120.000;
#STOPS:;
#BGCHANGES:;
#FGCHANGES:;
//--------------- {step_type} - {creator} ----------------
#NOTEDATA:;
#STEPSTYPE:{step_type};
#DESCRIPTION:{creator};
#DIFFICULTY:{difficulty};
#METER:1;
#RADARVALUES:0,0,0,0,0;
#SPEEDS:0.000=1.000=0.000=0;
#SCROLLS:0.000=1.000;
#TICKCOUNTS:0.000=4;
#TIMESIGNATURES:0.000=4=4;
#COMBOS:0.000=1;
#NOTES:;
"""


@dataclass
class Config:
    """Configuration settings for charttool."""

    pump_dir: str = "pump-charts"
    dance_dir: str = "dance-charts"
    creator: str = "Anonymous"

    def get_output_dir(self, step_type: str) -> str:
        """Get the appropriate output directory based on step type."""
        if step_type.startswith("pump"):
            return self.pump_dir
        if step_type.startswith("dance"):
            return self.dance_dir
        return self.pump_dir  # Default to pump


def load_config() -> Config:
    """Load configuration from file or return defaults."""
    parser = configparser.ConfigParser()
    config_dir = Path(
        platformdirs.user_config_dir("charttool", appauthor=False, ensure_exists=True),
    )
    config_path = config_dir / "config.ini"

    if not config_path.exists():
        # Create default config file
        config = Config()
        parser["charttool"] = {
            "pump_dir": config.pump_dir,
            "dance_dir": config.dance_dir,
            "creator": config.creator,
        }
        with config_path.open("w", encoding="utf-8") as f:
            parser.write(f)
    else:
        parser.read(config_path)
        config = Config(
            pump_dir=parser["charttool"]["pump_dir"],
            dance_dir=parser["charttool"]["dance_dir"],
            creator=parser["charttool"]["creator"],
        )

    return config


app = typer.Typer()


def sanitize_filename(filename: str) -> str:
    """Remove invalid characters and transliterate Unicode characters in filename."""
    # First transliterate Unicode characters
    transliterated = unidecode(filename)
    # Then remove any remaining invalid characters
    return re.sub(r'[<>:"/\\|?*]', "", transliterated)


@app.command()
def create(  # noqa: PLR0915
    url: str = typer.Argument(..., help="YouTube URL of the song"),
    output_dir: str | None = typer.Option(
        None,
        "--output",
        "-o",
        help="Output directory (defaults to config or song title)",
    ),
) -> None:
    """Create an SSC file from a YouTube video."""
    config = load_config()

    match urlparse(url).netloc:
        case "www.youtube.com" | "youtube.com" | "youtu.be":
            from youtube import download_audio, download_bg, get_title  # noqa: PLC0415
        case _:
            typer.echo("Error: Non supported URL", err=True)
            raise typer.Exit(1)

    url = url.split("&")[0]

    # Get video info and possible title/artist combinations
    title_options = get_title(url)

    # Present options to user
    typer.echo("\nPossible title/artist combinations:", color=BLUE)
    for i, option in enumerate(title_options, 1):
        typer.echo(f"{i}. Title: {typer.style(option['title'], fg=GREEN)}")
        typer.echo(
            f"   Artist: {typer.style(option['artist'], fg=YELLOW)}",
        )
        typer.echo()

    # Get user choice
    choice = typer.prompt(
        typer.style("Select option number", fg=BLUE),
        type=int,
        default=1,
    )
    if not 1 <= choice <= len(title_options):
        typer.echo("Invalid choice", err=True)
        raise typer.Exit(1)

    selected = title_options[choice - 1]

    # Allow user to modify the selection
    title = typer.prompt(
        typer.style("Enter/modify song title", fg=BLUE),
        default=selected["title"],
    )
    artist = typer.prompt(
        typer.style("Enter/modify artist name", fg=BLUE),
        default=selected["artist"],
    )

    # Get step type
    step_types = {"1": "pump-single", "2": "dance-single", "3": "pump-double"}

    step_choice = typer.prompt(
        typer.style("\nSelect step type:", fg=BLUE)
        + "\n"
        + "\n".join(f"{k}: {typer.style(v, fg=GREEN)}" for k, v in step_types.items())
        + "\nChoice",
        type=str,
        default="1",
    )

    if step_choice not in step_types:
        typer.echo("Invalid step type choice", err=True)
        raise typer.Exit(1)

    step_type = step_types[step_choice]

    # Get difficulty
    difficulties = {
        "1": ("Beginner", CYAN),  # Light blue for BG
        "2": ("Easy", GREEN),  # Green for EZ
        "3": ("Medium", YELLOW),  # Yellow/Gold for NM
        "4": ("Hard", RED),  # Red for HD
        "5": ("Challenge", MAGENTA),  # Purple for IN
        "6": ("Edit", WHITE),  # White/Gray for ED
    }

    difficulty_choice = typer.prompt(
        typer.style("\nSelect difficulty:", fg=BLUE)
        + "\n"
        + "\n".join(
            f"{k}: {typer.style(v[0], fg=v[1])}" for k, v in difficulties.items()
        )
        + "\nChoice",
        type=str,
        default="5",
    )

    if difficulty_choice not in difficulties:
        typer.echo("Invalid difficulty choice", err=True)
        raise typer.Exit(1)

    difficulty = difficulties[difficulty_choice][0]

    ascii_title = sanitize_filename(title)
    dir_name = f"{ascii_title} ({config.creator})"

    # Create output directory
    if output_dir is None:
        output_dir = Path(config.get_output_dir(step_type)) / dir_name

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Download audio
    audio_path = output_path / f"{ascii_title}.ogg"
    if not download_audio(url, audio_path):
        typer.echo("Failed to download audio", err=True)
        raise typer.Exit(1)

    # Download bg
    bg_path = output_path / "bg.jpg"
    typer.echo(f"Downloading bg to {bg_path}")
    if not download_bg(url, bg_path):
        typer.echo("Failed to download bg", err=True)
        raise typer.Exit(1)

    # Create SSC file
    ssc_content = SSC_TEMPLATE.format(
        title=title,
        artist=artist,
        creator=config.creator,
        music_file=f"{ascii_title}.ogg",
        step_type=step_type,
        difficulty=difficulty,
    )
    ssc_path = output_path / f"{ascii_title}.ssc"
    ssc_path.write_text(ssc_content, encoding="utf-8")

    typer.echo(f'\nFiles created successfully in directory: "{output_path.absolute()}"')

    os.startfile(ssc_path)  # noqa: S606


if __name__ == "__main__":
    app()
