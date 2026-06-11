SHELL := /bin/bash

.PHONY: sync clean test test-unit-tests test-doctest build ty ruff import_lint type_check lint pre_commit format

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
	# Run doctests in src/. Tolerates exit code 5 (no tests collected) so that
	# `make test` passes on a fresh project before any doctests have been added.
	uv run --no-sources pytest --doctest-modules src; rc=$$?; [ $$rc -eq 5 ] && exit 0 || exit $$rc

build:
	uv build

ty:
	uv run ty check

ruff:
	uv run --no-sources ruff format --check --target-version py312 src tests
	uv run --no-sources ruff check --fix --exit-non-zero-on-fix src tests

import_lint:
	uv run --no-sources lint-imports

type_check: ty

lint: ruff type_check import_lint

pre_commit:
	pre-commit run --all-files

format:
	# format all code
	uv run ruff format

# ---------------------------------------------------------------------------
# Documentation targets — merged into the project Makefile by the
# update-docs skill. Assumes Sphinx source is at docs/source/ and output
# lands at docs/build/.
#
# This header also serves as the merge sentinel: the scaffolding step looks
# for it in the project Makefile to detect that the block was already merged
# (idempotency). Keep the header text intact when editing.
# ---------------------------------------------------------------------------

# Command prefix that runs tools inside the project environment. These
# targets are opinionated on uv (the `uv sync` calls below assume it) and on
# a src/ layout (docs-live watches src/); RUN stays a variable only so
# one-off invocations can override it.
RUN ?= uv run

.PHONY: docs docs-strict docs-linkcheck docs-live test-docs docs-doctest clean-docs

# Build HTML documentation.
docs:
	uv sync --group docs
	$(RUN) sphinx-build -a -b html docs/source docs/build/html
	@echo "Open docs/build/html/index.html"

# Strict build: fail on any warning.
# Use this in CI to catch broken cross-references, orphaned pages, and
# autodoc surprises before they reach the main branch.
docs-strict:
	uv sync --group docs
	$(RUN) sphinx-build -W --keep-going -a -b html docs/source docs/build/html

# Check external links. Kept separate from docs-strict because it depends on
# the network and is therefore flaky in CI and useless offline.
docs-linkcheck:
	uv sync --group docs
	$(RUN) sphinx-build -a -b linkcheck docs/source docs/build/linkcheck

# Live-reload mode: rebuild on file change. Watches both docs source and src.
docs-live:
	uv sync --group docs
	$(RUN) sphinx-autobuild -a -b html docs/source docs/build/html \
		--watch src \
		--open-browser

# Run the docs drift-tripwire test suite.
test-docs:
	$(RUN) pytest tests/docs

# Run Sphinx doctest builder to verify code examples in docs.
docs-doctest:
	uv sync --group docs
	$(RUN) sphinx-build -a -b doctest docs/source docs/build/doctest

# Remove build artefacts and auto-generated API stubs. The _apidoc path must
# match the ``:toctree:`` directory in docs/source/reference/python-api.md.
clean-docs:
	rm -rf docs/build docs/source/reference/_apidoc
