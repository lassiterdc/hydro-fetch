# Work Chunk 02F: Annual Statistics Computation

**Phase**: 2F — Core Computation
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

1. **`src/hydro_fetch/statistics/annual.py`** — annual statistics computation for precipitation datasets:

   - `compute_annual_statistics(ds, precip_var, exclude_years, quantile_levels, wet_day_threshold)` — compute annual statistics from a multi-year precipitation dataset. Returns an xarray Dataset with statistics as data variables, dimensioned by `(year, y, x)`.

     Output variables:
     - `annual_total_mm`: total precipitation per year per grid cell (mm/year)
     - `annual_mean_rate`: mean precipitation rate per year per grid cell (in input units)
     - `annual_max_daily`: maximum daily total per year per grid cell (mm)
     - `annual_quantiles`: quantile values (e.g., 10th, 50th, 90th percentile of daily totals) per year per grid cell
     - `wet_day_count`: number of days with precipitation above `wet_day_threshold`
     - `max_consecutive_dry_days`: longest streak of days below the threshold

   - `compute_multi_year_summary(ds_annual, exclude_years)` — compute multi-year summary statistics from the annual statistics dataset. Returns mean annual total, standard deviation, coefficient of variation, anomaly (departure from mean) per year.

2. **Product-agnostic**: works on any precipitation dataset — MRMS, QPE Pass2, AORC, or bias-corrected products. The function accepts a `precip_var` parameter specifying the precipitation variable name. No product-specific logic or branching.

3. **Unit-aware**: the input dataset must have a `units` attribute on the precipitation variable (e.g., `"mm/day"`, `"mm/hr"`). The module converts to mm/day internally before computing statistics. Raises `ValueError` if units are missing.

4. **Leap year handling**: must correctly compute annual totals accounting for 365 vs 366 days. Use `calendar.isleap()` or pandas datetime operations, not `yr % 4`.

5. **Year exclusion**: the old code optionally excluded 2012-2014 from mean annual computations (`_ha` lines 68-72, `__utils.py` line 34). The new code accepts an `exclude_years` parameter for this purpose. Exclusion applies to `compute_multi_year_summary()`, not to `compute_annual_statistics()`.

6. All functions are pure computation — no file I/O, no plotting.

### Key Design Decisions

- **Input granularity**: `compute_annual_statistics()` should accept daily-resolution data as input (aggregated by 02B). It should not re-aggregate from sub-daily — that is 02B's responsibility.
- **Unit conversion**: the old code (`_ha` lines 52, 74-80) computes annual mean using `resample(time='Y').mean(skipna=True)` which gives mean daily values, then multiplies by days-per-year to get mm/year. The new code should be explicit about this conversion and track units in attrs.
- **StageIV variant elimination**: the old code had separate scripts `_ha` (MRMS) and `_ha2` (StageIV) that were nearly identical, differing only in I/O paths, coordinate names, and unit conversion factors. The new module eliminates this duplication by accepting any precipitation dataset with standardized dimension names. The `_ha2` StageIV-specific preprocessing (longitude conversion, time shift, negative/extreme value clamping) belongs in the data loading layer, not in statistics.
- **Configurable wet-day threshold**: default 0.254 mm (0.01 inches) — a commonly used threshold in precipitation climatology.
- **Max consecutive dry days**: requires sequential logic. Implement using `xr.apply_ufunc` with `dask='parallelized'` or compute per-year. Document performance implications for CONUS-scale grids.
- **Chunking**: the old code computed chunk sizes based on target memory per chunk (`_ha` lines 20-28). The new code should work with whatever chunking the input has; it should not prescribe chunk sizes.

### Success Criteria

- `compute_annual_statistics()` produces correct annual totals, means, max, quantiles, wet days, and max consecutive dry days
- Leap years are handled correctly
- Year exclusion works for computing multi-year summaries
- Product-agnostic — no product-specific code paths
- Works with dask-backed arrays for CONUS-scale data
- Units are tracked in xarray attrs
- Raises `ValueError` if precipitation variable lacks units attribute

