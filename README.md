# charttool

Create StepMania/Pump starter charts from YouTube videos. The interactive `ct`
command lets you choose title, artist, step type, and difficulty, then downloads
audio and a background image and writes an `.ssc` file.

Requires Python 3.13+, [uv](https://docs.astral.sh/uv/), and ffmpeg on `PATH` for
real audio downloads.

```sh
make setup
uv run --frozen ct --help
uv run --frozen ct 'https://www.youtube.com/watch?v=VIDEO_ID' --output ./my-chart
```

The CLI reads or creates `config.ini` in the current directory. Its `[charttool]`
section supports `pump_dir`, `dance_dir`, and `creator`. This checkout's config
includes a local absolute output path; review it before real chart creation, or
pass `--output`. `ct --config` displays the active configuration. Successful
creation opens the chart in the default application.

## Development

```sh
make setup    # install locked dependencies, including Ruff
make doctor   # check Python, imports, CLI, and optional ffmpeg
make check    # fast correctness lint and offline unittest suite
make test     # only tests
make lint-all # full source lint report, including existing style debt
```

The tests use temporary files and mocked YouTube, HTTP, ffmpeg, and editor
boundaries; no media downloads or GUI applications are needed. GitHub Actions
runs the same `make check` on pushes and pull requests. See [AGENTS.md](AGENTS.md)
for the project map, focused test commands, and development conventions.
