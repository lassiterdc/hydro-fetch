# Work Chunk 04D: CLI Entry Point

**Phase**: 4D — Workflow Orchestration (CLI)
**Created**: 2026-03-01

---

## Before Proceeding

Review the following documents before making any edits to plans or writing any code:

- [`full_codebase_refactor.md`](../full_codebase_refactor.md) — master refactor plan; update it if any decisions made here affect the overall plan.
- [`CONTRIBUTING.md`](../../../../CONTRIBUTING.md) — development philosophy.
- [`07_old_code_porting_audit.md`](07_old_code_porting_audit.md) — record any deferred old code decisions here.

**Prerequisites**: Work chunks 04A (Snakemake rule templates), 04B (run modes), and 04C (Snakemake profiles) complete.

---

## Task Understanding

### Requirements

1. Create `src/hydro_fetch/cli.py` — the main CLI module providing the `hydro-fetch` command with three subcommands:
   - **`hydro-fetch run <pipeline.yaml>`** — full pipeline execution: load config, build Snakemake workflow, invoke Snakemake API programmatically. This is the primary entry point for all users.
   - **`hydro-fetch download <pipeline.yaml>`** — download-only mode: executes only the download rules from the Snakemake DAG (targets download output files). Useful for pre-staging data on HPC before submitting processing jobs.
   - **`hydro-fetch status <pipeline.yaml>`** — show pipeline progress: which rules have completed, which are pending, estimated remaining files. Reads Snakemake's `.snakemake/` metadata to determine state.

2. Common flags across all subcommands:
   - `--dry-run` / `-n` — preview the Snakemake DAG without executing anything. Shows which rules would run and their dependencies.
   - `--profile <local|slurm>` — override the auto-selected Snakemake profile (default is derived from `run_mode` in the pipeline YAML).
   - `--cores <N>` — override the profile's core count.
   - `--verbose` / `-v` — increase log verbosity.

3. Register the CLI entry point in `pyproject.toml` under `[project.scripts]`:
   - `hydro-fetch = "hydro_fetch.cli:app"`

4. The CLI loads the pipeline YAML config, validates it via the Pydantic model (01B), builds the Snakemake workflow via the workflow builder (04A/04B), selects the profile (04C), and invokes Snakemake programmatically using the Snakemake Python API (not subprocess).

### Key Design Decisions

- **CLI framework: typer**: Use `typer` for the CLI framework. It provides type-annotated argument parsing, automatic help generation, and integrates well with Pydantic models. If typer introduces dependency conflicts, fall back to `click` (typer is built on click).
- **Snakemake invocation via Python API**: Use `snakemake.api` (Snakemake 8+) to invoke workflows programmatically rather than shelling out to the `snakemake` CLI. This provides better error handling, return codes, and avoids PATH/environment issues.
- **Config validation happens early**: The CLI validates the pipeline YAML before building any workflow. Invalid config produces a clear error message with the specific validation failure, not a Snakemake traceback.
- **`status` reads Snakemake metadata**: The status command inspects Snakemake's `.snakemake/` metadata directory and output file existence to determine which rules have completed. It does not re-invoke the full Snakemake engine.
- **Consistent exit codes**: 0 = success, 1 = config/validation error, 2 = download error, 3 = processing error. Supports scripting and CI integration.

### Success Criteria

- `hydro-fetch --help` displays available subcommands with descriptions
- `hydro-fetch run --help` displays all flags with descriptions
- `hydro-fetch run cases/norfolk/pipeline.yaml --dry-run` loads config, builds workflow, and prints the DAG without execution
- `hydro-fetch download cases/norfolk/pipeline.yaml --dry-run` shows only download rules
- `hydro-fetch status cases/norfolk/pipeline.yaml` reports pipeline state (or "no previous run" if no metadata exists)
- Entry point works after `pip install -e .` (registered in pyproject.toml)
- Invalid YAML config produces a user-friendly validation error, not a Python traceback

---

## Evidence from Codebase

Inspect before implementing:

1. `src/hydro_fetch/workflow/builder.py` (from 04A/04B) — `WorkflowBuilder.build()` returns a Snakemake-invocable workflow object or config
2. `src/hydro_fetch/config/loader.py` (from 01B) — `load_config(path)` loads and validates pipeline YAML
3. `src/hydro_fetch/config/model.py` (from 01B) — `PipelineConfig` Pydantic model with all config fields
4. `src/hydro_fetch/workflow/profiles/` (from 04C) — profile paths to pass to Snakemake
5. `src/hydro_fetch/exceptions.py` (from 01A) — `ConfigurationError`, `DownloadError`, `ProcessingError` for exit code mapping
6. `pyproject.toml` — existing `[project.scripts]` section (or absence thereof); add entry point here
7. Snakemake 8 Python API documentation — `snakemake.api.SnakemakeApi` usage patterns
8. `_old_code_to_refactor/hpc/*.sh` — old entry points were SBATCH scripts with hardcoded paths; the CLI replaces all of these

