# Work Chunk 04B: Run Mode Implementation

**Phase**: 4B — Workflow Orchestration (Run Modes)
**Created**: 2026-03-01

---

## Before Proceeding

Review the following documents before making any edits to plans or writing any code:

- [`full_codebase_refactor.md`](../full_codebase_refactor.md) — master refactor plan; update it if any decisions made here affect the overall plan.
- [`CONTRIBUTING.md`](../../../../CONTRIBUTING.md) — development philosophy.
- [`07_old_code_porting_audit.md`](07_old_code_porting_audit.md) — record any deferred old code decisions here.

**Prerequisites**: Work chunk 04A (Snakemake rule templates) complete.

---

## Task Understanding

### Requirements

1. Extend `src/hydro_fetch/workflow/builder.py` to support two run modes that configure the same Snakemake rules with different parameters:
   - **`local_clip`**: download one timestep, clip to AOI, process, delete raw CONUS file. Sequential execution with limited storage footprint. Designed for local PCs.
   - **`hpc_conus`**: download all CONUS data for the full date range, then process the full grid. Parallel execution with large storage (~11 TB). Targets HPC clusters with SLURM.
2. The run mode is specified in the pipeline YAML config (`run_mode: local_clip | hpc_conus`) and read from the `PipelineConfig` model (01B).
3. Both modes invoke the same Snakemake `.smk` rule files (from 04A) but with different config parameters that control:
   - Whether clipping happens immediately after download (local_clip) or as a separate post-download step (hpc_conus)
   - Whether raw CONUS files are retained after processing (hpc_conus retains; local_clip deletes)
   - Snakemake resource allocation (cores, memory, parallelism)
   - Whether SLURM submission is used (hpc_conus) or local execution (local_clip)
4. The workflow builder generates a Snakemake config dict that encodes run-mode-specific behavior, passed to rule templates via `config["run_mode"]`, `config["clip_after_download"]`, `config["retain_raw"]`, etc.

### Key Design Decisions

