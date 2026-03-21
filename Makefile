PYTHON ?= python
UV ?= uv
UV_CACHE_DIR ?= $(PWD)/.uv-cache
PACKAGE = watchlist_signal_bot

.PHONY: sync lint format test run dry-run render-workflows check-workflows clean

sync:
	UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) sync --group dev

lint:
	UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) run ruff check .

format:
	UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) run ruff format .

test:
	UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) run pytest

run:
	UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) run python -m $(PACKAGE).main

dry-run:
	UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) run python -m $(PACKAGE).main --dry-run

render-workflows:
	UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) run python -m $(PACKAGE).github_actions

check-workflows:
	UV_CACHE_DIR=$(UV_CACHE_DIR) $(UV) run python -m $(PACKAGE).github_actions --check

clean:
	rm -rf .pytest_cache .ruff_cache htmlcov
