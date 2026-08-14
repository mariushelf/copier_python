"""Integration tests for the copier template."""

import re
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import copier

# A valid Python package / import name: lowercase letters, digits and
# underscores, not starting with a digit.
VALID_PACKAGE_NAME = re.compile(r"^[a-z_][a-z0-9_]*$")

TEMPLATE_ROOT = Path(__file__).resolve().parent.parent

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
    assert local == [("release.yaml", "./.github/workflows/cicd.yaml")]


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
