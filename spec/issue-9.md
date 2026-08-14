Port the *added-fact* documentation rule from
[XomniaAI/agentic-engineering-loop#434](https://github.com/XomniaAI/agentic-engineering-loop/pull/434)
into the template's `AGENTS.md`, so generated projects tell their agents to keep
docs, docstrings, and comments short.

## Why

The template already enforces docstring **presence** — ruff `D` with the numpy
convention in `template/pyproject.toml.jinja` — but nothing bounds their
**length**. Agents working in a freshly generated project therefore produce
`Parameters`/`Returns` blocks that restate the annotations, step-by-step
narrations of the implementation, and docstrings that only grow on every edit.
Upstream #434 fixed exactly this gap in the loop's own `AGENTS.md` with a single
rule: past the summary line, a line must carry a fact the code cannot.

`template/AGENTS.md` is the natural home — it is the file `template/CLAUDE.md`
includes (`@AGENTS.md`), and it currently holds only *Package Management* and
*Git Conventions*.

## Scope

Two files, both under `template/`:

1. `template/AGENTS.md` — append the new section (see verbatim text below).
2. `tests/test_template.py` — in `test_template_renders`, add coverage that the
   agent-instruction files actually land in a generated project:

   ```python
   assert (project_path / "AGENTS.md").is_file()
   assert (project_path / "CLAUDE.md").is_file()
   ```

No other file changes.

## Exact text to add

Append at the **end of `template/AGENTS.md`**, after the *Git Conventions*
section, separated by one blank line. Heading is Title Case to match the two
existing headings (upstream uses sentence case; the template does not). Prose
wrapped at 80 columns. `template/AGENTS.md` is a static file (no `.jinja`
suffix), so it must contain **no Jinja expressions** — do not reference
`{{ project_slug }}` or any other variable.

```markdown
## Documentation and Comment Style

Brevity is not tidiness — it is what gets the text read. A docstring, comment,
or page nobody reads still has to be maintained, so it is worse than none.

Docstring *presence* is enforced by ruff's `D` rules (numpy convention) in
`pyproject.toml`. This section bounds their *length*.

The unit of judgement is the *added fact*: after the summary line, every line
must tell the reader something they cannot get from the name, the signature,
the type hints, or the code itself.

Earns more than a summary line:

- a contract the signature doesn't show — preconditions, invariants, what it
  raises
- units, bounds, or formats a type can't carry (`timeout: float` — seconds or
  milliseconds?)
- caller-visible behaviour that would surprise — mutation, ordering,
  idempotency, blocking, retries, cost (a network round-trip, an LLM call)
- a pointer to the *why* when it isn't obvious (link the issue or ADR, don't
  restate it)

Does not:

- restating the signature, or a numpy `Parameters`/`Returns` section where the
  name and type already say it
- narrating the implementation step by step — that's the code
- history ("previously…", "refactored to…") — that's git
- examples for a function whose use is obvious from its name

The same rule governs prose: the README covers what a reader needs to install,
run, and maintain the project; implementation detail belongs in the code.
Prefer a list, table, or short code example over paragraphs. When editing an
existing docstring, comment, or page, it must not get longer unless behaviour
was added.
```

## Deliberately not ported from #434

- **The `docs/source/contributing/code_style.md` half.** The template ships no
  Sphinx `docs/` tree and no contributing guide, so that counterpart has no
  target here. `AGENTS.md` is the single source.
- **Loop-specific wording.** "the cost of spawning a Claude run" becomes the
  generic "a network round-trip, an LLM call"; "`docs/` covers behaviour needed
  to operate or maintain the loop" becomes the README sentence above.
- **The port-inheritance rewording** — specific to the upstream codebase (also
  dropped by #434 itself relative to its own upstream).

## Out of scope

- Adding a root-level `AGENTS.md` for the `copier_python` repo itself.
- Adding a `docs/` tree or `CONTRIBUTING.md` to the template (that belongs in
  its own issue if wanted).
- Changing the ruff `D` selection or its ignore list in
  `template/pyproject.toml.jinja`.
- Retro-fitting the rule onto the template's existing docstrings in
  `template/src/{{ project_slug }}/*.jinja` — they are already one-liners and
  comply.

## Acceptance criteria

- [ ] `template/AGENTS.md` ends with the *Documentation and Comment Style*
      section, matching the text above; the existing *Package Management* and
      *Git Conventions* sections are unchanged.
- [ ] No Jinja delimiters (`{{`, `{%`) introduced in `template/AGENTS.md`.
- [ ] `tests/test_template.py::test_template_renders` asserts both `AGENTS.md`
      and `CLAUDE.md` exist in the generated project.
- [ ] `uv run pytest tests` passes (all tests, including the rendered
      project's `make lint`, `make test`, and pre-commit run).
- [ ] Commit message uses the `docs:` prefix and carries no `Co-Authored-By` or
      other AI attribution trailer, per the template's own *Git Conventions*.

## Verification

```bash
cd /workspace/copier_python
uv run pytest tests -q
```

The suite generates a project into a temp dir, runs `uv sync`, then `make lint`,
`make test`, and `pre-commit run --all-files` inside it — so it needs network
access and takes a few minutes. Nothing in the added text is executable, so a
green suite plus a read of the rendered `AGENTS.md` is the full check.

## Risk

Low. Documentation-only text in a static template file, plus two assertions.
Worst case is wording taste, reviewable in the diff.
