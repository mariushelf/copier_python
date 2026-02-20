SHELL := /bin/bash

.PHONY: sync clean test test-unit-tests test-doctest build ty ruff type_check lint pre_commit format

sync:
	uv sync --all-extras

clean:
	rm -rf dist
	rm -rf .artifacts
	rm -rf .mypy_cache
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +


test: test-unit-tests test-doctest

test-unit-tests:
	uv run --no-sources pytest tests

test-doctest:
	uv run --no-sources pytest src

build:
	uv build

ty:
	uv run ty check

ruff:
	uv run --no-sources ruff format --check --target-version py312 src tests
	uv run --no-sources ruff check --fix --exit-non-zero-on-fix src tests

type_check: ty

lint: ruff type_check

pre_commit:
	pre-commit run --all-files

format:
	# format all code
	uv run ruff format
