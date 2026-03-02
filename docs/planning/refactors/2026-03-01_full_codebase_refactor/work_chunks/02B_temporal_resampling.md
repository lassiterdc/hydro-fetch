# Work Chunk 02B: Temporal Resampling

**Phase**: 2B — Core Computation
**Created**: 2026-03-01

---

## Before Proceeding

- [`full_codebase_refactor.md`](../full_codebase_refactor.md) — master plan
- [`CONTRIBUTING.md`](../../../../CONTRIBUTING.md) — development philosophy
- [`07_old_code_porting_audit.md`](07_old_code_porting_audit.md) — record any deferred decisions

**Prerequisite**: Work chunk 01D (I/O layer) complete.

---

## Task Understanding

### Requirements

1. **`src/hydro_fetch/process/temporal.py`** — temporal resampling functions for precipitation data:

   - `resample_to_constant_timestep(ds, target_timestep_min)` — resample an irregularly-spaced time series to a constant timestep. The old code (`_da2` lines 622-627) reindexes to 1-minute resolution via forward-fill, then resamples to the target (e.g., 2 min or 5 min). The new code should replicate this approach.
   - `aggregate_to_hourly(ds)` — resample sub-hourly data to hourly using `.resample(time="1h").mean()`. Ported from `_db` lines 58-63.
   - `aggregate_to_daily(ds)` — resample hourly data to daily totals. Ported from `_db` lines 101-104. The old code multiplied hourly mm/hr by 24 before daily mean — verify this produces correct daily totals.
   - `aggregate_to_monthly(ds)` — resample daily data to monthly totals. Ported from `local/a1` (monthly aggregation).
   - `aggregate_to_annual(ds)` — resample daily data to annual totals. Ported from `_ha` lines 52-80. Must handle leap years (366 vs 365 days).
   - `combine_daily_to_annual(datasets)` — concatenate daily datasets into a single annual dataset. Ported from `_dc`.

2. **`missing_duration_min` DataArray** (per Decision 6): during temporal aggregation, compute a DataArray showing total missing duration (minutes) per day per grid cell.
   - Dimensions: `(time_day, y, x)` — one value per day per grid cell
   - Value: total minutes of missing data for that day
   - Computed by counting expected vs actual timesteps per day, multiplied by the timestep duration
   - Expected timestep count is determined from the product's native temporal resolution (e.g., 720 timesteps/day for 2-min data, 24 for hourly)
   - Stored alongside precipitation data in the same output

3. **Product name timestep update** (per Decision 1): when temporal resampling produces a new timestep, the product name updates accordingly (e.g., `mrms_crctd_w_pass2_2min` becomes `mrms_crctd_w_pass2_1hr`). Functions should update `attrs["product_name"]` if present.

4. All functions are pure computation — receive xarray Datasets, return xarray Datasets. No file I/O.

5. Must handle dask-backed arrays for out-of-core processing.

### Key Design Decisions

- **Resampling semantics**: `mean()` for intensity-based data (mm/hr), `sum()` for accumulation-based data. The old code used `mean()` because MRMS PrecipRate is in mm/hr — the mean of hourly rates over a day gives mm/hr, which must be multiplied by duration to get totals. The new code should be explicit about units in function docstrings and attribute updates.
- **Forward-fill for irregular timesteps**: the old code reindexes to 1-min then resamples. This assumes precipitation rate is constant between observations. Document this assumption.
- **Leap year handling**: the old code (`_ha` lines 75-80) checks `yr % 4 == 0` for leap years — this is incorrect for years divisible by 100 but not 400 (e.g., 1900). Use `calendar.isleap()` or let pandas handle it via proper datetime operations.
- **Attribute updates**: each aggregation function should update `attrs["time_step"]`, `attrs["original_temporal_resolution"]`, and long_name/units metadata.
- **No silent data loss**: if a day has all-NaN timesteps, the aggregated result should be NaN (not 0). The old code used `skipna=True` in `.mean()` — this can mask missing data. The `missing_duration_min` DataArray provides the companion signal for quality assessment.

### Success Criteria

- `resample_to_constant_timestep()` correctly resamples irregular MRMS data to a constant timestep
- All aggregation functions produce correct totals/means with proper unit handling
- `missing_duration_min` DataArray is computed during aggregation and included in output
- Leap years are handled correctly
- All functions work with dask-backed arrays
- Product name timestep suffix updates when aggregation changes the temporal resolution
- No file I/O in any function

---

## Evidence from Codebase

Inspect before implementing:

