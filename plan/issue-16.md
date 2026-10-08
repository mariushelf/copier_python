# Plan: #16, use hyphens in generated GitHub repository URLs

## What I found in the tree

- Only three template lines build `github.com/{{ github_username }}/{{ project_slug }}`: `template/pyproject.toml.jinja:28-29` and `template/README.md.jinja:3` and `:9`. A grep of `template/` for `github.com` and `github_username` finds nothing else. `.pre-commit-config.yaml.jinja` and `README.md.jinja:74` point at third-party repositories. `.claude/settings.json` only lists the bare host. These stay as they are.
- The template already builds the hyphenated name inline as `{{ project_slug | replace('_', '-') }}`. It does this 4 times: `pyproject.toml.jinja:6`, `README.md.jinja:4` (twice) and `:25`, and `docs/source/conf.py.jinja:25`.
- The `project_slug` uses that must keep underscores are: `pyproject.toml.jinja:32` (wheel `packages`), `:114`, `:129`, `:135` and `:149` (import-linter), all of `AGENTS.md.jinja`, `python-api.md.jinja`, and the `src/` and `tests/` file and directory names.
- The tests render with `copier.run_copy(..., vcs_ref="HEAD")`. In copier 9.11.3, `_vcs.py:191-211` copies uncommitted changes from a local HEAD and raises a `DirtyLocalWarning`. So a template edit is visible to the tests before it is committed. You do not need to commit before you go from red to green.
- There is no `graphify-out/` in this worktree, so skip the `graphify update .` step from CLAUDE.md.

## Decisions the spec left open

1. **Inline filter, no shared variable.** Write `{{ project_slug | replace('_', '-') }}` directly at each of the 6 places. Do not add a `{% set %}`, and do not add a hidden copier variable with `when: false`. This matches the 4 existing places that do the same. A hidden copier variable would also be saved in `.copier-answers.yml`, and that comes too close to the "no new question" assumption.
2. **The new test does its own light render, not the session `project` fixture.** The fixture runs `uv sync`, so the rendered tree has `.venv/` and `uv.lock`. The editable install's `*.dist-info/METADATA` repeats the `Project-URL` values. A grep over the whole tree (criterion 3) would then scan thousands of files and depend on what `uv` writes. Follow the pattern of `test_default_slug_is_valid_package_name`: call `copier.run_copy` into `tmp_path` with `COPIER_DATA` and no `uv sync`. Parametrize over `include_hexagonal` (`[True, False]`, ids `hexagonal` and `flat`) so both layouts are grepped. Each case takes a few seconds and needs no network.
3. **One test function covers criteria 1–3.** They are all facts about the same render. If one fails, the assertion message shows which.

## Steps

### Step 1: Write a failing test (red)

**File:** `tests/test_template.py`. Add the test after `test_docs_scaffold_renders`, or next to `test_default_slug_is_valid_package_name`. A suggested name is `test_github_urls_use_hyphenated_repo_name`. Add `import tomllib` to the imports.

The test should:
- Render as described in decision 2.
- Parse `pyproject.toml` with `tomllib`. Assert that `project.urls` equals `{"Homepage": "https://github.com/testuser/test-project", "Repository": "https://github.com/testuser/test-project"}`.
- Collect every `https://github.com/testuser/<repo>` in `README.md` with a regex such as `r"github\.com/testuser/([^/)\s\"]+)"`. Assert the list is not empty (4 matches are expected today). Assert every match equals `"test-project"`.
- Walk every file under the destination, skipping `.git/`. Read each one as text and skip any that fail to decode. Assert that no file contains `github.com/testuser/test_project`. The message should list the files that do.
- Have a docstring that says why: the repository name uses hyphens, the package name uses underscores, and the CI badge broke for `auto-shopper`. Match the docstring style of the tests around it.

**Verify:** `uv run pytest tests/test_template.py -k github_urls -v` fails on the current template, in both parametrized cases, on the pyproject assertion. Record that red run, because the spec requires the test to fail against the current template.

**Dependencies:** none.

### Step 2: Fix the template (green)

**Files:**
- `template/pyproject.toml.jinja:28-29`: replace `{{ project_slug }}` with `{{ project_slug | replace('_', '-') }}` in the `Homepage` and `Repository` URLs.
- `template/README.md.jinja:3`: same change in both URLs (badge image and link).
- `template/README.md.jinja:9`: same change in both URLs (link text and target).

Do not touch any other `project_slug` use (see the list above).

**Verify:**
- `uv run pytest tests/test_template.py -k github_urls -v` passes in both cases.
- `grep -rn 'github.com/{{ github_username }}/{{ project_slug }}}' template/` returns nothing.

**Dependencies:** Step 1, so that the test is red before the fix.

### Checkpoint: full suite

- Run `uv run pytest`. It is slow: 2 renders, `uv sync`, pre-commit and a Sphinx build. Pass `timeout` at about 600000 ms and run it in the foreground. All existing tests must stay green. This covers criterion 5: `test_template_renders` checks `src/test_project/`, `test_main_executes` imports `test_project.main`, and `test_make_lint` runs the import-linter contracts.
- `git diff --stat` shows only `tests/test_template.py`, `template/pyproject.toml.jinja` and `template/README.md.jinja`.

### Step 3: Commit

Make one commit for the test and one for the fix, or a single `fix:` commit. Both fit the history, which uses separate conventional commits per concern (see `bd38693` and `9515c31`). Suggested messages are `test: assert generated GitHub URLs use hyphenated repo name` and `fix: use hyphens in generated GitHub repository URLs`.

## Mapping to the acceptance criteria

| Criterion | Proved by |
|---|---|
| 1 (pyproject URLs) | Step 1, `tomllib` assertion |
| 2 (README URLs) | Step 1, regex over `README.md` |
| 3 (no underscore URL anywhere) | Step 1, file walk over the rendered tree |
| 4 (test exists and fails before the fix) | Step 1 red run, then Step 2 green run |
| 5 (underscores kept for imports) | Existing suite at the checkpoint, with no edits to those lines |

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| The file walk hits binary or odd files | Low | Skip `.git/` and skip files that fail to decode. The render without `uv sync` contains only template output and `.copier-answers.yml`. |
| The fix is applied too broadly and touches `packages` or import-linter lines | High: breaks imports and lint | Edit only the 3 listed lines. `test_make_lint`, `test_main_executes` and `test_generated_tests_pass` would catch a mistake. |
| The full suite needs network access for `uv sync` and pre-commit | Medium | Run Step 1 and Step 2 by themselves first, then the full suite. If the full suite fails only because of the network, report that as such. |
