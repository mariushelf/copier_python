"""Integration tests for the copier template."""

import contextlib
import os
import re
import shutil
import signal
import socket
import subprocess
import time
import tomllib
from pathlib import Path
from types import SimpleNamespace

import plumbum
import pytest
import yaml

import copier

# A valid Python package / import name: lowercase letters, digits and
# underscores, not starting with a digit.
VALID_PACKAGE_NAME = re.compile(r"^[a-z_][a-z0-9_]*$")

TEMPLATE_ROOT = Path(__file__).resolve().parent.parent

# Both CI workflows carry the aggregate `ci-gate` job. They can be parsed
# straight from disk: `_templates_suffix: .jinja` means only `.jinja` files are
# rendered, so the template's ci.yaml is copied verbatim (which is also why
# its `${{ matrix.python-version }}` survives generation).
CI_WORKFLOWS = [
    TEMPLATE_ROOT / ".github" / "workflows" / "ci.yaml",
    TEMPLATE_ROOT / "template" / ".github" / "workflows" / "ci.yaml",
]


def _load_workflow(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _triggers(workflow: dict) -> dict:
    """Return a workflow's `on:` block.

    PyYAML follows YAML 1.1, where a bare ``on`` key is the boolean ``True``,
    so the block cannot simply be looked up by its name.
    """
    return workflow[True] if True in workflow else workflow["on"]

COPIER_DATA = {
    "author_name": "Test Author",
    "author_email": "test@example.com",
    "github_username": "testuser",
    "project_name": "Test Project",
    "project_slug": "test_project",
    "project_short_description": "A test project.",
    "version": "0.1.0",
    "license": "MIT",
}


@pytest.fixture(scope="session", params=[True, False], ids=["hexagonal", "flat"])
def project(tmp_path_factory, request):
    """Generate a project from the template and install its dependencies.

    Parametrised over the ``include_hexagonal`` answer so that both the
    hexagonal scaffolding and the plain layout are exercised end to end.
    """
    include_hexagonal = request.param
    dst = tmp_path_factory.mktemp("hex" if include_hexagonal else "flat")
    copier.run_copy(
        src_path=str(TEMPLATE_ROOT),
        dst_path=str(dst),
        data={**COPIER_DATA, "include_hexagonal": include_hexagonal},
        defaults=True,
        unsafe=True,
        vcs_ref="HEAD",
    )
    subprocess.run(
        ["uv", "sync"],
        cwd=dst,
        check=True,
        capture_output=True,
    )
    return SimpleNamespace(path=dst, hexagonal=include_hexagonal)


def test_template_renders(project):
    """Verify key files exist, and that hexagonal files appear only when asked."""
    assert (project.path / "pyproject.toml").is_file()
    assert (project.path / "README.md").is_file()
    assert (project.path / "LICENSE").is_file()
    assert (project.path / "Makefile").is_file()
    assert (project.path / "src" / "test_project").is_dir()
    assert (project.path / "src" / "test_project" / "__init__.py").is_file()
    assert (project.path / "src" / "test_project" / "main.py").is_file()
    assert (project.path / "tests" / "test_test_project.py").is_file()
    assert (project.path / "AGENTS.md").is_file()
    assert (project.path / "CLAUDE.md").is_file()
    # AGENTS.md is rendered from a .jinja source, so placeholders must resolve.
    assert "{{" not in (project.path / "AGENTS.md").read_text(encoding="utf-8")

    domain = project.path / "src" / "test_project" / "domain"
    example_test = project.path / "tests" / "test_example_notes.py"
    assert domain.is_dir() == project.hexagonal
    assert example_test.is_file() == project.hexagonal


def test_docs_scaffold_renders(project):
    """Verify the documentation scaffold is present and placeholders resolved.

    The docs scaffold must ship complete so a generated project builds its
    Sphinx site immediately; this checks the key entry points exist and that
    the templated identity made it into conf.py and index.md.
    """
    source = project.path / "docs" / "source"
    assert (source / "conf.py").is_file()
    assert (source / "index.md").is_file()
    assert (source / "reference" / "python-api.md").is_file()
    # Meta-layer vendored verbatim into contributing/.
    assert (source / "contributing" / "voice.md").is_file()
    assert (source / "contributing" / "documentation_guide.md").is_file()
    # Drift-tripwire harness.
    assert (project.path / "tests" / "docs" / "test_doc_claims.py").is_file()

    # Copier placeholders must be resolved, not left verbatim.
    conf = (source / "conf.py").read_text(encoding="utf-8")
    assert 'PROJECT_NAME = "Test Project"' in conf
    assert 'DIST_NAME = "test-project"' in conf
    assert "{{" not in conf
    index = (source / "index.md").read_text(encoding="utf-8")
    assert index.startswith("# Test Project")
    assert "{{" not in index


def test_generated_tests_pass(project):
    """Run pytest in the generated project and verify it passes."""
    result = subprocess.run(
        ["uv", "run", "pytest"],
        cwd=project.path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"pytest failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_main_executes(project):
    """Run the generated project's main module."""
    result = subprocess.run(
        ["uv", "run", "python", "-m", "test_project.main"],
        cwd=project.path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"main module failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_make_lint(project):
    """Verify that `make lint` succeeds on the generated project."""
    result = subprocess.run(
        ["make", "lint"],
        cwd=project.path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"make lint failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_make_test(project):
    """Verify that `make test` succeeds on the generated project."""
    result = subprocess.run(
        ["make", "test"],
        cwd=project.path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"make test failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_pre_commit_passes(project):
    """Verify that pre-commit hooks pass on the generated project."""
    subprocess.run(
        ["git", "add", "."],
        cwd=project.path,
        check=True,
        capture_output=True,
    )
    result = subprocess.run(
        ["uvx", "pre-commit", "run", "--all-files"],
        cwd=project.path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"pre-commit failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_make_docs_strict(project):
    """Verify `make docs-strict` builds the docs with zero warnings.

    The scaffold is contracted to pass `sphinx-build -W` immediately after
    generation, before any page is authored — broken cross-references,
    orphaned pages, or autodoc surprises must fail here, not silently ship.
    """
    result = subprocess.run(
        ["make", "docs-strict"],
        cwd=project.path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"make docs-strict failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_make_test_docs(project):
    """Verify `make test-docs` passes on the freshly generated project.

    The drift-tripwire suite in tests/docs/ must be green out of the box; its
    structural checks (every page reachable from a toctree) guard the scaffold
    itself, independent of any project-specific claims added later.
    """
    result = subprocess.run(
        ["make", "test-docs"],
        cwd=project.path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"make test-docs failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )


# A `uses:` step reference, capturing the ref and any trailing comment.
USES_LINE = re.compile(r"^\s*(?:-\s*)?uses:\s*(?P<ref>\S+)\s*(?:#\s*(?P<comment>.*))?$")
# A third-party action pinned to a full 40-character commit SHA.
SHA_PINNED_REF = re.compile(r"^[^@]+@[0-9a-f]{40}$")
# The version the pinned SHA corresponds to, e.g. "v7.0.1".
VERSION_COMMENT = re.compile(r"^v\d+\.\d+\.\d+")


def _uses_refs(workflow_dir):
    """Yield ``(path, lineno, ref, comment)`` for every ``uses:`` in a directory."""
    for path in sorted(Path(workflow_dir).glob("*.yaml")):
        for lineno, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            match = USES_LINE.match(line)
            if match:
                yield path, lineno, match["ref"], match["comment"]


def assert_actions_are_sha_pinned(workflow_dir):
    """Assert every third-party action in ``workflow_dir`` is pinned to a commit SHA.

    A mutable ref (``@v4``, or worse a branch like ``@release/v1``) resolves at run
    time to whatever upstream points at today, so anyone who can move that tag runs
    arbitrary code in our CI with our tokens. Only an immutable 40-hex commit SHA
    closes that hole. Local reusable workflows (``./.github/...``) are exempt: they
    live in the same repo and are not a supply-chain surface.
    """
    refs = list(_uses_refs(workflow_dir))
    assert refs, f"no `uses:` steps found under {workflow_dir}"

    unpinned = [
        f"{path.name}:{lineno}: {ref}"
        for path, lineno, ref, _ in refs
        if not ref.startswith("./") and not SHA_PINNED_REF.match(ref)
    ]
    assert not unpinned, "actions not pinned to a 40-hex commit SHA:\n" + "\n".join(
        unpinned
    )

    # The trailing version comment is what makes the pin reviewable and tells a
    # future updater which release the opaque SHA actually is.
    uncommented = [
        f"{path.name}:{lineno}: {ref}"
        for path, lineno, ref, comment in refs
        if not ref.startswith("./")
        and not (comment and VERSION_COMMENT.match(comment.strip()))
    ]
    assert not uncommented, (
        "pinned actions missing a `# vX.Y.Z` version comment:\n" + "\n".join(uncommented)
    )


def test_own_workflows_pin_actions_to_sha():
    """This repo's own CI must pin its actions, not just the template's."""
    assert_actions_are_sha_pinned(TEMPLATE_ROOT / ".github" / "workflows")


def test_generated_workflows_pin_actions_to_sha(project):
    """Every generated project inherits the template's refs, so they must be pinned.

    Asserted against the *rendered* project rather than the template source, so the
    pins are proven to survive copier rendering into every downstream repo.
    """
    assert_actions_are_sha_pinned(project.path / ".github" / "workflows")


def test_generated_release_keeps_local_workflow_ref_unpinned(project):
    """The local reusable-workflow ref must stay a path, not become a SHA.

    ``uses: ./.github/workflows/...`` refers to a file inside the generated repo
    itself. A SHA there would pin the project to one of its own commits that does
    not exist yet — so this ref is deliberately excluded from the pinning sweep.
    """
    local = [
        (path.name, ref)
        for path, _, ref, _ in _uses_refs(project.path / ".github" / "workflows")
        if ref.startswith("./")
    ]
    assert local == [("release.yaml", "./.github/workflows/ci.yaml")]


def test_default_slug_is_valid_package_name(tmp_path):
    """The auto-derived project_slug must be a valid Python package name.

    The default project_name ("<author>'s new project") contains an
    apostrophe, which a blocklist of character replacements would leak into the
    slug (e.g. ``joe_doe's_new_project``) — an invalid package name that breaks
    ``uv`` and imports. We render with the apostrophe-bearing defaults and no
    explicit project_slug, then assert the derived slug and package directory
    are valid.
    """
    dst = tmp_path / "generated"
    copier.run_copy(
        src_path=str(TEMPLATE_ROOT),
        dst_path=str(dst),
        data={"author_name": "Joe Doe", "author_email": "joe@example.com"},
        defaults=True,
        unsafe=True,
        vcs_ref="HEAD",
    )
    package_dirs = [p.name for p in (dst / "src").iterdir() if p.is_dir()]
    assert package_dirs, "no package directory was rendered under src/"
    slug = package_dirs[0]
    assert VALID_PACKAGE_NAME.match(slug), f"invalid package name: {slug!r}"
    assert slug.isidentifier(), f"slug is not a valid identifier: {slug!r}"


@pytest.mark.parametrize("include_hexagonal", [True, False], ids=["hexagonal", "flat"])
def test_github_urls_use_hyphenated_repo_name(tmp_path, include_hexagonal):
    """Generated GitHub URLs name the repository with hyphens, not underscores.

    GitHub repositories are conventionally hyphenated while the Python package
    needs underscores. Building the URL from ``project_slug`` unchanged broke
    the CI badge and project URLs for e.g. ``auto-shopper``. We render without
    ``uv sync`` (which would add ``.venv/`` metadata that repeats the URLs) and
    check pyproject.toml, README.md, and every other rendered file.
    """
    dst = tmp_path / "generated"
    copier.run_copy(
        src_path=str(TEMPLATE_ROOT),
        dst_path=str(dst),
        data={**COPIER_DATA, "include_hexagonal": include_hexagonal},
        defaults=True,
        unsafe=True,
        vcs_ref="HEAD",
    )
    repo_url = "https://github.com/testuser/test-project"

    pyproject = tomllib.loads((dst / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["urls"] == {
        "Homepage": repo_url,
        "Repository": repo_url,
    }

    readme = (dst / "README.md").read_text(encoding="utf-8")
    repos = re.findall(r"github\.com/testuser/([^/)\]\s\"]+)", readme)
    assert repos, "README.md has no github.com/testuser URL"
    assert set(repos) == {"test-project"}, f"README repo names: {repos}"

    offenders = []
    for path in dst.rglob("*"):
        if not path.is_file() or ".git" in path.relative_to(dst).parts[:1]:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        if "github.com/testuser/test_project" in text:
            offenders.append(str(path.relative_to(dst)))
    assert not offenders, f"underscored repo URL found in: {offenders}"


@pytest.mark.parametrize("workflow_path", CI_WORKFLOWS, ids=lambda p: p.name)
def test_ci_gate_covers_every_job(workflow_path):
    """The `ci-gate` job must depend on every other job in its workflow.

    A branch ruleset names required checks literally, so it requires only
    `ci-gate` and the workflow itself carries the "everything must be green"
    list. That indirection is only safe while `needs:` stays complete — add a
    job (or a whole matrix) and forget the list, and the gate goes green while
    the new job burns. This test is the tripwire for exactly that drift.
    """
    workflow = _load_workflow(workflow_path)
    jobs = workflow["jobs"]

    assert "ci-gate" in jobs, f"{workflow_path.name} has no ci-gate job"
    gate = jobs["ci-gate"]

    # Without `if: always()` the gate is skipped when a dependency fails, and a
    # skipped required check leaves the PR waiting forever instead of failing.
    assert gate.get("if") == "always()"
    assert set(gate["needs"]) == set(jobs) - {"ci-gate"}


@pytest.mark.parametrize("workflow_path", CI_WORKFLOWS, ids=lambda p: p.name)
def test_ci_workflow_triggers(workflow_path):
    """Push runs only on main; pull_request stays so fork PRs still get a gate.

    Firing on every push *and* on pull_request produces two identical `ci-gate`
    check runs for a same-repo PR branch. Dropping `pull_request:` instead
    would mean fork PRs never run CI, so the required check never appears and
    those PRs cannot be merged.
    """
    triggers = _triggers(_load_workflow(workflow_path))
    assert triggers["push"] == {"branches": ["main"]}
    assert "pull_request" in triggers


def _assert_dependabot_config(path: Path, actions_dirs=("/",)) -> None:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert config["version"] == 2
    updates = {u["package-ecosystem"]: u for u in config["updates"]}
    assert set(updates) == {"uv", "github-actions"}
    for update in updates.values():
        dirs = update.get("directories") or [update["directory"]]
        expected = actions_dirs if update["package-ecosystem"] == "github-actions" else ("/",)
        assert dirs == list(expected)
        assert update["schedule"]["interval"] == "weekly"
        assert update["cooldown"]["default-days"] == 7


def test_own_dependabot_config():
    # The repo's own Actions live in "/" and the generated ones in "/template/.github/workflows".
    _assert_dependabot_config(
        TEMPLATE_ROOT / ".github" / "dependabot.yml",
        ("/", "/template/.github/workflows"),
    )


def test_generated_dependabot_config(project):
    _assert_dependabot_config(project.path / ".github" / "dependabot.yml")


def test_invalid_project_slug_is_rejected(tmp_path):
    """An explicitly supplied invalid project_slug must fail validation.

    The validator guards against bad user input regardless of the default, so a
    slug containing an apostrophe (or any non-identifier character) must abort
    rendering rather than producing a broken project.
    """
    dst = tmp_path / "generated"
    with pytest.raises(ValueError, match="project_slug"):
        copier.run_copy(
            src_path=str(TEMPLATE_ROOT),
            dst_path=str(dst),
            data={**COPIER_DATA, "project_slug": "joe_doe's_project"},
            defaults=True,
            unsafe=True,
            vcs_ref="HEAD",
        )


# --- graphify -------------------------------------------------------------

GRAPHIFY_STAGES = ["post-commit", "post-checkout", "post-merge", "post-rewrite"]


def _graphify_hook(project_path: Path) -> dict:
    config = yaml.safe_load(
        (project_path / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    )
    hooks = [h for r in config["repos"] for h in r["hooks"] if h["id"] == "graphify"]
    assert len(hooks) == 1
    return hooks[0]


def test_graphify_is_configured(project):
    """The rendered project wires graphify into pre-commit, deps and docs."""
    config = yaml.safe_load(
        (project.path / ".pre-commit-config.yaml").read_text(encoding="utf-8")
    )
    assert set(config["default_install_hook_types"]) == {"pre-commit", *GRAPHIFY_STAGES}

    assert config["default_stages"] == ["pre-commit"]

    hook = _graphify_hook(project.path)
    assert hook["stages"] == GRAPHIFY_STAGES
    assert hook["always_run"] is True
    assert hook["pass_filenames"] is False
    assert hook["language"] == "system"

    script = project.path / "scripts" / "graphify-update.sh"
    assert script.stat().st_mode & 0o111, "hook script must be executable"
    body = script.read_text(encoding="utf-8")
    assert "GRAPHIFY_NO_AUTO_REFRESH=1" in body
    assert "uv run --frozen graphify update ." in body

    pyproject = tomllib.loads((project.path / "pyproject.toml").read_text("utf-8"))
    assert any(
        d.startswith("graphifyy>=") for d in pyproject["dependency-groups"]["dev"]
    )
    gitignore = (project.path / ".gitignore").read_text(encoding="utf-8")
    assert "graphify-out/" in gitignore.splitlines()
    assert not (project.path / ".gitattributes").exists()
    agents = (project.path / "AGENTS.md").read_text(encoding="utf-8")
    assert "## Code Graph" in agents
    assert "graphify query" in agents


def _script(project_path: Path) -> str:
    return str(project_path / "scripts" / "graphify-update.sh")


def _fake_uv(bin_dir: Path, body: str) -> dict:
    bin_dir.mkdir(exist_ok=True)
    fake = bin_dir / "uv"
    fake.write_text(f"#!/bin/sh\n{body}\n", encoding="utf-8")
    fake.chmod(0o755)
    return {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}


def test_graphify_script_exits_zero_without_tools(project, tmp_path):
    """With neither uv nor graphify on PATH the script is a silent no-op."""
    result = subprocess.run(
        [shutil.which("sh"), _script(project.path)],
        cwd=tmp_path,
        env={"PATH": str(tmp_path)},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert not (tmp_path / "graphify-out").exists()


def test_graphify_script_skips_without_lockfile(project, tmp_path):
    """No uv.lock: log why, exit 0, and do not create a lock."""
    env = _fake_uv(tmp_path / "bin", "echo built >> built.txt")
    result = subprocess.run(
        ["sh", _script(project.path)],
        cwd=tmp_path,
        env={**env, "GRAPHIFY_UPDATE_FOREGROUND": "1"},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "no uv.lock" in (tmp_path / "graphify-out" / "update.log").read_text()
    assert not (tmp_path / "uv.lock").exists()
    assert not (tmp_path / "built.txt").exists()


def test_graphify_script_survives_failing_build(project, tmp_path):
    """A failing build is logged and still exits 0, releasing the lock."""
    (tmp_path / "uv.lock").write_text("")
    env = _fake_uv(tmp_path / "bin", "echo boom; exit 3")
    result = subprocess.run(
        ["sh", _script(project.path)],
        cwd=tmp_path,
        env={**env, "GRAPHIFY_UPDATE_FOREGROUND": "1"},
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    log = (tmp_path / "graphify-out" / "update.log").read_text()
    assert "boom" in log
    assert "update failed" in log
    assert not (tmp_path / "graphify-out" / ".lock").exists()


def test_graphify_script_coalesces_triggers(project, tmp_path):
    """A trigger during a running build makes the holder build once more."""
    (tmp_path / "uv.lock").write_text("")
    counter = tmp_path / "builds.txt"
    env = {
        **_fake_uv(tmp_path / "bin", f"echo x >> {counter}; sleep 2"),
        "GRAPHIFY_UPDATE_FOREGROUND": "1",
    }
    first = subprocess.Popen(
        ["sh", _script(project.path)], cwd=tmp_path, env=env
    )
    deadline = time.monotonic() + 30
    while not counter.exists() and time.monotonic() < deadline:
        time.sleep(0.1)
    # Second and third triggers arrive mid-build: no extra parallel build.
    for _ in range(2):
        second = subprocess.run(["sh", _script(project.path)], cwd=tmp_path, env=env)
        assert second.returncode == 0
    assert first.wait(timeout=60) == 0
    assert counter.read_text().count("x") == 2
    assert not (tmp_path / "graphify-out" / ".lock").exists()


def test_graphify_script_recovers_stale_lock(project, tmp_path):
    """A lock whose holder is dead does not block builds forever."""
    (tmp_path / "uv.lock").write_text("")
    lock = tmp_path / "graphify-out" / ".lock"
    lock.mkdir(parents=True)
    dead = subprocess.Popen(["true"])
    dead.wait()
    (lock / "pid").write_text(str(dead.pid))
    env = _fake_uv(tmp_path / "bin", f"echo x >> {tmp_path / 'builds.txt'}")
    subprocess.run(
        ["sh", _script(project.path)],
        cwd=tmp_path,
        env={**env, "GRAPHIFY_UPDATE_FOREGROUND": "1"},
        check=True,
    )
    assert (tmp_path / "builds.txt").read_text().count("x") == 1


def test_graphify_script_does_not_steal_live_lock(project, tmp_path):
    """A live holder keeps its lock even when the lock directory is old."""
    (tmp_path / "uv.lock").write_text("")
    lock = tmp_path / "graphify-out" / ".lock"
    lock.mkdir(parents=True)
    holder = subprocess.Popen(["sleep", "30"])
    try:
        (lock / "pid").write_text(str(holder.pid))
        old = time.time() - 3600
        os.utime(lock, (old, old))
        env = _fake_uv(tmp_path / "bin", f"echo x >> {tmp_path / 'builds.txt'}")
        subprocess.run(
            ["sh", _script(project.path)],
            cwd=tmp_path,
            env={**env, "GRAPHIFY_UPDATE_FOREGROUND": "1"},
            check=True,
        )
        assert not (tmp_path / "builds.txt").exists()
        assert (lock / "pid").read_text() == str(holder.pid)
    finally:
        holder.kill()
        holder.wait()


def test_generation_survives_failing_uv_lock(tmp_path):
    """The best-effort `uv lock` task must not abort project generation."""
    env = _fake_uv(tmp_path / "bin", "echo offline >&2; exit 2")
    dst = tmp_path / "proj"
    # copier runs tasks with plumbum's environment, not os.environ.
    with plumbum.local.env(PATH=env["PATH"]):
        copier.run_copy(
            src_path=str(TEMPLATE_ROOT),
            dst_path=str(dst),
            data={**COPIER_DATA, "include_hexagonal": False},
            defaults=True,
            unsafe=True,
            vcs_ref="HEAD",
        )
    assert (dst / "pyproject.toml").is_file()
    assert not (dst / "uv.lock").exists()


def _online() -> bool:
    try:
        socket.create_connection(("pypi.org", 443), timeout=5).close()
    except OSError:
        return False
    return True


def _wait_for(path: Path, timeout: float = 90.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.is_file():
            return True
        time.sleep(1)
    return path.is_file()


def _wait_idle(*roots: Path, timeout: float = 60.0) -> None:
    """Wait for background builds to finish so tmp_path can be removed."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not any((r / "graphify-out" / ".lock").exists() for r in roots):
            return
        time.sleep(1)
    for r in roots:
        pid_file = r / "graphify-out" / ".lock" / "pid"
        if pid_file.exists():
            with contextlib.suppress(OSError, ValueError):
                os.kill(int(pid_file.read_text()), signal.SIGTERM)


@pytest.mark.skipif(shutil.which("uv") is None, reason="uv not available")
@pytest.mark.skipif(not _online(), reason="network not available")
def test_graphify_hooks_build_graph_per_worktree(tmp_path):
    """Commit and `git worktree add` each produce their own graphify-out/.

    Needs network access (installs the project's dev dependencies, graphify
    included). Exercises the real post-commit and post-checkout hooks, and that
    a checkout of a commit without a pre-commit config still succeeds.
    """
    dst = tmp_path / "proj"
    worktree = tmp_path / "wt"
    copier.run_copy(
        src_path=str(TEMPLATE_ROOT),
        dst_path=str(dst),
        data={**COPIER_DATA, "include_hexagonal": False},
        defaults=True,
        unsafe=True,
        vcs_ref="HEAD",
    )
    assert (dst / "uv.lock").is_file(), "copier _tasks should create uv.lock"

    def run(*cmd, cwd=dst):
        return subprocess.run(cmd, cwd=cwd, check=True, capture_output=True, text=True)

    try:
        run("uv", "sync")
        run("git", "config", "user.email", "t@example.com")
        run("git", "config", "user.name", "T")
        run("uv", "run", "pre-commit", "install", "--allow-missing-config")
        for name in ["post-commit", "post-checkout", "post-merge", "post-rewrite"]:
            assert (dst / ".git" / "hooks" / name).is_file(), f"{name} not installed"

        run("git", "add", ".")
        # --no-verify skips the pre-commit stage only; post-commit still fires.
        run("git", "commit", "--no-verify", "-m", "chore: initial")
        assert _wait_for(dst / "graphify-out" / "graph.json"), "no graph after commit"

        run("git", "worktree", "add", "-b", "other", str(worktree))
        assert _wait_for(worktree / "graphify-out" / "graph.json"), (
            "post-checkout did not build a graph in the new worktree"
        )

        # A commit without .pre-commit-config.yaml must stay checkout-able.
        run("git", "checkout", "-q", "--orphan", "bare")
        run("git", "rm", "-rfq", ".")
        run("git", "commit", "-q", "--allow-empty", "--no-verify", "-m", "bare")
        run("git", "checkout", "-q", "main")
        run("git", "checkout", "-q", "bare")
    finally:
        _wait_idle(dst, worktree)
