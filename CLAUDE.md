# CLAUDE.md

Guidance for Claude Code when working in this repository. See [README.md](README.md) for the user-facing overview.

## What this is

The **ProgSnap2 Toolkit** is a Python package (`progsnap2`, under `src/`) for collecting, converting, and analyzing programming-process log data in the [ProgSnap2 format](https://cssplice.org/progsnap2/). It is a research codebase for CS education / educational data mining, part of the SPLICE project. It has three main jobs:

1. **Analysis**: load a ProgSnap2 dataset (CSV, SQLite, or SQL) into pandas and compute metrics.
2. **Conversion**: turn public datasets (CodeWorkout, FalconCode, CodeBench, Edwards keystroke data) into ProgSnap2.
3. **Collection**: a FastAPI server that validates and logs ProgSnap2 events to a SQL/SQLite database.

## Environment and commands

- Python 3.11+. The project env is a local conda env at `.conda/`. Use `./.conda/python.exe`, because the system `python` does not have the dependencies installed.
- Dependencies: `requirements/*.in` are the sources and `pyproject.toml` reads them dynamically. `requirements*.txt` are pinned outputs of `pip-compile`; regenerate them with `gen_requirements.bat` rather than editing them by hand.
- Tests: `./.conda/python.exe -m pytest` (runs in about 5 seconds). `pyproject.toml` sets `testpaths = ["tests"]` and puts `src` on the path. Don't pass `.` or `sample_data` as a path: pytest would crawl the datasets for 10+ minutes and fail collecting dataset files. Tests write temporary output to `test_data/`, which is cleaned at the start of each session.
  - Known failures as of 2026-11-13: `test_directory_codestate_writer` (DirectoryCodeStateWriter is missing abstract methods), `test_event_writer_one_event` (`SQLWriter` has no `conn`), `test_sqlite_writer_add_events` (transaction already begun). They happen before any of your changes, so don't treat them as regressions.
- Run the API with `run_api.bat` or `run_api.sh` (uvicorn with reload, on `progsnap2.api.main:app`). The docs are at http://127.0.0.1:8000/docs. The config is `src/progsnap2/api/api_config.yaml`, and the API writes to `test-data/example.db` by default.
- Docs: `scripts/generate_docs.py` plus `mkdocs build`, which CI runs on pushes to `main` that touch the spec YAML.

## Architecture

```
src/progsnap2/
  spec/        ProgSnap2 spec model (pydantic), loaded from spec/versions/progsnap2-v1.0.yaml
    enums.py   GENERATED from the spec YAML, so don't hand-edit it (see "Regenerating code" below)
    gen/       code generators: enums, TypeScript client, DB schema, docs
  database/    reading and writing datasets
    config.py           PS2DataConfig (read) / PS2DataWriteConfig (write)
    writer/db_writer_factory.py  IOFactory: chooses the CSV or SQL reader/writer and the CodeState backend
    reader/             CSVReader, SQLReader
    codestate/          CodeState backends: Table (CSV/SQL), Directory, Git, Keystroke
  analytics/
    ps2_dataset.py      PS2Dataset (main entry point for analysis) + Preprocessor classes
    analytics_config.py AnalyticsConfig, Granularity, ProgrammingLanguage
    metrics/            error (EQ, RED, Watwin), score, and time metrics
    preprocessors/      dataset-specific preprocessors
  datasets/    AnalyticsConfig instances for known datasets (codeworkout.F19, falconcode.S21, ...)
  converters/  notebooks (and, increasingly, scripts) that convert raw datasets into ProgSnap2
  api/         FastAPI collection server; event models are generated dynamically from the spec
  examples/    demo notebooks
```

### Key concepts

- **Spec-driven.** Columns, event types, metadata properties, and link tables all come from the spec YAML. Refer to them with the enums in `progsnap2.spec.enums` (conventionally `MainTableColumns as Cols`, `EventType`, `CoreTables`, `CodeStatesTableColumns`, `MetadataProperties`) rather than string literals.
- **Loading flow.** `AnalyticsConfig.load(root)` calls `create_data_config(root)` to get a `PS2DataConfig`, then builds a `PS2Dataset`, which uses `IOFactory` to pick a reader. A `PS2DataConfig` has exactly one of `main_table_file` (CSV) or `sqlalchemy_url` (SQL/SQLite).
- **Metadata** comes from the dataset's metadata table, or from the config when the dataset lacks one. `CodeStateRepresentation` in the metadata decides which CodeState backend is used.
- **Preprocessors** run in order on `get_main_table()` / `get_link_table()`. Defaults are `AddProblemIDPreprocessor` and `TimePreprocessor`. Dataset configs prepend their own (e.g. sorting, extracting error types). The base dataset fixes quirks at load time, not in the raw data.
- **Datasets with multiple semesters** define a `_base_config` and use `dataclasses.replace` for each term (`S19`, `F19`, ...), setting fields such as `early_time`.

### Regenerating code

After editing the spec YAML, run `./.conda/python.exe test.py`. It regenerates `spec/enums.py` and copies the generated TypeScript client methods to the clipboard (it needs `pyperclip`). This is a stopgap: a more formal auto-generation process is planned, so don't build further tooling on top of `test.py`.

## Data access: whitelist only

Real datasets live in `sample_data/<dataset>/`. The folder is gitignored and large, so don't commit it.

**You may read or inspect data only from these datasets**, which are public and de-identified:

- `sample_data/codebench/`
- `sample_data/codeworkout/`
- `sample_data/edwards/`

For every other folder in `sample_data/` (e.g. `falconcode`, `cs1eng`, `feature_importance`, and anything new), **don't open, grep, list contents of, query, or print data from it**, even when that would be convenient for debugging. You may write or edit code that loads those datasets (e.g. their configs in `datasets/`), but don't run it yourself in a way that prints its data to you. Ask the user to run it and report back. If you're unsure whether a dataset is on the whitelist, assume it isn't and ask.

`.claude/settings.json` partly enforces this with deny rules for the folders that aren't whitelisted and for `sample_data.zip`. Those rules are written per folder, so a new non-whitelisted dataset isn't blocked until a matching rule is added there. Ask the user to add one, rather than relying on the deny list to keep you out.

## Converters

- New converters should be **jupytext notebooks** (paired `.py` in percent format, `# %%` cells), because conversions have meaningful intermediate output worth inspecting. jupytext is installed in `.conda` but isn't yet in `requirements/`. The older converters are plain `.ipynb` files in `converters/`.
- Put each converter in its own folder, `converters/<dataset>/`, with its tests in `tests/`.
- Raw input lives in `sample_data/<dataset>/raw/`. Converter output goes next to it in `sample_data/<dataset>/`.
- Preferred output is **SQLite with a Table CodeState representation**. Write `MainTable`, `CodeStates`, `Metadata`, and `Link*` tables, and add an index on `CodeStates.CodeStateID`. After converting, add or update a config in `datasets/` so the result loads with `config.load(root)`.

## Conventions

- The paths in `README.md` use Windows backslashes. The primary development platform is Windows (PowerShell / `.bat` scripts), but keep code portable (`os.path.join`).
- Modules use `logger = logging.getLogger(__name__)`, not `print`.
- Several TODOs mark known design debt (e.g. splitting `IOFactory` into a reader and a writer). Don't refactor them unless asked.
- **Git:** the user commits by default, so don't commit unless asked. If asked to commit, use a feature branch (e.g. `codebench`) and open a PR to `main` rather than committing to `main` directly.

## Current work

- `codebench` branch: converting raw CodeBench semesters to ProgSnap2 (SQLite, tabular CodeStates), using `sample_data/codebench/f24` as the reference format. The task description is in `src/progsnap2/converters/codebench/codebench-task.md`.