---

## Evidence from Codebase

Inspect before implementing:

1. `_old_code_to_refactor/hpc/_ha_generate_annual_statistics_netcdfs.py` — MRMS annual statistics:
   - Lines 20-28: chunking computation based on target memory size
   - Lines 37-47: load daily NetCDFs, sort by time, remove unused variables
   - Line 49: `ds_allyrs = xr.concat(lst_ds, dim="time", coords='minimal')`
   - Line 52: `ds_yearly = ds_allyrs.resample(time='Y').mean(skipna=True)` — annual mean
   - Lines 54-56: replace time coordinate with year integers
   - Lines 58-62: update attrs (long_name, units, description)
   - Lines 68-72: optionally exclude 2012-2014 from computations
   - Lines 75-80: convert from mm/day to mm/year by multiplying by days-in-year (with leap year check using `yr % 4`)
   - Lines 84-86: export to zarr then NetCDF

2. `_old_code_to_refactor/hpc/_ha2_generate_annual_statistics_netcdfs_stageIV.py` — StageIV variant:
   - Nearly identical structure to `_ha`
   - Lines 58-71: additional preprocessing: convert from preceding to following time interval (`time - pd.Timedelta(1, "h")`), filter negative values, filter values > 9000
   - Lines 86-87: same `resample(time='Y').mean()` approach
   - Lines 112-121: convert from mm/hr to mm/year (multiplies by hours-per-year, not days-per-year, because StageIV is hourly)
   - Lines 123-133: coordinate reformatting (longitude conversion, dimension renaming)

3. `_old_code_to_refactor/hpc/__utils.py`:
   - Line 34: `exclude_2013to2014_from_mean_for_anamolies_plot = True`
   - Line 24: `use_quantized_data = False` — controls whether 2012-2014 data is included in analysis

4. `src/hydro_fetch/process/temporal.py` (from 02B) — temporal resampling functions that produce the daily data consumed by annual statistics

---

## File-by-File Change Plan

### New Files

| File | Purpose |
|------|---------|
| `src/hydro_fetch/statistics/annual.py` | Annual statistics computation |
| `src/hydro_fetch/statistics/__init__.py` | Package init; export annual statistics functions |
| `tests/test_annual_statistics.py` | Unit tests for annual statistics |

### Modified Files

| File | Change |
|------|--------|
| `full_codebase_refactor.md` | Update Phase 2 status; mark `_ha` and `_ha2` in tracking table |

---

## Risks and Edge Cases

| Risk | Mitigation |
|------|-----------|
| `resample(time='Y').mean()` with `skipna=True` can produce biased annual means when many days are missing | Pair with `missing_duration_min` from 02B; document in function docstring that years with significant missing data should be flagged via 02D QA/QC before computing statistics |
| Leap year calculation using `yr % 4` is incorrect for century years | Use `calendar.isleap()` |
| Input data may be in mm/hr (hourly) or mm/day (daily) — conversion to mm/year differs | Require units attribute on the precipitation variable; implement explicit unit conversion with a clear mapping; raise on unrecognized units |
| The old `_ha2` code filters values > 9000 — this is StageIV-specific | Do not include product-specific value filtering in the statistics module. Data cleaning belongs in the preprocessing/QA/QC layer (02D). |
| Very large CONUS-scale multi-year datasets may exceed memory | All operations use dask-compatible xarray methods; no `.values` calls that force full materialization |
| Incomplete years (first/last year of record may have partial data) | Document that partial years produce valid but potentially misleading statistics; consider adding a `min_days` threshold parameter to exclude years with insufficient data |
| Max consecutive dry days requires sequential logic that may not parallelize well with dask | Implement using `xr.apply_ufunc` with `dask='parallelized'`; document performance implications |
| Excluding years from multi-year summary but not from individual-year statistics | `exclude_years` only affects `compute_multi_year_summary()`, not `compute_annual_statistics()`. Both functions should be clear about this. |

