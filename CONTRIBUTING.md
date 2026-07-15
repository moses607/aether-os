# Contributing to Aether OS

Thanks for your interest in Aether OS, an open-source Python AI agent kernel.
This guide covers how to set up a dev environment, run the checks, the coding
standards we hold the base kernel to, how to add a skill, and how to open a good
pull request.

## Development setup

Aether targets **Python 3.10+**. Create a virtual environment and install the
package in editable mode with the `dev` extra:

```bash
python -m venv .venv
# Linux / macOS
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

pip install -e ".[dev]"
```

The base kernel is **standard-library only**. The `[dev]` extra pulls in the
tooling used below (pytest, ruff, mypy).

## Running the checks

All three must pass before a PR is merged. CI runs the same commands on Python
3.10, 3.11, and 3.12.

```bash
# Tests
pytest

# Lint
ruff check .

# Type-check
mypy aether
```

You can run the CLI locally to smoke-test your change:

```bash
python -m aether.cli --help
```

## Coding standards

- **Stdlib-only in the base kernel.** The `aether` base package must not import
  third-party runtime dependencies. This keeps the kernel auditable, portable,
  and free of supply-chain surface.
- **Optional dependencies live behind extras.** If a feature needs a third-party
  library, gate it behind an optional extra (e.g. `aether[some-feature]`) and
  import it lazily so the base kernel still imports and runs without it.
- **Everything is typed.** New code carries type annotations and must pass
  `mypy aether` cleanly. No `# type: ignore` without a comment explaining why.
- **Everything is documented.** Public modules, classes, and functions have
  docstrings. If you change behavior, update the relevant docs in the same PR.
- **New features need tests.** Add tests under `tests/` that fail without your
  change and pass with it. Bug fixes should include a regression test.
- **Respect the security model.** The kernel treats all model/tool output as
  untrusted data, enforces deny-by-default policy, gates high-risk actions behind
  human approval, and writes an append-only audit log. Do not add code paths that
  bypass these. See `SECURITY.md`.
- **Style is enforced by ruff.** Run `ruff check .` (and `ruff format .` if you
  use it) before pushing; keep the diff focused.

## Adding a skill

Skills extend the agent with new capabilities. Each skill lives in its own
directory and ships a `SKILL.md` describing it:

1. Create a directory for the skill and add a `SKILL.md` that documents:
   - **Name & purpose** — what the skill does, in one or two sentences.
   - **Actions it proposes** — the concrete actions it may ask the kernel to
     perform, and their risk level (so they can be allowlisted deliberately).
   - **Inputs / outputs** — what it consumes and produces.
   - **Permissions required** — filesystem paths, network endpoints, processes.
   - **Safety notes** — anything a reviewer should know before enabling it.
2. Implement the skill in typed, documented, stdlib-only Python (optional deps
   behind an extra, imported lazily).
3. Add tests under `tests/` covering the happy path and at least one denied /
   requires-approval path.
4. Remember: skills are untrusted code until reviewed. Signing/verification is on
   the roadmap but not yet built, so make your skill easy to audit.

## Pull request guidelines

- **Branch** from the default branch and keep each PR focused on one change.
- **Describe the why**, not just the what. Link any related issue.
- **Green checks required:** `pytest`, `ruff check .`, and `mypy aether` must all
  pass. CI runs them on the full 3.10/3.11/3.12 matrix.
- **Tests included** for new features and bug fixes.
- **Docs updated** when behavior or public API changes.
- **No new base-kernel dependencies.** If you think one is unavoidable, open an
  issue to discuss it first.
- **Security-relevant changes** should call out how they interact with the
  policy, approval gate, and audit log so reviewers can pay attention.

By contributing, you agree that your contributions are licensed under the
project's Apache License 2.0 (see `LICENSE`).
