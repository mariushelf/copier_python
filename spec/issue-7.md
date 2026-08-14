Goal: allow easy activation of branch protection in github via rule set.

Normally, all targets that must be green must be hand-configured. This is flaky.

Instead, implement via CI gate so that rules don't need to list all possible targets.

See https://github.com/rodekruis/qualitative-feedback-analysis/blob/main/.github/workflows/ci.yaml for reference.

---

## Spec

**What:** Add one aggregate `ci-gate` job to **both** CI workflows — the shipped
`template/.github/workflows/cicd.yaml` (so every generated project has it) and this repo's own
`.github/workflows/ci.yaml` — restrict `push:` to `main` in both, add a drift test that the gate's
`needs` covers every other job, and note the required check name in the template README.

**Why:** A branch ruleset must name required status checks literally, so today it has to list every
matrix leg (`test (3.12)`, `test (3.13)`, …). That list silently rots the moment a matrix dimension
or job is added or renamed — the ruleset keeps passing while the new leg goes unchecked, which is
the flakiness this ticket is about. One unmatrixed aggregate job whose name never changes is the
only thing the ruleset has to require, and `needs:` moves the "everything must be green" list into
the workflow, next to the jobs it guards.

### The gate job

Identical in both files except its `needs:` list. Append to `jobs:` in each:

```yaml
  # Single aggregate check to require in the branch ruleset. It depends on
  # every other CI job and fails if any of them failed or was cancelled.
  # Requiring this one check (instead of each job or matrix leg) keeps the
  # ruleset stable when matrix dimensions change, and means a conditionally
  # skipped dependency never leaves a required check stuck "waiting" —
  # `skipped` is treated as acceptable here.
  ci-gate:
    if: always()
    needs: [lint, test]        # own ci.yaml has only `test`, so: needs: [test]
    runs-on: ubuntu-latest
    steps:
      - name: Verify no required job failed
        run: |
          results="${{ join(needs.*.result, ' ') }}"
          echo "Upstream job results: ${results}"
          for r in ${results}; do
            if [ "${r}" = "failure" ] || [ "${r}" = "cancelled" ]; then
              echo "::error::A required CI job did not pass (result: ${r})."
              exit 1
            fi
          done
          echo "All required CI jobs passed (or were acceptably skipped)."
```

`if: always()` is load-bearing: without it the job is skipped when a dependency fails, and a
skipped required check leaves the PR waiting forever instead of failing.

The job has **no `uses:` step** — not even `actions/checkout` — so it adds nothing to the
action-pinning surface of #4.

### Trigger change (both files)

Both workflows currently fire on `push:` (every branch) *and* `pull_request:`, which produces two
identical `ci-gate` check runs on any same-repo PR branch. Restrict push to `main`:

```yaml
on:
  push:
    branches: [main]
  pull_request:
  workflow_call:      # template/cicd.yaml only; the repo's own ci.yaml has none
```

Keep `pull_request:` — dropping it (as the qfa reference does) means fork PRs never run CI, so the
required check never appears and those PRs become unmergeable. Accepted cost: pushing a branch with
no PR open no longer runs CI.

### Drift test

The gate is only as good as its `needs:` list — add a job, forget the list, and the gate goes green
while the new job burns. Add to `tests/test_template.py`, parameterized over both workflow files on
disk (no rendering needed, see below), asserting: a `ci-gate` job exists, it carries `if: always()`,
and `set(needs) == set(jobs) - {"ci-gate"}`.

Two traps for the implementer:

- **PyYAML parses a bare `on:` key as boolean `True`** (YAML 1.1). Any assertion that inspects
  triggers must read `workflow[True] if True in workflow else workflow["on"]` — the same dance
  `tests/test_docker_packaging.py` uses in the aeloop repo.
- **`pyyaml` is currently only a transitive dependency** (via `copier`). Add it explicitly to the
  `dev` group in the root `pyproject.toml` rather than relying on the transitive.