---

## Validation Plan

```bash
# Unit tests
conda run -n hydro_fetch pytest tests/test_annual_statistics.py -v

# Smoke test
conda run -n hydro_fetch python -c "
from hydro_fetch.statistics.annual import compute_annual_statistics, compute_multi_year_summary
print('All imports OK')
"

# Linting
conda run -n hydro_fetch ruff check src/hydro_fetch/statistics/annual.py
conda run -n hydro_fetch ruff format --check src/hydro_fetch/statistics/annual.py
```

### Test Cases

1. **Basic annual total**: Create a synthetic 365-day dataset with constant 1 mm/day precipitation. Verify `annual_total_mm = 365`.
2. **Leap year**: Create a 366-day dataset for a leap year. Verify `annual_total_mm = 366`.
3. **Annual max daily**: Create data with one extreme day (100 mm) and 364 normal days (1 mm). Verify `annual_max_daily = 100`.
4. **Quantiles**: Create data with known distribution. Verify 10th, 50th, 90th percentile values.
5. **Wet day count**: Create data with 200 wet days (>0.254 mm) and 165 dry days. Verify `wet_day_count = 200`.
6. **Max consecutive dry days**: Create data with a 30-day dry stretch. Verify `max_consecutive_dry_days = 30`.
7. **Multi-year summary**: Create 5 years of data with varying annual totals. Verify mean, std, CV, and anomaly.
8. **Year exclusion**: Compute multi-year summary with one year excluded. Verify the excluded year does not affect the mean.
9. **Missing data**: Create data with one month of NaN values. Verify annual mean is computed from available data.
10. **Product-agnostic**: Run the same function on datasets with different variable names (e.g., `rainrate` vs `APCP_surface`). Verify it works when `precip_var` is specified.
11. **Unit validation**: Pass a dataset with no units attribute. Verify `ValueError` is raised.
12. **Dask compatibility**: Run with dask-backed arrays.

---

## Documentation and Tracker Updates

- Update `full_codebase_refactor.md`: mark `_ha` and `_ha2` as ported in tracking table
- Record in `07_old_code_porting_audit.md`: `_ha2` StageIV-specific preprocessing (negative value clamping, >9000 filtering, longitude conversion, time shift) is not ported to the statistics module — it belongs in data preprocessing/QA/QC
- Update `work_chunks/README.md`: mark 02F as complete

---

## Definition of Done

- [ ] `src/hydro_fetch/statistics/annual.py` implements `compute_annual_statistics()` and `compute_multi_year_summary()`
- [ ] Computes: total annual precip, max daily, mean daily, quantiles, wet day count, max consecutive dry days
- [ ] Product-agnostic: accepts any precipitation dataset with `time` dimension
- [ ] Precipitation variable name is a function parameter (not hardcoded)
- [ ] Unit-aware: converts input units to mm/day internally; raises `ValueError` on missing units
- [ ] Configurable wet-day threshold and quantile levels
- [ ] Output dimensions: `(year, y, x)` with integer year coordinate
- [ ] Handles leap years correctly with `calendar.isleap()`, not `yr % 4`
- [ ] `exclude_years` parameter supported for multi-year summaries
- [ ] Dask-compatible: works with lazy arrays, no forced materialization
- [ ] QA/QC logic from old code (negative value filtering, year exclusion) is NOT included — documented as deferred to 02D
- [ ] `_ha2` preprocessing non-porting decision recorded in porting audit
- [ ] Unit tests with synthetic data for all statistics
- [ ] `ruff check` and `ruff format` pass
- [ ] Type hints and docstrings on all public functions
- [ ] **Move this document to `../implemented/` once all boxes above are checked**
