Should be `ci.yaml` for more precise naming.

---

## Spec

**What:** Rename `template/.github/workflows/cicd.yaml` → `template/.github/workflows/ci.yaml`,
change its internal `name: CI/CD` → `name: CI`, and update the two references to the old filename:
`template/.github/workflows/release.yaml:28` (`uses: ./.github/workflows/cicd.yaml`) and the badge
in `template/README.md.jinja:3`. No `_migrations` entry, no test changes beyond keeping the suite
green.

**Why:** The workflow contains only `lint`, `test` and `docs` jobs — there is no deployment in it.
Releasing lives in `release.yaml` and publishing in `publish.yaml`, so `cicd.yaml` / `name: CI/CD`
claims a responsibility the file does not have, and generated projects inherit that misnomer. `ci`
is what the file actually is, and it matches this repo's own `.github/workflows/ci.yaml`.

### Copier-update behaviour (the open question, answered)

Verified empirically with copier 9.11.3 by generating a project from `origin/main`, committing the
rename in a template clone, and running `copier update`:

- **A clean `copier update` does perform the rename.** `cicd.yaml` is deleted, `ci.yaml` is created,
  and the `release.yaml` / `README.md` references are rewritten. This holds whether or not the
  template carries git tags. **So this ticket needs no `_migrations` entry.**
- **A downstream project's local edits to `cicd.yaml` are silently dropped** — they are not carried
  into `ci.yaml`, and no conflict or `.rej` file is produced. Recoverable from the project's own git
  history, but the update will not warn.
- Two pre-existing template defects gate the above; both are **out of scope here** (see below) and
  neither blocks this rename:
  1. The template ships no `{{ _copier_conf.answers_file }}.jinja`, so generated projects have no
     `.copier-answers.yml` and `copier update` refuses to run at all: *"Cannot update because cannot
     obtain old template references from `.copier-answers.yml`."* Every project generated to date is
     therefore un-updatable, which is why this rename cannot strand anyone today.
  2. `_tasks` (`git init`, `git checkout -b main`) also run on `update` and fail there
     (`fatal: a branch named 'main' already exists`, exit 128). The abort lands *after* `ci.yaml` is
     written and *before* `cicd.yaml` is deleted — a half-applied rename leaving both files, with the
     stale `cicd.yaml` still triggering on `push`/`pull_request` and producing duplicate CI runs.

### Notes for the implementer

- Use `git mv` so the rename is recorded as a rename.
- `cicd.yaml` has no `.jinja` suffix and is copied verbatim (`_templates_suffix: .jinja`); keep it
  that way — its `${{ matrix.python-version }}` would collide with Jinja.
- Branch rulesets require **job** names (`lint`, `test`, `docs`), which do not change, so no ruleset
  breaks. The README **badge URL is per-filename**, so existing generated projects keep a badge
  pointing at `cicd.yaml` until they re-render; acceptable, and noted rather than mitigated.
- #7 (CI gate) edits the same file and declares this rename out of its own scope — whichever lands
  first, the other rebases. Not a dependency.

## Acceptance criteria

- [ ] `template/.github/workflows/ci.yaml` exists with the previous `cicd.yaml` content and no
      `.jinja` suffix; `template/.github/workflows/cicd.yaml` no longer exists.
- [ ] The rename is recorded as a rename in the commit (`git show --stat` shows R, not add+delete).
- [ ] `ci.yaml` line 1 reads `name: CI`.
- [ ] `template/.github/workflows/release.yaml` uses `./.github/workflows/ci.yaml`.
- [ ] The `Tests` badge in `template/README.md.jinja` points at `actions/workflows/ci.yaml` in both
      the image URL and the link target.
- [ ] `git grep -i cicd` returns nothing under `template/`.
- [ ] `uv run pytest tests` is green.
- [ ] Commit uses a `refactor:` prefix and carries no AI attribution trailer.

## Out of scope

- Shipping `{{ _copier_conf.answers_file }}.jinja` so generated projects become updatable (defect 1
  above) — its own ticket.
- Guarding `_tasks` with `when: "{{ _copier_conf.operation == 'copy' }}"` so `copier update` is not
  aborted by `git init` / `git checkout -b main` (defect 2 above) — its own ticket.
- Renaming the `template/docs/source/contributing/ci_cd.md` stub or its `# CI/CD` heading: that page
  documents the whole pipeline including release and publish, so its name is not the misnomer.
- Any `_migrations` entry — the empirical result above shows the rename propagates without one.

## Verification

```bash
uv run pytest tests          # needs network; renders a project and runs its lint/test/pre-commit
git grep -i cicd -- template/ ; echo "exit=$?"   # expect no matches
```

No `Depends-on:` — every file this spec touches is present on `origin/main`.