The template workflow can be parsed straight from disk because `_templates_suffix: .jinja` means
only `.jinja` files are rendered — `cicd.yaml` is copied verbatim, which is why its existing
`${{ matrix.python-version }}` survives generation today. Do **not** rename it to `.jinja`; `${{ }}`
would then collide with Jinja.

### README note

Under *Development* in `template/README.md.jinja`, at most four lines naming `ci-gate` as the single
check to require in a branch ruleset. Per `AGENTS.md`, add the fact and nothing more — no
walkthrough of the GitHub settings UI.

## Acceptance criteria

- [ ] `template/.github/workflows/cicd.yaml` has a `ci-gate` job exactly as specified above, with
      `needs: [lint, test]`, `if: always()`, `runs-on: ubuntu-latest`, and no `uses:` step.
- [ ] `.github/workflows/ci.yaml` has the same job with `needs: [test]`.
- [ ] In both files `push:` is restricted to `branches: [main]`, `pull_request:` is retained, and the
      template's `workflow_call:` is retained.
- [ ] `tests/test_template.py` gains a test, parameterized over both workflow files, asserting the
      gate exists, carries `if: always()`, and that its `needs` equals every other job in that file.
- [ ] That test fails if a job is added to either workflow without being added to `needs` (verify by
      temporarily adding a dummy job locally, or by reasoning stated in the PR body).
- [ ] `pyyaml` is an explicit entry in the `dev` dependency group of the root `pyproject.toml`.
- [ ] `template/README.md.jinja` names `ci-gate` as the required check in ≤4 added lines under
      *Development*.
- [ ] `template/.github/workflows/cicd.yaml` still has no `.jinja` suffix and renders verbatim — the
      existing rendered-project tests still pass.
- [ ] `uv run pytest tests` is green.
- [ ] Commit uses the `ci:` prefix (as in 9b55106) and carries no AI attribution trailer.

## Activating the protection (repo admin, after merge)

The one check to require is `ci-gate`. Applies identically to this repo and to any generated project.

UI: *Settings → Rules → Rulesets → New branch ruleset* → target **Default branch** → tick **Require
status checks to pass** → add `ci-gate` → enforcement **Active**.

Or:

```bash
gh api -X POST repos/<owner>/<repo>/rulesets --input - <<'JSON'
{
  "name": "main",
  "target": "branch",
  "enforcement": "active",
  "conditions": { "ref_name": { "include": ["~DEFAULT_BRANCH"], "exclude": [] } },
  "rules": [
    { "type": "required_status_checks",
      "parameters": {
        "strict_required_status_checks_policy": false,
        "required_status_checks": [ { "context": "ci-gate" } ]
      } }
  ]
}
JSON
```

- Leave **Require branches to be up to date** (`strict_required_status_checks_policy`) off unless you
  want every merge to force a rebase and a full CI re-run on the next PR in the queue.
- Add the parameterless `deletion` and `non_fast_forward` rule types to also block branch deletion
  and force-pushes.
- Adding a CI job later needs no ruleset edit — that is the point of the gate.

## Out of scope

- Creating or enabling the branch ruleset itself — that is a repo-admin action in GitHub settings,
  not code. The section above is the recipe; this ticket only makes one stable check name available
  to require.
- Automating ruleset creation via `gh api` (GitHub does not import rulesets from a repo file).
- Renaming `cicd.yaml` → `ci.yaml` in the template (#8) and pinning actions to hashes (#4). Both are
  independent of this change; whichever lands first, the other rebases.

## Verification

```bash
uv run pytest tests            # needs network; renders a project and runs its lint/test/pre-commit
```

The gate's runtime behaviour can only be fully proven on GitHub: after merge, confirm a `ci-gate`
check run appears on a PR and that a ruleset can require it by that name.

No `Depends-on:` — nothing this spec builds on is unmerged.
