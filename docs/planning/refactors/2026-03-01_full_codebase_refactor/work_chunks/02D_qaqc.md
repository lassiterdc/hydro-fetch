# Work Chunk 02D: QA/QC Checks and Flagging

**Phase**: 2D — Core Computation
**Created**: 2026-03-01

---

## Before Proceeding

- [`full_codebase_refactor.md`](../full_codebase_refactor.md) — master plan
- [`CONTRIBUTING.md`](../../../../CONTRIBUTING.md) — development philosophy
- [`07_old_code_porting_audit.md`](07_old_code_porting_audit.md) — record any deferred decisions

**Prerequisites**: Work chunks 01D (I/O layer) and 02B (temporal resampling) complete.

---

## Task Understanding

### Requirements

1. **`src/hydro_fetch/process/qaqc.py`** — QA/QC checks, flagging, and quality assessment functions:

   - `validate_resampling_quality(ds, performance_df)` — validate the quality of temporal resampling by checking for duration problems, coordinate duplicates, and export errors. Ported from `_da3` lines 55-63 (checking `problem_exporting_netcdf`/`problem_exporting_zarr` flags) and the `check_duplicates()` function found in `_da3` lines 66-80, `_da2` lines 141-155, and `_i` lines 54-68.

   - `flag_questionable_data(ds, missing_duration_min, max_gap_fraction)` — flag data that should be treated as questionable due to excessive missing data, anomalous values, or known bad periods. Uses `missing_duration_min` from 02B to identify gap-affected periods. Replaces the old approach in `_da3c` which renamed files to exclude them — the new code flags data in-place without deleting it.

   - `compute_correction_factor_statistics(ds_qaqc, grouping)` — compute summary statistics (sum, min, max, mean, quantiles) of bias correction QA/QC variables grouped by year, month, or year-month. Ported from `_da3b` lines 90-122 which uses `flox.xarray.xarray_reduce()` for blockwise groupby operations.

   - `check_coordinate_duplicates(ds, dims)` — detect duplicate values along spatial dimensions. Ported from the `check_duplicates()` helper that appears in `_da3`, `_da2`, and `_i`.

2. **Must not silently delete data**: the old code (`_da3c`) renamed files to effectively remove questionable dates. The new code must flag data (e.g., add a `quality_flag` DataArray or attribute) and let the user or workflow decide what to do. This follows the CONTRIBUTING.md principle of fail-fast and explicit error handling.

3. **Integration with `missing_duration_min`** from 02B: the `missing_duration_min` DataArray is the primary signal for temporal data quality. QAQC functions should use it to flag periods where gap fraction exceeds a configurable threshold.

4. All functions are pure computation — no file I/O.

### Key Design Decisions

- **Flag, don't delete**: the old code's approach of renaming files to exclude bad dates (`_da3c`) is replaced by in-dataset flagging. A `quality_flag` DataArray or coordinate can be added to indicate questionable periods. Downstream consumers (Snakemake rules, statistics functions) can filter based on this flag.
- **Configurable thresholds**: the old code hardcoded `dates_to_omit_for_rainyday = pd.date_range("2015-01-01", "2015-01-31")` in `__utils.py`. The new code should accept quality thresholds as parameters (e.g., max allowable gap fraction per day, max correction factor for flagging).
- **Performance tracking**: the old code accumulated performance metrics in dictionaries and exported to CSV (`_da2` performance dict). The new QA/QC module should produce a structured QA/QC report (as a DataFrame or Dataset) rather than ad-hoc dictionaries.
- **Grouped statistics**: the old `_da3b` used `flox` for efficient blockwise groupby operations on large datasets. The new code should use `flox.xarray.xarray_reduce()` for the same purpose if the dataset is large, or standard xarray groupby for smaller datasets.
- **Error evaluation**: the old `_evaluate_errors.py` script parsed SLURM job output files for error strings. This is HPC-specific and is replaced by Snakemake's built-in error handling (Phase 4). The error-parsing logic does not need to be ported to the library. Record this decision in the porting audit.

### Success Criteria

- `validate_resampling_quality()` detects and reports coordinate duplicates, duration problems, and export errors
- `flag_questionable_data()` adds quality flags to datasets based on `missing_duration_min` and configurable thresholds
- `compute_correction_factor_statistics()` produces grouped summary statistics matching the old code's output
- No data is silently deleted — all quality issues are flagged and reported
- All functions work with dask-backed arrays

---

## Evidence from Codebase

Inspect before implementing:

1. `_old_code_to_refactor/hpc/_da3_qaqc_resampling.py` — main QA/QC consolidation script:
   - Lines 36-53: consolidates per-day CSV performance logs from `_da2` into a single CSV
   - Lines 55-63: filters for successful exports
   - Lines 66-80: `check_duplicates()` — checks for duplicate lat/lon values
   - Lines 107-203: consolidates daily QA/QC zarrs into monthly zarrs, then into yearly zarrs
   - Lines 172-191: handles datasets with duplicate coordinates by using a reference dataset's coordinates

2. `_old_code_to_refactor/hpc/_da3b_qaqc_preprocessing.py` — grouped QA/QC statistics:
   - Lines 33-35: creates year, month, year_month grouping coordinates
   - Lines 38-68: `write_netcdf()` — writes grouped statistics with optional spatial resampling to StageIV resolution
   - Lines 89-122: groupby operations for sum, min, max, mean, quantiles using `flox`

