# Architecture Decision Records

ADRs record significant architectural decisions: the context, the options
considered, and the rationale for the choice made. They are not changed after
the decision is accepted; superseded records are moved to `obsolete/`.

ADR files are named `NNN-short-slug.md` (e.g. `001-choose-web-framework.md`).

<!-- EDIT: Add ADR entries to the table below. -->

| ADR | Title | Status |
|-----|-------|--------|
| — | *(no ADRs yet)* | — |

<!-- The ``obsolete/*`` glob keeps superseded ADRs reachable in the doctree
so a strict (-W) build does not flag them as orphans. Sphinx warns when a
glob matches zero documents, so ``obsolete/index.md`` must stay in place: it
guarantees the glob always matches at least one page. -->

```{toctree}
:maxdepth: 1
:hidden:
:glob:

obsolete/*
```
