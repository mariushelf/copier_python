# Project Guidelines

## Package Management

Use `uv` for all dependency management (not `pip`). Examples:
- `uv add <package>` to add a dependency
- `uv pip install -e .` to install the project
- `uv run <command>` to run commands in the project environment

## Git Conventions

Use semantic commit messages:

- `feat:` new feature
- `fix:` bug fix (something was actually broken)
- `docs:` documentation changes
- `style:` formatting, missing semicolons, etc. (no code change)
- `refactor:` code restructuring without changing behavior
- `test:` adding or updating tests
- `chore:` maintenance tasks, dependency updates, CI config, cleanup of things that work but are unnecessary

Do NOT add "Co-Authored-By" or any AI attribution trailers to commit messages.

## Architecture

This project follows a hexagonal (ports-and-adapters) architecture. The
dependency rule points inward: outer layers may import inner layers, never the
reverse.

- **Flow:** driving adapter (`main.py`) → application service (use case) →
  driven adapters (behind ports) → result.
- Driven adapters (databases, HTTP clients, external APIs, ...) sit behind ports
  declared in `{{ project_slug }}.domain.ports`, so implementations can be
  swapped without touching the core.
- **Every class that implements a port must explicitly inherit from it** — this
  applies to production adapters *and* test doubles (e.g.
  `class InMemoryNoteRepository(NoteRepository):`,
  `class FakeNoteRepository(NoteRepository):`). Although Python `Protocol`s
  support structural typing without inheritance, the explicit base class makes
  the port↔adapter relationship discoverable in IDEs ("go to definition" jumps
  to the contract) and signals intent to readers. Skipping the inheritance is
  reserved for genuinely ad-hoc cases (e.g. a one-line
  `unittest.mock.MagicMock(spec=NoteRepository)`, which enforces conformance via
  `spec=`) and should be the exception, not the default.

Layer rules are enforced by `import-linter` contracts in `pyproject.toml`
(`make lint` runs them). The package layout is:

- `{{ project_slug }}.domain` — entities, value objects, errors, and driven
  ports (the inner core; no third-party infrastructure imports).
- `{{ project_slug }}.services` — application services / use cases (depend only
  on `domain`).
- `{{ project_slug }}.adapters` — driven adapter implementations of the ports
  declared in `{{ project_slug }}.domain.ports`.
- `{{ project_slug }}.main` — the composition root and driving adapter: wires
  concrete adapters into the services at startup. As the composition root it is
  the one module allowed to import from every layer.

The `domain`, `services`, and `adapters` packages ship with a small,
clearly-marked example slice (a `Note` entity, a `NoteRepository` port, an
in-memory adapter, and a `NoteService`). Search for `# --- example` and delete
those blocks once you start modelling your own domain.

## Testing & Linting

- `make test` runs the test suite.
- `make lint` runs ruff, the `ty` type checker, and the `import-linter`
  architecture contracts.
