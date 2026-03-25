# Plan: Fix Test Environment & Add CI/CD Pipeline

**Date:** 2026-03-25
**Status:** Implementation

## Problem Statement

The test suite is broken due to environment issues, and there is no CI/CD pipeline:

1. **Dev dependencies not installed in the project venv** — `pytest`, `pytest-asyncio`, and `pytest-cov` are missing from `.venv`. The globally installed `pytest` (Python 3.11) is being used instead of a project-local one (Python 3.12), so `import yaml`, `import exchange_calendars`, etc. fail at test collection time (18 of 22 test files fail to collect).
2. **pytest-asyncio configuration** — `asyncio_mode = "auto"` is unrecognized because the global pytest doesn't have `pytest-asyncio` installed.
3. **No CI/CD** — No `.github/workflows/` directory exists. Tests, linting, and frontend builds are never verified automatically.

## Root Cause Analysis

Running `uv run pytest` invokes the **globally installed** `/root/.local/bin/pytest` (Python 3.11 via uv tools) rather than a venv-local pytest. The project venv at `.venv/` has production deps installed but `.[dev]` extras were never installed, so there is no `.venv/bin/pytest`.

**Proof:**
- `uv run python -c "import yaml"` succeeds (uses `.venv` Python 3.12)
- `uv run pytest --co` fails with `ModuleNotFoundError: No module named 'yaml'` (pytest runs under Python 3.11)

## Implementation Plan

### Phase 1: Fix Test Environment

#### 1.1 Install dev dependencies in the project venv

```bash
uv pip install -e ".[dev]"
```

This installs `pytest`, `pytest-asyncio`, `pytest-cov`, and `ruff` into `.venv`, so `uv run pytest` resolves to the venv-local binary under Python 3.12.

#### 1.2 Fix pytest-asyncio configuration

Update `pyproject.toml` to use the current pytest-asyncio configuration format:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
pythonpath = ["src"]
```

Verify `asyncio_mode = "auto"` is recognized after installing `pytest-asyncio` in the venv. If the installed version requires it, add:

```toml
[tool.pytest-asyncio]
mode = "auto"
```

#### 1.3 Run full test suite and fix any test failures

```bash
uv run pytest -v
```

Address any actual test code issues (as opposed to environment issues) that surface once imports work.

### Phase 2: Add GitHub Actions CI/CD

#### 2.1 Create `.github/workflows/ci.yml`

**Trigger:** Push to `main` and all pull requests.

**Jobs:**

##### Job 1: `backend-tests`
- **Runs on:** `ubuntu-latest`
- **Python:** 3.12
- **Steps:**
  1. Checkout code
  2. Install uv
  3. Set up Python 3.12 via uv
  4. Install dependencies: `uv pip install -e ".[dev]"`
  5. Run linting: `uv run ruff check src/`
  6. Run tests with coverage: `uv run pytest -v --tb=short`

##### Job 2: `frontend-build`
- **Runs on:** `ubuntu-latest`
- **Node:** 20
- **Steps:**
  1. Checkout code
  2. Set up Node.js 20
  3. Install dependencies: `npm ci` (in `frontend/`)
  4. TypeScript check + build: `npm run build` (in `frontend/`)

#### 2.2 Workflow design decisions

- **No Docker build in CI** — Docker builds are slow and the Dockerfile is simple; the unit tests and lint provide sufficient signal.
- **No deployment step** — This is a trading bot that runs locally or on a private server; auto-deploy is out of scope.
- **Coverage reporting** — Start with console output; add coverage badges later if desired.
- **Concurrency** — Cancel in-progress runs on the same branch to save CI minutes.

## Files Changed

| File | Change |
|------|--------|
| `pyproject.toml` | Fix pytest-asyncio config if needed |
| `.github/workflows/ci.yml` | New — CI pipeline |
| `README.md` | Update roadmap to mark CI/CD as done |

## Success Criteria

1. `uv run pytest -v` passes all tests locally
2. `uv run ruff check src/` passes with no errors
3. GitHub Actions CI runs on push/PR and passes
4. Frontend `npm run build` succeeds in CI
