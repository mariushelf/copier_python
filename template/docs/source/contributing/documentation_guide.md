<!-- Canonical meta-layer shipped by the update-docs skill. This file is dropped verbatim into docs/source/contributing/. Edit the canonical copy in the skill's assets/meta/, not the per-repo copy. -->

# Documentation guide

How the documentation under `docs/source/` is organized, and the conventions
every page follows. This is the reasoning behind the
[step-by-step how-to](writing_documentation.md): that page gives the
procedure, this one explains why. Voice and tone are governed separately by
[Voice and tone](voice.md).

## How the documentation is organized

Two axes structure the docs.

The **primary axis is audience** — the top-level sections divide by who is
reading:

- `glossary`, `index` — orientation for any reader.
- `concepts/`, `guides/` — library or service users.
- `operations/` — operators running the system: deployment, configuration,
  monitoring, runbooks.
- `architecture/`, `architecture/implementation/`, `contributing/`, `adr/` —
  library or service maintainers.

The **secondary axis is document type** — within an audience section, each
page is one of:

| Type | Answers | Lives in |
|------|---------|----------|
| Explanation | what / why | `concepts/`, `architecture/` |
| How-to | how is a task done | `guides/`, `operations/`, `contributing/` |
| Reference | what are the exact facts | `glossary`, `reference/`, API docs |
| Decision record | why a choice was made | `adr/` |

### Relation to Diátaxis

The four types above are the four Diátaxis quadrants (tutorial, how-to,
reference, explanation; see `diataxis.fr`). The difference is the *primary*
split. Diátaxis organizes a whole site by type; these docs organize first by
audience, and let types appear within each audience section. A library user
finds the explanation of caching (`concepts/cache`) and the how-to for
processing records (`guides/process_records`) in the same place, rather than in
separate site-wide "explanation" and "how-to" trees. The two systems are
compatible, not opposed.

## Separate the what, the how, and the why

A single page should not define a concept, walk through using it, and justify
the design all at once. Conflating the three produces a page no reader can act
on: the library user wades through internal rationale; the maintainer hunts
for an invariant buried under a tutorial. Each concern gets its own page,
linked to the others:

- **What** a thing is → its concept page (`concepts/`).
- **How** it is used → a how-to (`guides/`).
- **How** it is built → its implementation page (`architecture/implementation/`).
- **Why** it was decided → an ADR (`adr/`).

A concept page may carry light "why" inline. Deep rationale belongs in an ADR,
which the concept page links to.

## Page shapes

Pages of the same type cover the same ingredients. These are *ingredients, not
templates*: a page covers them in flowing prose under headings that fit its
subject, never a fixed boilerplate that announces each section by name. A
concept page reads like an explanation, not a filled-in form.

### Concept pages

Cover, in whatever order reads naturally:

- The concept itself — a definition and a working mental model, in plain prose.
- Its boundaries — what the library does and does not model here, and why. A
  `{important}` admonition suits a deliberate non-feature.
- Where it is used — a pointer to the relevant `guides/` how-to.
- How it is built — a pointer to the `architecture/implementation/` page.
- The decisions behind it — links to the relevant ADRs.

Write it the way the Polars user guide explains a concept: describe the thing
well. Do not label the prose with a heading like "What is this concept" — the
reader already knows they are reading about a concept.

### Implementation pages

For maintainers. Cover:

- A conceptual anchor — a pointer up to the matching `concepts/` page.
- Where it lives — module paths and `file:line` references.
- How it is built — the internal types and how they collaborate.
- The replacement seam — the port or protocol that gates swapping the
  implementation, with a `file:line`.
- Invariants and edge cases.
- The decisions — ADR cross-references.

Concept and implementation pages do not map one-to-one. One concept may
decompose into several implementation pages (a cache splits into admission,
eviction, and persistence); another stays a single page. Let the implementation
drive the split.

### How-to pages

Title them by the reader's goal ("Processing records", not "The
`process_records()` API"). Lead with the task, give ordered steps, prefer
imperatives.

### Reference pages

Exhaustive and scannable — the glossary, the FAQ, the generated API docs.
Optimized for lookup, not for reading start to finish.

## Conventions

### Only `docs/source/` is rendered

`docs/source/` is the only tree Sphinx renders. Siblings under `docs/`
(`docs/reviews/`, specs, working notes) are not in any `toctree` and never
appear in the built site, so development artifacts can live next to the docs
without polluting them.

### Code is the source of truth

Every factual claim about architecture or behavior must be traceable to
current source. The existing prose is not evidence — verify against the code.
Do not write what cannot be verified; flag an uncertain point with a
`{caution}` admonition rather than guessing. The `tests/docs/` suite pins a set
of these claims — exported symbols, enum values, defaults — and fails when code
and docs drift apart.

### Document the present, label the planned

Describe what the code does today, in the present tense. For behavior that is
designed but not yet implemented, say so explicitly in a self-contained
`{caution}` admonition — state what is unbuilt and where the design appears.
Never present an aspiration as current behavior.

### Folder indexes

Every content subdirectory of `docs/source/` carries two index files:

- `index.md` — the Sphinx section index, holding the section's `toctree`.
- `README.md` — a thin stub pointing at `index.md`, so the folder renders a
  landing page when browsed on github.com. README files are excluded from the
  Sphinx build via `exclude_patterns`; they never appear in the rendered site.

Underscore-prefixed directories (`_static/`, `_templates/`, `_apidoc/`) and
pure asset directories are exempt.

### Naming

- Name pages for what a reader seeks, in full words a newcomer recognizes.
  Internal jargon does not belong in a filename.
- Use full words in prose and identifiers; do not abbreviate technical terms
  to save characters.
- Cite external systems (third-party services, vendors) only for concrete,
  system-specific values such as endpoint URLs or rate-limit tiers, not as
  a generic stand-in for a concept.

### Cross-references

- Link in-tree pages with the MyST `{doc}` role and a source-root-absolute
  docname — `` {doc}`/concepts/cache` `` (leading slash, no `.md`). Markdown
  `../` links across directories break the strict build.
- ADRs carry no `Status:` field. Reference them as links and let them hold the
  rationale rather than restating it.
- Use `file:line` pointers freely in commit messages and pull requests,
  sparingly in reader-facing prose.

### Voice

[Voice and tone](voice.md) is the authoritative register: sober, direct, no
second-person familiarity, no marketing. It is the one document this guide does
not restate — read it before drafting.

## Building and verifying

- `make docs` builds the HTML site.
- `make docs-strict` builds with warnings-as-errors (`sphinx-build -W`). A new
  page must appear in a `toctree`, or the strict build fails. Clear
  `docs/build/` first — incremental builds hide cross-reference
  warnings.
- `make test-docs` runs the `tests/docs/` tripwires.
- `make docs-doctest` runs examples authored as `{doctest}` / `{testcode}`
  blocks.
