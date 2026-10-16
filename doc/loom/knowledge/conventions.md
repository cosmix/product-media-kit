# Coding Conventions

> Discovered coding conventions in the codebase.
> A summary of the current tree: correct a section in place with `replace-section`.

## Team rules

The lead talks to the human, owns the records and each medium's plan, briefs agent-team teammates, reviews every output and decides. One owner per file; files plus short messages; human decisions go into `<project>/NOTES.md` before anyone is briefed; the lead reviews before the human sees anything; change only what was asked; the product repository is read-only; no sudo, no system installs, no `pip install`. Detail: [conventions/kit-workflow](conventions/kit-workflow.md).

## Python code conventions

- Modules start with a docstring (CLI modules show their usage); most use `from __future__ import annotations` (`post/` targets Python 3.13 with `type` aliases and generic function syntax instead).
- webcap finds the project module through `webcap.project.product()` (cached) and reads optional attributes with `getattr(module, NAME, default)`; functions that need it take the module as a parameter so tests can pass a stand-in. Async code uses Playwright's `async_api` with `asyncio.run` in each `main()`; `main()` turns a `ValueError` into `webcap: <message>` and exit 1.
- Public functions carry type hints. Tools stop with `SystemExit(message)`; loaders raise `ValueError` for bad shape and `FileNotFoundError` for missing files; CLIs catch `ValueError` and print `<tool>: <message>`. Status lines in the kit scripts start with the level (`ok`, `WARN`, `MISSING`), then the item and a hint.
- ruff runs with its defaults (no `[tool.ruff]` section; `post/pyproject.toml` adds one per-file ignore): they include I001, FURB and TRY004, so write `if isinstance(...): return` then `raise ValueError(...)` or add a justified `noqa`. Lint gate per package: `uv run --frozen ruff check .`; `ruff format` is not a gate.
- Shell scripts are bash with `set -euo pipefail`; never pipe into `grep -q` under `pipefail`, capture the output first.

## Product environment variables and fixtures

A project's product module reads the product's location from `PRODUCT_REPO`, `PRODUCT_WEB_DIST` and `PRODUCT_BIN`, never from hard-coded paths; `webcap.server.require_env(name, what)` returns the path or stops naming what to set. `PRODUCT_URL` (or `BASE_URL` in product.py) switches the web harness to live mode. `tuicap.capture.clean_env(home, drop=(...))` removes the product's env vars and points `HOME` at a scratch home. Fixture state is built inside `fixtures/` with the product's own init commands, never by hand-editing its files.

## Editorial rules for prose

Plain and accurate; no hype, no LLM-isms; name things as the product does and check each claim against the code; name a category, never other companies. Full list: [conventions/kit-workflow](conventions/kit-workflow.md). Capture pitfalls table: [conventions/capture-pitfalls](conventions/capture-pitfalls.md).

## Names and deliverables

Scenario, label and box names match `^[a-z0-9]+(-[a-z0-9]+)*$` in both media. Deliverables are `<stage>-<slug>-v<N>[-<suffix>].<ext>` in `outputs/`; a tool rewrites the latest revision of its stage and `--next` starts a new one after a review ([architecture/outputs-and-reuse](architecture/outputs-and-reuse.md)).

## Guides and tests

Run every suite through the package's own uv environment (`uv run --frozen pytest` from `fixtures/web`, `fixtures/tui`, `post`, `edit` or `tests`); the system `python3` has none of the dependencies. Frozen loom contracts (`test_contracts.py` files) are defined with `adapter=pytest` and `cwd` set to the package directory ([mistakes/loom-gates](mistakes/loom-gates.md)). The guides cite each other's sections only by names that `tests/test_docs_contracts.py` resolves, and every fenced block names its language.

## Knowledge files

Backticked paths in knowledge files must exist in the tree or `loom knowledge check --strict` fails. Write a path inside an installed project as `<project>/NOTES.md` (it passes as a runtime note).
