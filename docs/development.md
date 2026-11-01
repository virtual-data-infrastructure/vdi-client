# Development guide

## Environment setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
```

The development extras include test, typing, formatting, Markdown-quality, and
build tools.

The examples use `python -m pip` rather than `pip` to ensure that packages are
installed into the active virtual environment's interpreter.

## Tests

Run all tests:

```bash
pytest
```

Run a focused module:

```bash
pytest tests/test_config.py
```

Generate coverage while testing:

```bash
pytest --cov=vdi_client --cov-report=term-missing
```

## Linting and static checks

```bash
ruff check .
ruff format --check .
mypy
pyright
pymarkdownlnt scan README.md PYPI.md docs/*.md src/vdi_wrapper/README.md
codespell
```

Use `ruff format .` to apply the project's Python formatting.

## Sanitizer builds

Build an AddressSanitizer-enabled library:

```bash
make asan
```

Build a ThreadSanitizer-enabled library:

```bash
make tsan
```

Both libraries are placed in `src/vdi_wrapper/build/`. Use the matching compiler
and sanitizer runtime when compiling a test program, then pass the library to
`vdi run --lib`.

## Build a platform wheel

A release wheel bundles one or more EESSI-versioned libraries. For each EESSI
version, initialize that environment and run:

```bash
make install-library-versioned EESSI_VERSION=2023.06
```

After all desired libraries are present in `lib64/`, build the wheel:

```bash
make build-wheel
```

The resulting wheel is architecture-specific and is written to the `dist/`
directory.

The target creates a temporary `.build-venv` if the `build` package is not
already available. It does not install packages into the user's global Python
environment.
