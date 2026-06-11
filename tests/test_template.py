"""Integration tests for the copier template."""

import re
import subprocess
from pathlib import Path

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


@pytest.fixture(scope="session")
def project_path(tmp_path_factory):
    """Generate a project from the template and install its dependencies."""
    dst = tmp_path_factory.mktemp("generated")
    copier.run_copy(
        src_path=str(TEMPLATE_ROOT),
        dst_path=str(dst),
        data=COPIER_DATA,
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
    return dst


def test_template_renders(project_path):
    """Verify that key files exist after rendering."""
    assert (project_path / "pyproject.toml").is_file()
    assert (project_path / "README.md").is_file()
    assert (project_path / "LICENSE").is_file()
    assert (project_path / "Makefile").is_file()
    assert (project_path / "src" / "test_project").is_dir()
    assert (project_path / "src" / "test_project" / "__init__.py").is_file()
    assert (project_path / "src" / "test_project" / "main.py").is_file()
    assert (project_path / "tests" / "test_test_project.py").is_file()


def test_docs_scaffold_renders(project_path):
    """Verify the documentation scaffold is present and placeholders resolved.

    The docs scaffold must ship complete so a generated project builds its
    Sphinx site immediately; this checks the key entry points exist and that
    the templated identity made it into conf.py and index.md.
    """
    source = project_path / "docs" / "source"
    assert (source / "conf.py").is_file()
    assert (source / "index.md").is_file()
    assert (source / "reference" / "python-api.md").is_file()
    # Meta-layer vendored verbatim into contributing/.
    assert (source / "contributing" / "voice.md").is_file()
    assert (source / "contributing" / "documentation_guide.md").is_file()
    # Drift-tripwire harness.
    assert (project_path / "tests" / "docs" / "test_doc_claims.py").is_file()

    # Copier placeholders must be resolved, not left verbatim.
    conf = (source / "conf.py").read_text(encoding="utf-8")
    assert 'PROJECT_NAME = "Test Project"' in conf
    assert 'DIST_NAME = "test-project"' in conf
    assert "{{" not in conf
    index = (source / "index.md").read_text(encoding="utf-8")
    assert index.startswith("# Test Project")
    assert "{{" not in index


def test_generated_tests_pass(project_path):
    """Run pytest in the generated project and verify it passes."""
    result = subprocess.run(
        ["uv", "run", "pytest"],
        cwd=project_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"pytest failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_main_executes(project_path):
    """Run the generated project's main module."""
    result = subprocess.run(
        ["uv", "run", "python", "-m", "test_project.main"],
        cwd=project_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"main module failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_make_lint(project_path):
    """Verify that `make lint` succeeds on the generated project."""
    result = subprocess.run(
        ["make", "lint"],
        cwd=project_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"make lint failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_make_test(project_path):
    """Verify that `make test` succeeds on the generated project."""
    result = subprocess.run(
        ["make", "test"],
        cwd=project_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"make test failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_pre_commit_passes(project_path):
    """Verify that pre-commit hooks pass on the generated project."""
    subprocess.run(
        ["git", "add", "."],
        cwd=project_path,
        check=True,
        capture_output=True,
    )
    result = subprocess.run(
        ["uvx", "pre-commit", "run", "--all-files"],
        cwd=project_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"pre-commit failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_make_docs_strict(project_path):
    """Verify `make docs-strict` builds the docs with zero warnings.

    The scaffold is contracted to pass `sphinx-build -W` immediately after
    generation, before any page is authored — broken cross-references,
    orphaned pages, or autodoc surprises must fail here, not silently ship.
    """
    result = subprocess.run(
        ["make", "docs-strict"],
        cwd=project_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"make docs-strict failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )


def test_make_test_docs(project_path):
    """Verify `make test-docs` passes on the freshly generated project.

    The drift-tripwire suite in tests/docs/ must be green out of the box; its
    structural checks (every page reachable from a toctree) guard the scaffold
    itself, independent of any project-specific claims added later.
    """
    result = subprocess.run(
        ["make", "test-docs"],
        cwd=project_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"make test-docs failed:\nstdout: {result.stdout}\nstderr: {result.stderr}"
    )


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
