"""Check local prerequisites without downloading media or writing configuration."""

import importlib.util
import shutil
import sys
from importlib.metadata import PackageNotFoundError, version


def main() -> int:
    """Report development prerequisites and optional media tooling."""
    failed = sys.version_info < (3, 13)
    print(f"Python: {sys.version.split()[0]} (requires >=3.13)")
    for name in ("charttool", "typer", "unidecode", "yt_dlp", "requests", "ruff"):
        available = importlib.util.find_spec(name) is not None
        print(f"{name}: {'OK' if available else 'MISSING; run make setup'}")
        failed |= not available
    try:
        print(f"Installed charttool: {version('charttool')}")
    except PackageNotFoundError:
        print("Installed charttool: MISSING; run make setup")
        failed = True
    for name in ("uv", "ct"):
        executable = shutil.which(name)
        print(f"{name}: {executable or 'MISSING; run make setup / install uv'}")
        failed |= executable is None
    ffmpeg = shutil.which("ffmpeg")
    print(
        f"ffmpeg: {ffmpeg or 'optional for tests; required for real audio conversion'}"
    )
    return int(failed)


if __name__ == "__main__":
    raise SystemExit(main())
