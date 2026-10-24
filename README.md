# JAW

A minimal Python starter project, ready for development. It includes a command-line entry point and standard-library tests. No runtime dependencies or credentials are required.

## Requirements

- Python 3.11 or later

## Set up

Run these commands from the repository root:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

On Windows, activate the environment with `.venv\Scripts\activate` instead.

## Run

```sh
jaw
jaw --name Jeremy
```

The second command prints `Hello, Jeremy!`. This greeting is a starter example to replace with the project's intended behavior.

You can also run the source directly without installation:

```sh
python -m jaw --name Jeremy
```

## Test

```sh
python -m unittest discover -s tests -v
```

## Project layout

- `jaw/`: application code and command-line entry point.
- `tests/`: automated tests.
- `pyproject.toml`: package metadata and build configuration.

Add runtime dependencies to `project.dependencies` in `pyproject.toml` when needed. Keep secrets out of Git; local `.env` files are ignored. This starter does not read environment files or need configuration variables.