- **Same rules, different config**: Run modes do NOT duplicate Snakemake rules. Rules use conditional logic based on config values (e.g., `if config["clip_after_download"]` in the download rule's output/shell block).
- **local_clip deletes raw files eagerly**: After clipping and verifying the clipped output, the raw CONUS GRIB2 file is removed. This keeps disk usage proportional to the AOI size, not CONUS.
- **hpc_conus enables parallelism**: The Snakemake `--jobs` parameter is set high (e.g., 100+) and SLURM executor handles scheduling. local_clip uses `--jobs 1` for sequential download-clip-process cycles to minimize peak disk usage.
- **AOI is required for local_clip, optional for hpc_conus**: The config validator (01B) enforces that `aoi_path` is set when `run_mode: local_clip`. For hpc_conus, AOI is optional (process full CONUS if not set; clip post-hoc if set).
- **Temp file management**: local_clip marks raw CONUS downloads as Snakemake `temp()` outputs so they are auto-deleted after downstream rules consume them.

### Success Criteria

- `WorkflowBuilder.build()` produces different Snakemake config dicts for `local_clip` vs `hpc_conus` modes
- local_clip mode: raw CONUS files are marked as `temp()` in generated rules
- hpc_conus mode: raw CONUS files are retained as persistent outputs
- Config validation rejects `local_clip` without an AOI path
- Both modes produce identical final outputs (zarr/NetCDF) for the same AOI and date range

---

## Evidence from Codebase

Inspect before implementing:

1. `src/hydro_fetch/workflow/builder.py` (from 04A) — existing workflow builder skeleton; extend with run-mode logic
2. `src/hydro_fetch/workflow/rules/download.smk` (from 04A) — download rule template; must support conditional clipping
3. `src/hydro_fetch/workflow/rules/process.smk` (from 04A) — process rule template; resource allocation varies by mode
4. `src/hydro_fetch/config/model.py` (from 01B) — `PipelineConfig` with `run_mode` enum field
5. `_old_code_to_refactor/hpc/` — all SBATCH scripts use SLURM array jobs for per-year parallelism; this maps to hpc_conus mode
6. `_old_code_to_refactor/local/` — local scripts process smaller extents sequentially; this maps to local_clip mode
7. Decision 2 in master plan — AOI specification (vector file + clip_mode)
8. Decision 4 in master plan — flat output directory (`outputs/{product_name}.zarr`)

---

## File-by-File Change Plan

### New Files

| File | Purpose |
|------|---------|
| (none) | Run mode logic is added to existing builder.py, not a separate file |

### Modified Files

| File | Change |
|------|--------|
| `src/hydro_fetch/workflow/builder.py` | Add `_build_local_clip_config()` and `_build_hpc_conus_config()` methods; add run-mode dispatch in `build()` |
| `src/hydro_fetch/workflow/rules/download.smk` | Add conditional `temp()` wrapper on raw outputs when `config["retain_raw"] == False`; add post-download clip step when `config["clip_after_download"] == True` |
| `src/hydro_fetch/workflow/rules/process.smk` | Parameterize resource directives (threads, mem_mb) from config; adjust input paths based on whether clipped or raw files are used |
| `src/hydro_fetch/config/model.py` | Add validation rule: `local_clip` requires `aoi_path` to be set |
| `full_codebase_refactor.md` | Update Phase 4 status; mark 04B as in-progress/complete |

---

## Risks and Edge Cases

| Risk | Mitigation |
|------|-----------|
| local_clip deletes raw file before clip is verified | Clip step must verify output file integrity (non-empty, valid zarr/NC) before raw file removal; use Snakemake `temp()` which only deletes after downstream rule succeeds |
| Disk usage spike in local_clip if multiple downloads run in parallel | Enforce `--jobs 1` for download rules in local_clip mode; Snakemake resource constraints can also cap concurrent downloads |
| hpc_conus without AOI produces 11 TB of output — user may not realize this | Log a warning at workflow build time if hpc_conus mode is selected without an AOI; include estimated storage in the warning |
| Identical final outputs between modes is hard to verify for large datasets | Integration test uses a small date range (1-2 days) with Norfolk AOI; compare checksums of clipped outputs from both modes |
| Snakemake `temp()` behavior may vary across Snakemake versions | Pin minimum Snakemake version in pyproject.toml; test with current conda-forge version |

---

## Validation Plan

```bash
# Unit tests for run mode config generation
conda run -n hydro_fetch pytest tests/test_workflow.py -v -k "run_mode"

# Verify local_clip config requires AOI
conda run -n hydro_fetch python -c "
from hydro_fetch.config.model import PipelineConfig
# Should raise validation error: local_clip without AOI
try:
    PipelineConfig(run_mode='local_clip', aoi_path=None)
    print('ERROR: should have raised')
except Exception as e:
    print(f'Correctly rejected: {e}')
"

# Dry run both modes with Norfolk case study
conda run -n hydro_fetch hydro-fetch run cases/norfolk/pipeline_local_clip.yaml --dry-run
conda run -n hydro_fetch hydro-fetch run cases/norfolk/pipeline_hpc_conus.yaml --dry-run

# Ruff passes
conda run -n hydro_fetch ruff check src/hydro_fetch/workflow/
conda run -n hydro_fetch ruff format --check src/hydro_fetch/workflow/
```

---

## Definition of Done

- [ ] `WorkflowBuilder.build()` dispatches on `run_mode` to produce mode-specific Snakemake config
- [ ] local_clip mode: sequential execution, raw files as `temp()`, clip-after-download enabled
- [ ] hpc_conus mode: parallel execution, raw files retained, SLURM-compatible resource settings
- [ ] Config validation enforces AOI requirement for local_clip
- [ ] Download rules support conditional `temp()` and post-download clipping
- [ ] Process rules parameterize resources (threads, mem_mb) from config
- [ ] Both modes use the same `.smk` rule files — no rule duplication
- [ ] Unit tests cover config generation for both modes
- [ ] Dry-run produces valid DAG for both modes
- [ ] `ruff check` and `ruff format` pass
- [ ] **Move this document to `../implemented/` once all boxes above are checked**
