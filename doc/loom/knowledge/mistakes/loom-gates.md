# Loom Gates

> Contract cwd and uv_build bound: gate mistakes that apply to this repo's packages

## Frozen contracts ran from the repository root on the system python

**What happened**: contracts were frozen with `adapter=pytest` and `cwd=.`, so the completion run executed `python3 -m pytest <file>` from the repository root. The system `python3` has no pytest, Pillow or the kit packages, so every such contract failed with `No module named pytest` whatever the code did. The freeze recorded each red as `exit_nonzero_unverified` and accepted it, so stages finished their work and blocked only at completion. Re-freezing fixed one contract per `dispute-contract` filing (`--contract` takes one id) and a stage may file three disputes per kind.
**Why**: each package (`fixtures/web`, `fixtures/tui`, `post`, `edit`, `tests`) has its own uv environment; the contract's `cwd` must be that package directory. The repository root holds no `pyproject.toml` or `uv.lock`. Loom documents that an omitted `cwd` resolves to the nearest ancestor holding runner config, yet it recorded `.`.
**Prevention**: when a plan defines contracts for a uv package, set each contract's `cwd` to the package directory and confirm with `uv run --frozen pytest tests/test_contracts.py` there before freezing. After the contract session, read `loom stage contracts show <stage>`: a `cwd=.` row or an `exit_nonzero_unverified` outcome means the reds are unproven; fix it before implementation starts. A stage that finds a wrong `cwd` disputes every affected contract at once.
**Fix**: `loom stage amend <stage> --field contracts --op replace --index <n> --value <yaml with cwd>` for each contract, then `loom stage retry <stage> --context ...`.

## A seed `uv_build` bound warned on every build

**What happened**: a package's `pyproject.toml` kept a `uv_build>=0.8,<0.12` bound that excludes the locked uv 0.12.22, so every build printed `build_system.requires ... does not contain the current uv version`.
**Why**: the bound predates the uv upgrade; `uv add` cannot edit `build-system.requires`.
**Prevention**: keep every package's `uv_build` bound in step with the uv the kit locks with (`fixtures/tui/pyproject.toml` and `post/pyproject.toml` use `uv_build>=0.12.22,<0.13.0`). Every warning is yours.
**Fix**: edit the one line by hand.