3. `_old_code_to_refactor/hpc/_da3c_deleting_questionable_data.py` — deletes (renames) questionable data:
   - Lines 14-24: iterates over NetCDF files and renames those whose dates fall in `dates_to_omit_for_rainyday`
   - Uses hardcoded date range from `__utils.py` line 17

4. `_old_code_to_refactor/hpc/_evaluate_errors.py` — SLURM error log parser:
   - Lines 10-66: `evaluate_errors()` — parses SLURM output files for "error", "DUE TO TIME LIMIT", "CANCELLED AT" strings
   - Lines 68-75: `test_for_duplicates()` — checks for duplicate node names in exclusion lists
   - Lines 85-126: hard-coded SLURM job IDs and script names — entirely HPC-specific, not portable

5. `_old_code_to_refactor/hpc/__utils.py`:
   - Line 17: `dates_to_omit_for_rainyday = pd.date_range(start="2015-01-01", end="2015-01-31", freq="D")` — hardcoded bad date range
   - Lines 55-56: `lst_quants = [0.1, 0.5, 0.9]`, `crxn_upper_bound = 20`, `crxn_lower_bound = 0.01` — used in QA/QC quantile computations

6. `_old_code_to_refactor/hpc/_da2_resampling_to_same_tstep.py`:
   - Lines 141-155: `check_duplicates()` — same function duplicated across scripts
   - Lines 85-86, 572-592: performance dictionary accumulation

---

## File-by-File Change Plan

### New Files

| File | Purpose |
|------|---------|
| `src/hydro_fetch/process/qaqc.py` | QA/QC validation, flagging, and statistics |
| `tests/test_qaqc.py` | Unit tests for QA/QC functions |

### Modified Files

| File | Change |
|------|--------|
| `src/hydro_fetch/process/__init__.py` | Ensure module is importable |

---

## Risks and Edge Cases

| Risk | Mitigation |
|------|-----------|
| `flox` may not be installed in all environments | Make `flox` a required dependency; it is already used in the old code and provides significant performance benefits for large-dataset groupby |
| Coordinate duplicate detection may be slow on CONUS-scale grids | The check is O(n) per dimension; profile and optimize only if needed |
| Hardcoded bad date ranges from old code may not apply to new data | Replace with configurable quality thresholds; do not hardcode any date ranges |
| Quality flags add a new dimension/variable to datasets | Use a simple boolean DataArray `quality_flag` with the same time dimension, or use dataset attributes for per-file flags |
| Old QA/QC statistics assumed StageIV resolution for coarsened outputs (`_da3b` lines 59-66) | The new code should be reference-product-agnostic; coarsened outputs are computed at whatever reference resolution the user configures |

---

## Validation Plan

```bash
# Unit tests
conda run -n hydro_fetch pytest tests/test_qaqc.py -v

# Smoke test
conda run -n hydro_fetch python -c "
from hydro_fetch.process.qaqc import (
    validate_resampling_quality,
    flag_questionable_data,
    compute_correction_factor_statistics,
    check_coordinate_duplicates,
)
print('All imports OK')
"

# Linting
conda run -n hydro_fetch ruff check src/hydro_fetch/process/qaqc.py
conda run -n hydro_fetch ruff format --check src/hydro_fetch/process/qaqc.py
```

### Test Cases

1. **check_coordinate_duplicates**: Create a dataset with duplicate latitude values; verify detection. Create one without duplicates; verify clean result.
2. **flag_questionable_data**: Create a dataset with `missing_duration_min` values ranging from 0 to 1440. Set threshold at 120 minutes (10%). Verify days with >120 min missing are flagged.
3. **flag_questionable_data with zero threshold**: All data should be flagged as questionable (edge case).
4. **compute_correction_factor_statistics**: Create a synthetic QA/QC dataset with correction factor values spanning a year. Group by month, verify sum/min/max/mean/quantile outputs.
5. **validate_resampling_quality**: Create a performance DataFrame with some failed entries; verify correct detection and reporting.
6. **No silent deletion**: Verify that no function removes data from a dataset — only adds flag variables.

---

## Documentation and Tracker Updates

- Update `full_codebase_refactor.md`: mark `_da3`, `_da3b`, `_da3c`, `_evaluate_errors` in tracking table
- Record in `07_old_code_porting_audit.md`: `_evaluate_errors.py` is not ported — its SLURM job log parsing functionality is replaced by Snakemake's built-in error handling
- Record in `07_old_code_porting_audit.md`: `_da3c`'s file-renaming approach is replaced by in-dataset flagging
- Update `work_chunks/README.md`: mark 02D as complete

---

## Definition of Done

- [ ] `src/hydro_fetch/process/qaqc.py` implemented with `validate_resampling_quality()`, `flag_questionable_data()`, `compute_correction_factor_statistics()`, `check_coordinate_duplicates()`
- [ ] No function silently deletes data — all quality issues are flagged
- [ ] Quality thresholds are configurable parameters, not hardcoded
- [ ] `compute_correction_factor_statistics()` supports grouped statistics (year, month, year-month)
- [ ] All functions are pure computation — no file I/O
- [ ] All functions work with dask-backed arrays
- [ ] `_evaluate_errors.py` non-porting decision recorded in porting audit
- [ ] `_da3c` approach change (flag instead of delete) recorded in porting audit
- [ ] Unit tests pass
- [ ] `ruff check` and `ruff format` pass
- [ ] Type hints and docstrings on all public functions
- [ ] **Move this document to `../implemented/` once all boxes above are checked**
