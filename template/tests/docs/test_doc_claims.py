"""Drift tripwire tests for documentation claims.

This module is a template dropped by the ``update-docs`` skill into
``tests/docs/test_doc_claims.py``. Its purpose is to pin factual claims made
in the documentation to the actual source code so that the build fails when
they drift.

Each test targets one specific, checkable claim: a public symbol that must
remain importable, a documented default value that must not change silently,
or a structural invariant of the docs tree itself. When a test fails, it
points directly at the drift — the code changed but the docs were not updated,
or vice versa.

Convention (matches the project standard): every test function carries at
least a one-line docstring describing what is being checked and why.

EDIT: Replace the placeholder assertions below with real claims sourced from
the project's documentation.
"""

from __future__ import annotations

import re
from fnmatch import fnmatch
from pathlib import Path

import pytest

# EDIT: replace ``your_package`` with the real top-level package name.
# import your_package

# ---------------------------------------------------------------------------
# Structural tests (no project-specific knowledge required)
# ---------------------------------------------------------------------------

DOCS_SOURCE = Path(__file__).parent.parent.parent / "docs" / "source"

# Matches rst explicit-title syntax: ``Some Title <docname>``.
_EXPLICIT_TITLE = re.compile(r"^.*<([^<>]+)>\s*$")


def _add_toctree_entry(
    entries: set[str], globs: set[str], item: str, base: str
) -> None:
    """Normalise one toctree body line into *entries* or *globs*.

    Skips directive option lines (``:maxdepth:``, ``:glob:``, ...) and reduces
    explicit-title entries (``Some Title <docname>``) to the docname. A glob
    pattern (``obsolete/*``) references many documents, not one docname, so it
    is resolved against *base* (the containing file's directory relative to the
    source root) and collected separately for ``fnmatch``-based reachability.
    """
    if not item or item.startswith(":"):
        return
    match = _EXPLICIT_TITLE.match(item)
    if match:
        item = match.group(1).strip()
    if any(ch in item for ch in "*?["):
        globs.add(f"{base}/{item}" if base else item)
        return
    entries.add(item)


def _collect_toctree_entries(root: Path) -> tuple[set[str], set[str]]:
    """Return (docnames, glob patterns) referenced in toctrees under *root*.

    Handles both MyST ````{toctree}```` fences (terminated by the closing
    fence) and rst ``.. toctree::`` directives inside ``eval-rst`` blocks.
    Per standard rst block rules, an rst directive body ends at the first
    non-empty line that is not indented relative to the directive line (or
    at the closing fence of the surrounding ``eval-rst`` block), so ordinary
    paragraphs following the directive are not harvested as entries.
    Glob patterns come back root-relative, ready for ``fnmatch``.
    """
    entries: set[str] = set()
    globs: set[str] = set()
    for md_file in root.rglob("*.md"):
        base = str(md_file.parent.relative_to(root)).replace("\\", "/")
        base = "" if base == "." else base
        lines = md_file.read_text(encoding="utf-8").splitlines()
        i = 0
        while i < len(lines):
            line = lines[i]
            if "```{toctree}" in line:
                # MyST fence: body runs until the closing ``` fence.
                i += 1
                while i < len(lines) and not lines[i].lstrip().startswith("```"):
                    _add_toctree_entry(entries, globs, lines[i].strip(), base)
                    i += 1
            elif line.lstrip().startswith(".. toctree::"):
                # rst directive: body is the indented block that follows.
                directive_indent = len(line) - len(line.lstrip())
                i += 1
                while i < len(lines):
                    body_line = lines[i]
                    if not body_line.strip():
                        i += 1  # blank lines may appear inside the body
                        continue
                    if body_line.lstrip().startswith("```"):
                        break  # closing fence of the eval-rst block
                    body_indent = len(body_line) - len(body_line.lstrip())
                    if body_indent <= directive_indent:
                        break  # dedented line: the directive body has ended
                    _add_toctree_entry(entries, globs, body_line.strip(), base)
                    i += 1
                continue  # re-examine the line that terminated the body
            i += 1
    return entries, globs


def test_every_md_appears_in_a_toctree() -> None:
    """Every .md page under docs/source/ must be reachable via a toctree.

    The exceptions are README.md (excluded from the build) and section
    ``index.md`` files, which are the toctree targets themselves. Orphaned
    pages produce Sphinx warnings (promoted to errors with -W) and are
    invisible to readers navigating via the sidebar; this test surfaces the
    problem at pytest time, before the build runs.
    """
    if not DOCS_SOURCE.is_dir():
        pytest.skip("docs/source not scaffolded")

    toctree_entries, toctree_globs = _collect_toctree_entries(DOCS_SOURCE)
    orphans = []
    for md_file in DOCS_SOURCE.rglob("*.md"):
        if md_file.name in ("README.md",):
            continue
        rel = md_file.relative_to(DOCS_SOURCE)
        # index.md files are the toctree entry targets themselves, not children.
        if md_file.stem == "index":
            continue
        docname = str(rel.with_suffix("")).replace("\\", "/")
        leaf = rel.stem
        # Accept a full relative docname, a bare leaf name, or a glob match
        # (e.g. an obsolete ADR pulled in via ``obsolete/*``).
        if (
            docname not in toctree_entries
            and leaf not in toctree_entries
            and not any(fnmatch(docname, pattern) for pattern in toctree_globs)
        ):
            orphans.append(str(rel))

    assert not orphans, (
        "The following pages are not referenced in any toctree:\n"
        + "\n".join(f"  docs/source/{p}" for p in sorted(orphans))
    )


# ---------------------------------------------------------------------------
# Symbol existence tests
# EDIT: replace with real exported symbols from the project.
# ---------------------------------------------------------------------------


# EDIT: Uncomment and adapt the example below. The import is the whole test;
# the bound name is intentionally unused, so append a ``noqa: F401`` comment to
# the import line to silence Ruff.
#
# def test_documented_public_symbol_exists() -> None:
#     """The symbol ``your_package.SomeClass`` must remain importable.
#
#     The reference docs at docs/source/reference/python-api.md advertise this
#     class as part of the public API. If it is renamed or removed the docs
#     become misleading; this test fails at that point.
#     """
#     from your_package import SomeClass


# ---------------------------------------------------------------------------
# Default-value tests
# EDIT: replace with real settings/constants from the project.
# ---------------------------------------------------------------------------


# EDIT: Uncomment and adapt the example below.
#
# def test_documented_default_value() -> None:
#     """The documented default for ``SomeSettings.timeout`` is 30 seconds.
#
#     docs/source/reference/settings.md states: "Default: 30". If the default
#     changes without updating the docs, this test fails.
#     """
#     from your_package.settings import SomeSettings
#
#     assert SomeSettings().timeout == 30, (
#         "docs/source/reference/settings.md documents the default timeout as 30; "
#         "update the docs if the default has intentionally changed."
#     )