1. `_old_code_to_refactor/hpc/_da2_resampling_to_same_tstep.py` lines 610-631 — timestep validation and resampling to constant timestep. Key logic: check if `tstep_min != target_tstep_min`, then reindex to 1-min via forward-fill, then resample to target.
2. `_old_code_to_refactor/hpc/_da2_resampling_to_same_tstep.py` line 275 — hourly aggregation for bias correction: `ds_mrms.resample(time="H").mean()`.
3. `_old_code_to_refactor/hpc/_db_resampling_to_hourly_and_daily_timesteps.py` lines 58-63, 101-115 — hourly and daily aggregation with attribute updates.
4. `_old_code_to_refactor/hpc/_dc_combining_daily_totals_in_annual_netcdfs.py` — combines daily NetCDFs into annual files via `xr.open_mfdataset()` + `concat`.
5. `_old_code_to_refactor/hpc/_ha_generate_annual_statistics_netcdfs.py` lines 49-80 — annual resampling with leap year handling and mm/day to mm/year conversion.
6. `_old_code_to_refactor/hpc/__utils.py` line 59 — `target_tstep = 5` (minutes). The new code uses 2-min as the native PrecipRate timestep; the target is configurable.
7. `_old_code_to_refactor/hpc/_da2_resampling_to_same_tstep.py` lines 35-36 — `tsteps_per_day = int(24 * 60 / target_tstep_min)` and `tsteps_per_hr = 60 / target_tstep_min`. These are used for computing expected timestep counts (relevant to `missing_duration_min`).

---

## File-by-File Change Plan

### New Files

| File | Purpose |
|------|---------|
| `src/hydro_fetch/process/temporal.py` | Temporal resampling and aggregation functions |
| `tests/test_temporal.py` | Unit tests for temporal resampling |

### Modified Files

| File | Change |
|------|--------|
| `src/hydro_fetch/process/__init__.py` | Ensure module is importable |

---

## Risks and Edge Cases

| Risk | Mitigation |
|------|-----------|
| Forward-fill resampling introduces artifacts at data gaps | Track gap duration in `missing_duration_min`; document the forward-fill assumption; flag days where gap duration exceeds a threshold |
| `skipna=True` in `.mean()` masks partially-missing days as valid | Use `missing_duration_min` as the companion quality signal; document that aggregated values include partial-day estimates when gaps exist |
| Leap year handling with `yr % 4` is incorrect | Use `calendar.isleap()` or pandas datetime operations |
| Unit confusion: mm/hr vs mm for different aggregation levels | Explicit unit tracking in attrs; docstrings specify input/output units |
| Large dask task graphs from chaining multiple resample operations | Test with realistic data sizes; consider intermediate `.persist()` calls if graphs become too large |
| The old code's daily total computation (`mean("time") * 24`) assumes 24 hours of data | Compute actual duration from timestamps to handle partial days correctly |
| Product name timestep suffix update requires knowledge of the product naming convention | Import product name manipulation utilities from constants or config |

---

## Validation Plan

```bash
# Unit tests
conda run -n hydro_fetch pytest tests/test_temporal.py -v

# Smoke test
conda run -n hydro_fetch python -c "
from hydro_fetch.process.temporal import (
    resample_to_constant_timestep,
    aggregate_to_hourly,
    aggregate_to_daily,
    aggregate_to_monthly,
    aggregate_to_annual,
    combine_daily_to_annual,
)
print('All imports OK')
"

# Linting
conda run -n hydro_fetch ruff check src/hydro_fetch/process/temporal.py
conda run -n hydro_fetch ruff format --check src/hydro_fetch/process/temporal.py
```

### Test Cases

1. **resample_to_constant_timestep**: Create a dataset with irregular timestamps (e.g., some 2-min gaps, some 10-min gaps), resample to 2-min, verify all timesteps are present and values are forward-filled.
2. **aggregate_to_hourly**: Create 2-min data for 1 hour (30 timesteps), aggregate to hourly, verify the result equals the mean of input values.
3. **aggregate_to_daily**: Create hourly data for 1 day (24 timesteps), aggregate to daily, verify total precipitation in mm.
4. **missing_duration_min**: Create a dataset with 3 missing timesteps out of 720 expected (2-min data for 1 day), verify `missing_duration_min` = 6 minutes for affected grid cells.
5. **Leap year**: Create annual data spanning 2024 (leap year) and 2023 (non-leap), verify correct day counts.
6. **Dask compatibility**: Run all tests with dask-backed arrays.
7. **Partial day**: Create a dataset with only 12 hours of data, verify daily aggregation produces correct values and `missing_duration_min` = 720 minutes.

---

## Documentation and Tracker Updates

- Update `full_codebase_refactor.md`: mark `_da2` (resampling portions), `_db`, `_dc`, `_da` as partially ported in tracking table
- Update `work_chunks/README.md`: mark 02B as complete

---

## Definition of Done

- [ ] `src/hydro_fetch/process/temporal.py` implemented with all six functions
- [ ] `missing_duration_min` DataArray computed during daily aggregation per Decision 6
- [ ] All functions are pure computation — no file I/O
- [ ] All functions work with dask-backed arrays
- [ ] Leap year handling uses `calendar.isleap()` or equivalent, not `yr % 4`
- [ ] Product name timestep suffix updates in attrs when temporal resolution changes (Decision 1)
- [ ] Unit metadata (attrs) updated by each aggregation function
- [ ] Unit tests cover regular, irregular, partial-day, and leap-year cases
- [ ] `ruff check` and `ruff format` pass
- [ ] Type hints and docstrings on all public functions
- [ ] **Move this document to `../implemented/` once all boxes above are checked**
