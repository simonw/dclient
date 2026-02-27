# Run tests and linters
@default: test lint

# Run pytest with supplied options
@test *options:
  uv run pytest {{options}}

# Run linters
@lint:
  echo "Linters..."
  echo "  cog"
  uv run cog --check README.md docs/*.md
  echo "  ruff check"
  uv run ruff check .
  echo "  ruff format"
  uv run ruff format . --check

# Rebuild docs with cog
@cog:
  uv run cog -r docs/*.md

# Serve live docs on localhost:8000
@docs: cog
  cd docs && uv run make livehtml

# Apply ruff fixes and formatting
@fix: cog
  uv run ruff check . --fix
  uv run ruff format .
