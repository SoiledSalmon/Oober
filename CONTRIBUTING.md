# Contributing to Oober

Thank you for your interest in contributing! This document describes the conventions used in this project.

## Branch Naming

Create all branches from `main` using one of the following prefixes:

| Prefix | Use case |
|--------|----------|
| `feature/<name>` | New features or enhancements |
| `fix/<name>` | Bug fixes |
| `docs/<name>` | Documentation-only changes |
| `refactor/<name>` | Code restructuring without behaviour change |
| `test/<name>` | Test additions or corrections |
| `chore/<name>` | Build, tooling, or dependency changes |

Examples:
```
feature/gnn-warm-start
fix/ilp-infeasibility-fallback
docs/readme-algorithm-section
```

## Commit Message Format

All commits must follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

```
<type>(<optional scope>): <short summary>

[optional body]
[optional footer]
```

Allowed types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`.

Examples:
```
feat(ilp): add adaptive delta relaxation for high-demand windows
fix(metrics): correct price-deviation buffer constant
docs(readme): update algorithm overview section
refactor(simulation): extract shared window-loop into helper
test(verification): add corridor price-stability assertion
chore: pin all dependencies to exact installed versions
```

## Pull Request Rules

- **No direct commits to `main`** — all changes must go through a pull request.
- **Branch must be up to date** with `main` before merging.
- **All tests must pass** before a PR can be merged:
  ```bash
  python tests/verify_backend.py
  pytest tests/test_backend_api.py
  pytest tests/test_metrics.py
  ```
- **At least one review** from another team member is required before merging.
- Keep PRs small and focused; one logical change per PR.

## Code Style

- Python files must be formatted to be **Black-compatible** (88-char line length, 4-space indent).
- Imports must follow **isort** order: stdlib → third-party → local.
- All public functions must have **Google-style docstrings** and **PEP 484 type annotations**.
- Constants must be `UPPER_SNAKE_CASE` in `oober/config.py` or in a `# Constants` block at the top of the module.

## Strict Constraint

> Do **not** modify any algorithmic logic, ILP formulation, matching decisions, or metric calculations without a team discussion and a dedicated PR that clearly documents the change in behaviour and updates the verification report.
