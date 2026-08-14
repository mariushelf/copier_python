Pin github actions to version hashes so that they are more robust against supply chain attacks. E.g., instead of `astral-sh/setup-uv@v5`, use `astral-sh/setup-uv@0x123456`

Use the latest versions available.

Do it in both this repo, and in the cicd.yaml in the template.

---

## Spec

**What:** Replace every **third-party** `uses:` reference in all four workflow files with a full
40-character **commit SHA**, followed by a `# vX.Y.Z` comment naming the version that SHA is.
Bump each action to its latest major at the same time (see the pin table). Four files, 17
third-party call sites; the one *local* reusable-workflow ref is deliberately left alone.

**Why:** A mutable ref — `@v4`, `@v10`, and especially `@release/v1` — resolves at run time to
whatever the upstream tag or branch points at *today*. Anyone who can move that tag (upstream
maintainer, or an attacker who compromises the account) executes arbitrary code inside our CI
with our tokens. A commit SHA is immutable, so a compromised upstream cannot retroactively change
what our workflows run. This matters twice over here: once for this repo, and once for the
template, where every generated project inherits the refs verbatim.

The highest-value single fix is `pypa/gh-action-pypi-publish@release/v1` — that is a **branch**,
not even a tag, so it changes under us on every upstream push, and that step holds the PyPI
trusted-publishing identity of every project generated from this template.

### Pin table

Scope confirmed at triage: **all four workflow files**, not only `cicd.yaml`. `publish.yaml` and
`release.yaml` carry the two highest-privilege actions (PyPI publish rights; `contents: write` tag
pushes), so excluding them would leave the ticket's own rationale unserved.

| action | current ref | pin to | version |
|---|---|---|---|
| `actions/checkout` | `@v4` | `3d3c42e5aac5ba805825da76410c181273ba90b1` | `v7.0.1` |
| `actions/setup-python` | `@v5` | `5fda3b95a4ea91299a34e894583c3862153e4b97` | `v7.0.0` |
| `astral-sh/setup-uv` | `@v5` | `20cfd1bf945f4377ade1205e4dbc17946fc9a30d` | `v10.0.1` |
| `pypa/gh-action-pypi-publish` | `@release/v1` | `dc37677b2e1c63e2034f94d8a5b11f265b73ba33` | `v1.14.2` |
| `python-semantic-release/python-semantic-release` | `@v10` | `39dd2052f2ce8282a5d932c31d58a2ca06d2550e` | `v10.6.1` |

Written form, at every call site:

```yaml
- uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1
```

The trailing comment is not decoration — it is the only thing that makes the diff reviewable and
tells a future updater what version it is looking at.

### Call sites (17 third-party refs)

- `.github/workflows/ci.yaml` — 3 (checkout, setup-python, setup-uv)
- `template/.github/workflows/cicd.yaml` — 9 (the same three, in each of `lint`, `test`, `docs`)
- `template/.github/workflows/publish.yaml` — 1 (pypi-publish)
- `template/.github/workflows/release.yaml` — 4 (checkout, semantic-release, setup-python, setup-uv)

**Do not pin `release.yaml:28`,** `uses: ./.github/workflows/cicd.yaml`. That is a *local*
reusable workflow inside the generated repo; it is not a supply-chain surface and a SHA there is
meaningless (it would pin the generated project to a commit of its own that does not exist yet).

### Two traps that will silently produce a broken pin

1. **Annotated tags.** `pypa/gh-action-pypi-publish` and `python-semantic-release` publish
   *annotated* tags, so `gh api repos/OWNER/REPO/git/ref/tags/vX` returns the **tag object** SHA,
   not the commit. Pinning that SHA fails at run time with an unresolvable-action error. It must
   be dereferenced (`^{}`). The two SHAs in the table above are already the dereferenced commits.
2. **Do not invent or recall a SHA.** Every hash must be resolved from the API at implementation
   time. A hallucinated 40-hex string either fails the run or, far worse, silently pins something
   nobody reviewed — which is the exact class of failure this ticket exists to prevent.

Re-resolve all five at build time (upstream may have released since triage; update the table and
say so in the PR body if a version moved):

```bash
for r in actions/checkout actions/setup-python astral-sh/setup-uv \
         pypa/gh-action-pypi-publish python-semantic-release/python-semantic-release; do
  tag=$(gh api repos/$r/releases/latest --jq .tag_name)
  sha=$(gh api "repos/$r/git/ref/tags/$tag" --jq .object.sha)
  type=$(gh api "repos/$r/git/ref/tags/$tag" --jq .object.type)
  # dereference annotated tags to the commit they point at
  [ "$type" = "tag" ] && sha=$(gh api "repos/$r/git/tags/$sha" --jq .object.sha)
  echo "$r@$sha # $tag"
done
```

### Major-version bumps: what actually changes

