# Work Chunk 01C: Path Management

**Phase**: 1C — Foundation
**Created**: 2026-03-01

---

## Before Proceeding

- [`full_codebase_refactor.md`](../full_codebase_refactor.md) — master plan
- [`CONTRIBUTING.md`](../../../../CONTRIBUTING.md) — development philosophy
- [`07_old_code_porting_audit.md`](07_old_code_porting_audit.md) — record any deferred decisions

**Prerequisites**: Work chunks 01A and 01B complete.

---

## Task Understanding

### Requirements

1. **`src/hydro_fetch/config/paths.py`** — centralized path construction for the hydro-fetch pipeline:
   - **Output paths**: construct product output paths from config, following Decision 4 (flat structure: `{output_dir}/{product_name}.{format}`).
     - `product_output_path(output_dir, product_name, output_format) -> Path` — returns e.g. `outputs/mrms_crctd_w_pass2_1hr.zarr`
     - `csv_output_path(output_dir, product_name) -> Path` — for gage-extracted CSV outputs
   - **Raw download paths**: organized by product and date to mirror the S3 bucket layout for easy comparison of local vs remote files.
     - `raw_download_dir(output_dir, product_name) -> Path` — returns e.g. `outputs/.downloads/mrms_2min/`
     - `raw_download_path(output_dir, product_name, date, filename) -> Path` — returns e.g. `outputs/.downloads/mrms_2min/20200101/MRMS_PrecipRate_00.00_20200101-120000.grib2.gz`
   - **State file path**: for incremental download tracking (per Decision 3/5).
     - `download_state_path(output_dir) -> Path` — returns `{output_dir}/.download_state.json`
   - **All paths are relative to `output_dir`** as specified in `PipelineConfig`. No hardcoded absolute paths.

### Key Design Decisions

- **Flat output structure per Decision 4** — `outputs/{product_name}.zarr` (or `.nc`, `.csv`). Product names already encode source, correction status, and timestep, so subdirectories would be redundant.
- **Raw downloads in a hidden `.downloads/` subdirectory** — keeps the output directory clean while co-locating raw data with processed output. The S3-mirror layout (`product/YYYYMMDD/filename`) enables the incremental download manager (Decision 5) to compare local files against S3 bucket listings by filename match.
- **Pure functions, no state** — path functions take explicit arguments (output_dir, product_name, etc.) and return `Path` objects. They do not create directories; directory creation is the caller's responsibility.
- **No defaults for function arguments** per CONTRIBUTING.md.

### Success Criteria

- All path functions are importable and return `Path` objects
- Output paths follow Decision 4 flat structure
- Raw download paths mirror the S3 bucket layout (product/date/filename)
- No hardcoded absolute paths; all paths are relative to the provided `output_dir`
- Path functions are pure (no side effects, no directory creation)

---

## Evidence from Codebase

Inspect before implementing:

1. `_old_code_to_refactor/hpc/__utils.py` lines 7-12 — hardcoded repo and data paths (`fldr_repo`, `fldr_nc_fullres_daily`, etc.). These are the anti-pattern this module replaces.
2. `_old_code_to_refactor/local/__filepaths.py` lines 1-53 — extensive hardcoded Windows paths and nested directory structures. The `return_*_filepaths()` functions (lines 112-131) show the old approach of grouping paths by script. The new module groups by purpose (output, download, state).
3. `_old_code_to_refactor/local/__filepaths.py` lines 20-24 — QA/QC output paths nested under the bias-corrected data directory. Consider whether QA/QC outputs need their own path function or belong under the flat output structure.
4. `full_codebase_refactor.md` Decision 4 — flat output structure with a threshold of ~8 files before considering subdirectories.
5. `full_codebase_refactor.md` Decision 5 — incremental download strategy relies on comparing S3 bucket listings against local files by filename. The raw download path structure must support this.

---

## File-by-File Change Plan

### New Files

| File | Purpose |
|------|---------|
| `src/hydro_fetch/config/paths.py` | Path construction functions for output, download, and state file paths |

### Modified Files

| File | Change |
|------|--------|
| `src/hydro_fetch/config/__init__.py` | Add re-exports for path functions |

---

## Risks and Edge Cases

| Risk | Mitigation |
|------|-----------|
| Output directory may not exist when paths are constructed | Path functions are pure and do not create directories; document that callers must `mkdir(parents=True, exist_ok=True)` before writing |
| Product name in file path may contain characters that are problematic on some filesystems | Canonical product names (Decision 1) use only lowercase, underscores, and digits — all filesystem-safe |
| The flat output structure may hit the ~8 file threshold when all products are enabled at multiple timesteps | Decision 4 notes this threshold; add a comment in the module referencing the decision and the threshold |
| Raw download directory could grow very large for multi-year CONUS downloads | This is expected behavior for HPC-CONUS mode. The `.downloads/` directory can be pruned after processing. Document this in the module docstring. |
| Relative vs absolute path ambiguity if `output_dir` in config is relative | `PipelineConfig` (01B) should resolve `output_dir` to absolute at load time; path functions here receive an already-resolved `Path` |

---

## Validation Plan

```bash
# Smoke test: imports
conda run -n hydro_fetch python -c "
from hydro_fetch.config.paths import product_output_path, raw_download_dir, raw_download_path, download_state_path
print('All path imports OK')
"

# Verify output path construction
conda run -n hydro_fetch python -c "
from hydro_fetch.config.paths import product_output_path, raw_download_path, download_state_path
from pathlib import Path

out = product_output_path(Path('/tmp/outputs'), 'mrms_crctd_w_pass2_1hr', 'zarr')
assert out == Path('/tmp/outputs/mrms_crctd_w_pass2_1hr.zarr'), f'Unexpected: {out}'

raw = raw_download_path(Path('/tmp/outputs'), 'mrms_2min', '20200101', 'MRMS_PrecipRate_00.00_20200101-120000.grib2.gz')
assert 'mrms_2min' in str(raw)
assert '20200101' in str(raw)

state = download_state_path(Path('/tmp/outputs'))
assert state.name == '.download_state.json'

print('All path tests passed')
"

# ruff
conda run -n hydro_fetch ruff check src/hydro_fetch/config/paths.py
conda run -n hydro_fetch ruff format --check src/hydro_fetch/config/paths.py
```

---

## Documentation and Tracker Updates

- Update `work_chunks/README.md`: mark 01C status

---

## Definition of Done

- [ ] `src/hydro_fetch/config/paths.py` implemented with all path construction functions
- [ ] Output paths follow Decision 4 flat structure (`{output_dir}/{product_name}.{format}`)
- [ ] Raw download paths mirror S3 bucket layout (`{output_dir}/.downloads/{product}/{YYYYMMDD}/{filename}`)
- [ ] Download state path returns `{output_dir}/.download_state.json`
- [ ] All functions are pure (no side effects, no directory creation)
- [ ] No function arguments have defaults (per CONTRIBUTING.md)
- [ ] No hardcoded absolute paths
- [ ] All functions have docstrings and type annotations
- [ ] `config/__init__.py` updated with re-exports
- [ ] `ruff check` and `ruff format` pass
- [ ] Pyright reports no errors
- [ ] **Move this document to `../implemented/` once all boxes above are checked**
