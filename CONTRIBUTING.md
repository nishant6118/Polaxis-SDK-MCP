# Contributing to polaxis-sdk

Thank you for helping make AI agent governance better. This guide covers everything you need to get started.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How to contribute](#how-to-contribute)
- [Development setup](#development-setup)
- [Project structure](#project-structure)
- [Running tests](#running-tests)
- [Submitting a pull request](#submitting-a-pull-request)
- [Reporting bugs](#reporting-bugs)
- [Requesting features](#requesting-features)
- [SDK design principles](#sdk-design-principles)
- [Release process](#release-process)

---

## Code of Conduct

Be respectful, constructive, and patient. We welcome contributors at all experience levels.

---

## How to contribute

We welcome:

| Type | Details |
|---|---|
| **Bug fixes** | Incorrect behaviour, wrong error messages, broken edge cases |
| **New framework integrations** | LangGraph, CrewAI, AutoGen, PydanticAI, Haystack, etc. |
| **New examples** | Real-world usage patterns that aren't already covered |
| **Tests** | More coverage is always welcome |
| **Documentation** | Typos, unclear explanations, missing docstrings |
| **TypeScript SDK** | A TS/JS port of the Python SDK |
| **Performance** | Reducing latency in the evaluate() hot path |

If you're unsure whether your idea fits, open an issue first.

---

## Development setup

**Requirements:** Python 3.10+, Git

```bash
# 1. Fork and clone
git clone https://github.com/YOUR_USERNAME/polaxis-sdk.git
cd polaxis-sdk

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 3. Install in editable mode with dev dependencies
pip install -e ".[dev,mcp]"

# 4. Verify everything works
pytest tests/ -v
```

**Environment variables for integration tests:**

```bash
# Only needed for tests that hit the real API
export POLAXIS_API_KEY=ag_test_...
```

Unit tests mock all HTTP calls and do **not** require an API key.

---

## Project structure

```
polaxis-sdk/
├── polaxis/
│   ├── __init__.py        # Public exports
│   ├── client.py          # Polaxis and PolaxisSync classes
│   ├── models.py          # EvaluateResult, ApprovalStatus
│   └── exceptions.py      # All custom exceptions
├── polaxis_mcp/
│   ├── __init__.py
│   └── server.py          # MCP proxy server
├── examples/
│   ├── basic_usage.py
│   ├── openai_tools_example.py
│   ├── langchain_example.py
│   └── mcp_config.json
├── tests/
│   ├── __init__.py
│   └── test_client.py
├── pyproject.toml
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

### Adding a new framework example

1. Create `examples/<framework>_example.py`
2. The file must:
   - Work without any hardcoded API keys (env vars only)
   - Include a top-level docstring explaining what it demonstrates
   - Be runnable as `python examples/<framework>_example.py`
3. Add it to the Examples table in `README.md`

---

## Running tests

```bash
# All tests
pytest tests/ -v

# Single test file
pytest tests/test_client.py -v

# With coverage
pytest tests/ --cov=polaxis --cov-report=term-missing

# Skip slow integration tests
pytest tests/ -m "not integration"
```

Tests use `unittest.mock` to avoid real HTTP calls. If you add a test that calls the live API, mark it:

```python
@pytest.mark.integration
async def test_real_evaluate():
    ...
```

---

## Submitting a pull request

1. **Create a branch** from `main`:
   ```bash
   git checkout -b feat/langraph-integration
   ```

2. **Make your changes.** Keep commits small and focused.

3. **Add or update tests.** All new code paths should be covered.

4. **Check for secrets.** Run:
   ```bash
   grep -rn "ag_prod_\|sk-\|Bearer\|password\|secret" . --include="*.py" --include="*.json" --include="*.toml"
   ```
   No real credentials should ever be committed.

5. **Run the full test suite** and confirm it passes:
   ```bash
   pytest tests/ -v
   ```

6. **Push and open a PR:**
   ```bash
   git push origin feat/langraph-integration
   ```
   Then open a pull request on GitHub against `main`.

7. **PR checklist:**
   - [ ] Tests pass locally
   - [ ] No secrets or API keys in any file
   - [ ] Docstrings added for new public functions/classes
   - [ ] Example added or updated if relevant
   - [ ] `CHANGELOG.md` entry added under `[Unreleased]`

---

## Reporting bugs

Open a GitHub Issue and include:

- Python version (`python --version`)
- SDK version (`pip show polaxis`)
- Minimal reproduction code (sanitize any API keys!)
- Actual vs. expected behaviour
- Full traceback if applicable

---

## Requesting features

Open a GitHub Issue with the **feature request** label. Describe:

- The use case / problem you're solving
- The API you'd want (pseudocode is fine)
- Any alternatives you've considered

---

## SDK design principles

When making changes, keep these in mind:

1. **Zero secrets by default.** The API key is always passed by the caller at runtime, never read from files or embedded.

2. **Async-first.** `Polaxis` is async. `PolaxisSync` is a thin wrapper that uses `asyncio.run()`. Avoid adding synchronous-only APIs.

3. **Raise, don't return errors.** When `raise_on_block=True` (the default), raise typed exceptions rather than returning result objects that callers might forget to check.

4. **Keep the evaluate() hot path fast.** One HTTP request, no retries, no caching. Latency budget is <5ms network-excluded.

5. **No hard dependencies beyond `httpx`.** MCP support is optional (`pip install polaxis[mcp]`). Framework integrations belong in examples, not in the core package.

6. **Type everything.** All public functions and methods must have complete type annotations.

---

## Release process

_(For maintainers)_

1. Update version in `pyproject.toml` and `polaxis/__init__.py`
2. Update `CHANGELOG.md` — move `[Unreleased]` to the new version + date
3. Commit: `git commit -m "chore: release v0.x.0"`
4. Tag: `git tag v0.x.0 && git push --tags`
5. GitHub Actions publishes to PyPI automatically on tag push

---

Questions? Open an issue or email **sdk@polaxis.io**.
