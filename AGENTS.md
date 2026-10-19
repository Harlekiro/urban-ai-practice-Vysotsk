# AGENTS.md

Python package boilerplate (IDU template) for `my_package`. It is a starting template:
`my_package`, `MyPackage`, and `my_module` are placeholder names meant to be renamed.

## Commands

Make targets are Unix-style (Windows: the docs recommend WSL/Ubuntu). Run from the repo root.

- Setup: `make install-dev` (editable install of `.[dev]`)
- Test: `make tests` — `pytest tests`; coverage: `make tests-cov`
- Single test: `pytest tests/test_1.py::test_my_function`
- Lint: `make lint` — `pylint my_package`
- Format: `make format` — runs `isort my_package` then `black my_package` (order matters)
- Build: `make build`; clean artifacts: `make clean`
- Docs: `pip install -e '.[docs]'` then `sphinx-build docs/source docs/build` (what CI runs), or `cd docs && make html`

## Verified gotchas

- The real Make targets are `tests` and `tests-cov`, but `docs/source/guide/testing.rst` and `.github/workflows/tests.yml` call `make test` / `make test-cov`, which do not exist. Use the `tests` spellings locally.
- The test extra in `pyproject.toml` is named `tests`, but `make install-test` installs `.[test]` (no `s`), so pytest is not installed by it. Use `pip install -e '.[tests]'`.
- `pyproject.toml` sets `license = { file = "LICENCE" }` but the file on disk is `LICENSE` (spelling mismatch to reconcile before packaging).
- Version is dynamic via `setuptools_scm` (from git tags). `my_package.__version__` reads installed metadata through `importlib.metadata`, so it only resolves after an editable/regular install.

## Conventions

- Style: black + isort + pylint, `line-length = 120`, target `py310`. isort config: `lines_after_imports = 2`, trailing commas.
- Docstrings: numpydoc style (Sphinx napoleon configured for numpy and google styles).
- Narrative docs/guides are written in Russian.
- `README.rst` is the single source embedded into docs via include markers: `.. logo-start/end` and `.. readme-start/end` (used by `docs/source/index.rst`). Keep those markers when editing.

## Layout / entrypoints

- `my_package/` — library code (`__init__.py` holds package metadata, `my_module.py` is the sample module).
- `tests/` — pytest suite (`test_1.py` imports `my_package.my_module`).
- `examples/my_example.ipynb` — sample notebook, embedded in docs via `docs/source/examples/my_example.nblink`.
- `docs/` — Sphinx sources in `docs/source`; separate Sphinx `Makefile` there.
- `my_package.egg-info/` and `.venv*` are local artifacts, not sources.

## CI / release

- `tests.yml` — on every push; runs `make install-test` then `make test` (both currently broken per above).
- `documentation.yml` — builds Sphinx; on push to `main` deploys to the `documentation` branch (GitHub Pages source). Also runs on PRs to `main`/`develop`.
- `pypi.yml` — triggered by `v*` tags; `main` → release to PyPI, `develop` → pre-release when the tag contains `.dev`/`a`/`b`/`rc`. Requires the `PYPI_API_TOKEN` secret.
