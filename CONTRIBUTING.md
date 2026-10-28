# Contributing to bugstack-python

Thank you for your interest in contributing!

## Development Setup

```bash
git clone https://github.com/Bugstackai/Bugstack-SDK-Python.git
cd bugstack-python
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev]"
```

## Running Tests

```bash
pytest
```

## Code Style

We use [Ruff](https://docs.astral.sh/ruff/) for linting and formatting:

```bash
ruff check .
ruff format .
```

## Type Checking

```bash
mypy src/bugstack
```

## Pull Requests

1. Fork the repo and create your branch from `main`
2. Add tests for any new functionality
3. Ensure all tests pass
4. Run the linter and type checker
5. Submit your PR

## Reporting Issues

Use [GitHub Issues](https://github.com/Bugstackai/Bugstack-SDK-Python/issues) to report bugs or request features.
