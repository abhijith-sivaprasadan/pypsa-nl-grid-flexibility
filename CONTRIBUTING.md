# Contributing

Issues and pull requests are welcome. Before proposing a change, describe the engineering question, affected assumptions, and expected user-visible behaviour.

1. Create a focused branch from `main`.
2. Install the project and development dependencies as documented in the README.
3. Add or update tests for every calculation change.
4. Run `ruff check .`, `ruff format --check .`, and `pytest -q`.
5. Update documentation when assumptions, inputs, outputs, or limitations change.

Do not describe internal consistency checks as external validation. Do not commit private, proprietary, or redistribution-restricted data.
