# Contributing to MintYourAgent

Thank you for your interest in contributing! This document provides guidelines.

## Code of Conduct

Be respectful and constructive. We're building something together.

## How to Contribute

### Reporting Bugs

1. Check existing issues first
2. Include version (`python mya.py --version`)
3. Include OS and Python version
4. Provide steps to reproduce
5. Include error messages (with `--debug` flag)

### Suggesting Features

1. Open an issue with "[Feature]" prefix
2. Describe the use case
3. Propose implementation if possible

### Pull Requests

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing`)
3. Make your changes
4. Run tests (`pytest`)
5. Run linting (`black . && isort .`)
6. Commit with conventional messages (`feat:`, `fix:`, `docs:`)
7. Push and create PR

## Development Setup

```bash
# Clone
git clone https://github.com/operatingdev/mintyouragent
cd mintyouragent

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linting
black .
isort .
mypy mya.py

# Security scan
bandit -r mya.py
```

## Code Style

- Use Black for formatting (line length 120)
- Use isort for imports
- Add type hints to all functions
- Add docstrings to public functions
- Keep functions focused and small

## Testing

- Write tests for new features
- Maintain >80% coverage
- Mock external API calls
- Test edge cases

### Running Tests

```bash
# All tests
pytest

# With coverage
pytest --cov=mya --cov-report=html

# Specific test
pytest tests/test_wallet.py -v
```

## Commit Messages

Follow Conventional Commits:

- `feat: add new command`
- `fix: handle edge case`
- `docs: update README`
- `refactor: simplify logic`
- `test: add unit tests`
- `chore: update dependencies`

## Release Process

1. Update version in `mya.py` and `pyproject.toml`
2. Update CHANGELOG.md
3. Create PR with version bump
4. After merge, tag release
5. Publish to PyPI (maintainers only)

## Questions?

- Open an issue
- Join Discord: https://discord.gg/mintyouragent

Thank you for contributing! 🚀
