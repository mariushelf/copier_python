"""Integration tests for the copier template."""

import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

import copier

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