Triage decision: pin at the **latest** major, per the ticket text — not at the current major's
tip. That makes this a `v4→v7` / `v5→v7` / `v5→v10` jump, so the breaking changes were checked
against upstream release notes rather than assumed. Findings:

- **checkout v5+** requires Actions runner ≥ `v2.327.1` (node24). GitHub-hosted `ubuntu-latest`
  satisfies this; self-hosted runners in generated projects may not.
- **checkout v7** blocks checking out fork PRs under `pull_request_target` / `workflow_run`.
  Neither trigger appears in any of these four files — no impact.
- **setup-python v6** is node24 (same runner floor). **v7** removed the `pip-install` input,
  which is not used here.
- **setup-uv v6** removed the `pyproject-file` / `uv-file` inputs, **v8** removed the old custom
  version-manifest format. None of the nine setup-uv steps pass *any* `with:` inputs, so both are
  no-ops for us.
- **setup-uv v9** changed `prune-cache` to default `false`, and `enable-cache` defaults to `auto`
  (caching **on** for hosted runners on `push` / `pull_request`). Consequence: **Actions cache
  usage will grow** — here and in every generated project. This is the one real operational cost
  of the bump; accepted and recorded, not mitigated.
- **setup-uv v10** makes `auto` *disable* the cache on `release`, tag-push, `pull_request_target`
  and `workflow_run` events. `release.yaml` runs on `workflow_dispatch` and `publish.yaml` uses no
  setup-uv, so nothing here changes behaviour.

If any of these bumps turns out to break CI, pin that one action at its **current** major's tip
SHA instead and note it in the PR body — hardening the ref is the goal; the version bump is the
part that may be traded away.

### Interaction with #7 and #8 — rebase, not dependency

Both edit the template CI workflow and both declare #4 independent of them:

- **#8** renames `template/.github/workflows/cicd.yaml` → `ci.yaml`. Apply this spec to the
  template CI workflow **under whatever name it carries at implementation time**; the file's
  content and its nine call sites are unaffected by the rename.
- **#7** adds a `ci-gate` job with **no `uses:` step**, so it adds no pins.

Whichever lands first, the other rebases. There is deliberately **no `Depends-on:`** line: every
file this spec touches exists on `origin/main` today (verified at `b55021b`).

## Acceptance criteria

- [ ] Every third-party `uses:` in `.github/workflows/ci.yaml`,
      `template/.github/workflows/{cicd,publish,release}.yaml` (the template CI workflow under its
      current name) references a full 40-hex commit SHA — 17 call sites, none left on a tag or
      branch ref.
- [ ] Each pinned ref carries a trailing `# vX.Y.Z` comment naming that SHA's version.
- [ ] `pypa/gh-action-pypi-publish` no longer references the `release/v1` **branch**.
- [ ] `release.yaml`'s `uses: ./.github/workflows/<template-ci>.yaml` local reusable-workflow ref
      is left unpinned and otherwise unchanged.
- [ ] Every SHA was resolved from the GitHub API during implementation (not recalled), and each
      one is a **commit** object — verified for the two annotated-tag actions with
      `gh api repos/OWNER/REPO/git/commits/<sha> --jq .sha` returning that same SHA.
- [ ] The PR body states the five `action@sha # version` pairs actually used, and flags any that
      differ from the table above because upstream released in the meantime.
- [ ] `git grep -nE 'uses:' -- .github template | grep -v '@[0-9a-f]\{40\}'` returns exactly one
      line: the local `./.github/workflows/…` reusable-workflow ref. (On `origin/main` at
      `b55021b` this same command returns 18 lines — 17 third-party refs plus that local one.)
- [ ] `uv run pytest tests` is green.
- [ ] This repo's own CI run on the PR passes on the newly pinned `checkout`/`setup-python`/
      `setup-uv` majors — i.e. the bump is proven, not just asserted.
- [ ] Commit uses a `ci:` prefix and carries no AI attribution trailer.

## Out of scope

- **Dependabot / Renovate config** to keep the pins fresh. Pinned SHAs never update on their own,
  so without an updater they freeze and miss upstream security fixes. Confirmed at triage as its
  own follow-up ticket for both this repo and the template — not this PR.
- Pinning tool versions outside GitHub Actions (pre-commit hook revs, `pipx install
  python-semantic-release` in `release.yaml`'s release-notes step, base images).
- Any change to what the workflows *do* — jobs, triggers, matrix, steps. Only `uses:` refs move,
  plus the incidental behaviour that the major bumps bring with them.
- Renaming `cicd.yaml` (#8) or adding the `ci-gate` job (#7).

## Verification

```bash
# every third-party ref is a 40-hex SHA; only the local reusable workflow may remain
git grep -nE 'uses:' -- .github template | grep -v '@[0-9a-f]\{40\}'

uv run pytest tests   # needs network; renders a project and runs its lint/test/pre-commit
```

Then confirm the PR's own CI run is green — that is the only real proof the major bumps hold.
