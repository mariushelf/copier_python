## Spec

**What:** Derive the GitHub repository name in generated URLs from `project_slug` with underscores replaced by hyphens (`{{ project_slug | replace('_', '-') }}`), the same derivation the template already uses for the distribution name. Affected lines on `main`:

- `template/pyproject.toml.jinja:28-29` — `Homepage` and `Repository` URLs
- `template/README.md.jinja:3` — CI badge image and link
- `template/README.md.jinja:9` — "Original repository" link

**Why:** GitHub repositories are conventionally named with hyphens, while the Python package name needs underscores. Today a project with `project_slug = auto_shopper` gets URLs pointing at `github.com/<user>/auto_shopper`, while the repository is `auto-shopper`, so the CI badge and the project URLs are broken in every generated project with an underscore in its slug. Found while generating `mariushelf/auto-shopper`.

## Acceptance criteria
- [ ] In a project generated with `project_slug = "test_project"` and `github_username = "testuser"`, `pyproject.toml` has `Homepage` and `Repository` equal to `https://github.com/testuser/test-project`.
- [ ] In the same project, every `github.com/testuser/...` URL in `README.md` uses `test-project`, and none uses `test_project`.
- [ ] No other generated file contains `github.com/<github_username>/<project_slug>` with an underscore (checked by grep over the rendered project).
- [ ] A test in `tests/test_template.py` renders the template and asserts the two criteria above, and fails against the current template.
- [ ] Python import paths, the package directory under `src/`, and import-linter contracts still use `project_slug` with underscores (existing tests stay green).

## Assumptions
- No new copier question (such as `repo_name`) is added; the repository name is derived, as asked. A separate question can be added later if a repository name ever differs from the hyphenated slug.
- Already generated projects are not migrated; `copier update` picks the change up.