---

## File-by-File Change Plan

### New Files

| File | Purpose |
|------|---------|
| `src/hydro_fetch/cli.py` | CLI module: typer app with `run`, `download`, `status` subcommands; config loading; Snakemake API invocation |

### Modified Files

| File | Change |
|------|--------|
| `pyproject.toml` | Add `[project.scripts]` entry: `hydro-fetch = "hydro_fetch.cli:app"`; add `typer` to dependencies |
| `full_codebase_refactor.md` | Update Phase 4 status; mark 04D as in-progress/complete; mark Phase 4 complete if all 04* chunks done |

---

## Risks and Edge Cases

| Risk | Mitigation |
|------|-----------|
| Snakemake Python API is less stable than CLI interface across versions | Pin minimum Snakemake version; wrap API calls in a thin adapter that can be updated if the API changes |
| typer dependency may conflict with other packages in the conda environment | typer is lightweight with few dependencies; if conflicts arise, fall back to click (typer is built on click) |
| `hydro-fetch status` requires `.snakemake/` metadata which may not exist | Handle gracefully: print "No previous run found" and exit cleanly if metadata directory is missing |
| Pipeline YAML path may be relative or absolute | Resolve to absolute path early in CLI using `Path.resolve()`; all downstream code receives absolute paths |
| Snakemake API may print to stdout/stderr in ways that conflict with CLI output | Capture Snakemake output via logging configuration; route to CLI's logging handler |
| `--dry-run` for `download` subcommand must correctly filter to download-only rules | Use Snakemake's target-based filtering: specify download output files as targets rather than filtering the full DAG post-hoc |

---

## Validation Plan

```bash
# Install in editable mode and verify entry point
conda run -n hydro_fetch pip install -e .
conda run -n hydro_fetch hydro-fetch --help

# Subcommand help
conda run -n hydro_fetch hydro-fetch run --help
conda run -n hydro_fetch hydro-fetch download --help
conda run -n hydro_fetch hydro-fetch status --help

# Dry run with Norfolk case study
conda run -n hydro_fetch hydro-fetch run cases/norfolk/pipeline.yaml --dry-run

# Download-only dry run
conda run -n hydro_fetch hydro-fetch download cases/norfolk/pipeline.yaml --dry-run

# Status with no prior run
conda run -n hydro_fetch hydro-fetch status cases/norfolk/pipeline.yaml

# Invalid config produces a clear error
conda run -n hydro_fetch hydro-fetch run /dev/null 2>&1 | head -5

# Verify exit codes
conda run -n hydro_fetch hydro-fetch run nonexistent.yaml; echo "Exit: $?"

# Unit tests
conda run -n hydro_fetch pytest tests/test_cli.py -v

# Ruff passes
conda run -n hydro_fetch ruff check src/hydro_fetch/cli.py
conda run -n hydro_fetch ruff format --check src/hydro_fetch/cli.py
```

---

## Definition of Done

- [ ] `src/hydro_fetch/cli.py` created with typer-based CLI app
- [ ] `hydro-fetch run <pipeline.yaml>` loads config, builds workflow, invokes Snakemake API
- [ ] `hydro-fetch download <pipeline.yaml>` targets download-only rules
- [ ] `hydro-fetch status <pipeline.yaml>` reports pipeline progress from Snakemake metadata
- [ ] `--dry-run` flag previews DAG without execution on all subcommands
- [ ] `--profile` flag overrides auto-selected profile
- [ ] `--cores` flag overrides profile core count
- [ ] `--verbose` flag increases log verbosity
- [ ] Entry point registered in `pyproject.toml` `[project.scripts]`
- [ ] `typer` added to project dependencies
- [ ] Config validation errors produce user-friendly messages (not raw tracebacks)
- [ ] Consistent exit codes (0=success, 1=config, 2=download, 3=processing)
- [ ] Unit tests for CLI argument parsing and config loading
- [ ] `ruff check` and `ruff format` pass
- [ ] **Move this document to `../implemented/` once all boxes above are checked**
