# CLAUDE.md

Read these files before beginning any task:

- `CONTRIBUTING.md`
- `architecture.md`

---

## Planning Document Lifecycle

Read `~/dev/claude-workspace/specialist_agent_docs/planning-document-lifecycle.md` for the full lifecycle rules.

---

## Environment

This project uses a conda environment named `hydro_fetch`.

- **Running tools**: Use `conda run -n hydro_fetch <command>` or activate the environment first with `conda activate hydro_fetch`.
- **Copier updates**: When running `copier update` through `conda run`, pass `--defaults` since there is no interactive terminal: `conda run -n hydro_fetch copier update --trust --skip-tasks --defaults`.

---

## Code Style

- **Python**: ≥3.10, target 3.12+
- **Formatter/linter**: `ruff format` and `ruff check` — run before submitting any code. Line length and all style rules are enforced by `pyproject.toml`; write code that will survive `ruff format` unchanged.
- **Type checker**: Pyright/Pylance — address squiggles organically as scripts are touched; do not leave new `# type: ignore` comments unless the issue is a known type checker limitation

---

## Terminology

- **Canonical product name**: `{source}[_{descriptor}][_crctd_w_{correction_source}]_{timestep}` — e.g., `mrms_2min`, `mrms_pass2_1hr`, `mrms_crctd_w_pass2_2min`, `mrms_crctd_w_aorc_2min`, `aorc_1hr`. Used as dict keys, directory names, and Snakemake wildcards.
- **Run mode**: `local_clip` (download, clip, process, delete raw) or `hpc_conus` (download all, process full CONUS grid). Set in `pipeline.yaml`.
- **Incremental download**: Compare S3 bucket listing against local files; download only the delta. Controlled by `PipelineConfig.incremental`.
- **Atomic write**: Download to `.tmp` suffix, rename on success. Prevents partial files from being treated as complete.

---

## Architecture Patterns

- **Config flow**: `pipeline.yaml` → `PipelineConfig` (Pydantic v2) → passed to download managers and processing functions. `system.yaml` → `SystemConfig` for AOI/CRS. Loaded via `hydro_fetch.config.load_pipeline_config()`.
- **Package structure**: `config/` → `acquire/` → `process/` → `statistics/` → `compare/` → `viz/` → `workflow/`. Each layer depends only on layers above it.
- **Snakemake orchestration**: Rules in `src/hydro_fetch/workflow/rules/`, profiles in `workflow/profiles/`. CLI entry point (`typer`) wraps `snakemake` invocation.
- **Path management**: All output paths resolved by `hydro_fetch.config.paths` module using `PipelineConfig.output_dir` as root. No hardcoded paths in processing code.

---

## AI Working Norms

Read `~/dev/claude-workspace/specialist_agent_docs/ai-working-norms.md` for the full protocol.
