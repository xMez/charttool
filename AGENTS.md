# Working on charttool

Charttool is a Python 3.13+ Typer CLI that creates StepMania/Pump `.ssc`
starter charts from YouTube videos. Use `uv` and the committed `uv.lock`.

## Start here

```sh
make setup    # install the locked project and dev dependencies
make doctor   # check the environment; ffmpeg is optional for offline tests
make check    # correctness lint + offline regression tests
```

After setup, `make check` should take seconds. With an existing environment,
you can bypass dependency synchronization:

```sh
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/ruff check --select E9,F63,F7,F82 src tests scripts
```

Run one test file with
`uv run --frozen python -m unittest discover -s tests -p 'test_cli.py' -v`.
Run `uv run --frozen ct --help` for a safe CLI smoke check.
The command is `ct URL`, not `ct create URL` (Typer exposes the single command
directly).

## Project map

- `src/charttool/cli.py`: configuration, prompts, filename sanitization,
  SSC template, output files, and editor launch.
- `src/charttool/parsing.py`: title cleanup and artist/title candidates.
- `src/charttool/youtube.py`: active metadata, thumbnail, and audio integration;
  invokes ffmpeg with loudness normalization and Vorbis quality 7.
- `src/charttool/youtube_old.py`: historical implementation, not imported by the
  CLI. Work on `youtube.py` unless the task explicitly concerns the old module.
- `tests/`: standard-library unittest regression suite; no pytest dependency.
- `scripts/doctor.py`: read-only prerequisite checks.
- `Makefile` and `.github/workflows/check.yml`: local and CI harness entry points.

## Development boundaries

`load_config()` reads or creates `config.ini` in the **current working directory**.
The tracked file contains a user's absolute dance-chart destination. Do not use
it for automated chart creation. Tests run in temporary directories and mock
downloads, HTTP requests, ffmpeg, and editor launches. Extend `OfflineTestCase`
for integration tests and explicitly mock the boundary you intend to exercise.
It rejects unmocked requests, YouTube downloader construction, subprocesses, and
Windows editor launches. Tests run serially because they change the process CWD.

Real creation requires network access and ffmpeg and opens the resulting SSC
with the platform's default application. Keep normal validation offline.
Use temporary paths for generated media and charts. Avoid modifying user config
or existing chart collections as part of development.

`make lint` gates syntax and definite runtime errors (`E9,F63,F7,F82`).
`make lint-all` reports the existing source's stricter Ruff `ALL` rules and
currently fails on pre-existing style/complexity issues. Do not bulk-fix unrelated
source to satisfy that report. Use `uv run --frozen ruff format tests scripts`
when formatting harness changes.

When changing behavior, add or update the relevant regression test, run
`make check`, and report the result. When intentionally changing dependencies,
update both `pyproject.toml` and `uv.lock`; ordinary setup uses `--frozen`.
