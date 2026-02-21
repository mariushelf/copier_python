"""Integration tests for the copier template."""

import subprocess
from pathlib import Path

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
