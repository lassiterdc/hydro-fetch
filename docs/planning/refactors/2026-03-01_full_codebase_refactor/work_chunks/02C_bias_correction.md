# Work Chunk 02C: Bias Correction

**Phase**: 2C — Core Computation
**Created**: 2026-03-01

---

## Before Proceeding

- [`full_codebase_refactor.md`](../full_codebase_refactor.md) — master plan
- [`CONTRIBUTING.md`](../../../../CONTRIBUTING.md) — development philosophy
- [`07_old_code_porting_audit.md`](07_old_code_porting_audit.md) — record any deferred decisions

**Prerequisites**: Work chunks 02A (spatial operations) and 02B (temporal resampling) complete.

---

## Task Understanding

### Requirements

1. **`src/hydro_fetch/process/bias_correction.py`** — bias correction of MRMS PrecipRate using a gage-corrected reference product:

   - `bias_correct_preciprate(ds_mrms, ds_reference, correction_bounds)` — main function. Computes a spatially-varying hourly correction factor from the reference product, applies it to the high-resolution MRMS PrecipRate, and fills grid cells where MRMS has no rain but the reference does. Returns the bias-corrected dataset plus diagnostic DataArrays.

   - `_compute_correction_factor(ds_mrms_hourly, ds_reference, upper_bound, lower_bound)` — compute the ratio `ds_reference / ds_mrms_hourly`, with bounds enforcement and handling of zero-precipitation cells. Ported from `_da2` lines 297-311.

   - `_fill_mrms_gaps_with_reference(ds_mrms, ds_reference, ds_mrms_hourly)` — where MRMS is zero but the reference product has precipitation, substitute the reference values. Ported from `_da2` lines 325-347.

   - `compute_correction_diagnostics(ds_corrected, ds_uncorrected, ds_reference, ds_correction_factor, ds_ref_fill)` — compute diagnostic variables: mean/min/max daily correction factor, quantiles of correction factor, daily totals (corrected vs uncorrected vs reference), fraction of total rain from reference fill values, hours of reference fill values. Ported from `process_bias_corrected_dataset()` in `_da2` lines 450-555.

   - `_reference_bias_correction(ds_mrms, ds_stageiv)` — legacy implementation using StageIV as the reference, preserved for comparison testing against the old pipeline. Wraps the same algorithm but with StageIV-specific preprocessing (longitude conversion, time shift, negative value clamping). Ported from `_da2` lines 654-668 and `__utils.py` `process_dans_stageiv()`.

2. **Primary reference** (Decision 7): `mrms_pass2_1hr` — MRMS MultiSensor QPE Pass2, gage-corrected hourly data from the same MRMS sensor network. This is the default.

3. **AORC alternative**: selectable via config. Uses AORC hourly precipitation as the reference. The old code already supports this path (`_da2` lines 669-688).

4. **Correction factor bounds** from `constants.py` (01A): `crxn_upper_bound = 20`, `crxn_lower_bound = 0.01`.

5. All functions are pure computation — no file I/O.

### Key Design Decisions

- **Algorithm overview** (from old code analysis):
  1. Resample MRMS PrecipRate to hourly resolution (temporal aggregation via `resample(time="H").mean()`)
  2. Spatially resample hourly MRMS to match the reference product's grid (downsampling from 1 km to reference resolution)
  3. Compute correction factor: `reference / mrms_hourly_at_ref_res`
  4. Handle edge cases: where MRMS is zero, set correction factor to 1; where reference is zero/negative, set correction factor to 1
  5. Enforce bounds: clamp correction factor to `[lower_bound, upper_bound]`
  6. Spatially upsample correction factor back to MRMS resolution
  7. Temporally upsample correction factor from hourly to native MRMS timestep (forward-fill)
  8. Apply: `mrms_corrected = mrms * correction_factor`
  9. Fill gaps: where MRMS is zero but reference has precipitation, substitute reference values (spatially resampled to MRMS resolution, temporally upsampled via forward-fill)

- **QPE Pass2 adaptation**: the old algorithm used StageIV or AORC as the reference. QPE Pass2 is from the same MRMS sensor with gage correction, so it is at the same 1 km spatial resolution. This simplifies steps 2 and 6 (no spatial resampling needed between MRMS and reference). However, the temporal resolution differs (MRMS PrecipRate is 2-min, QPE Pass2 is 1-hour), so temporal alignment is still required.

- **Spatial resampling dependency**: when reference resolution differs from MRMS (as with AORC or StageIV), use `reproject_match()` from 02A. When reference resolution matches (QPE Pass2), spatial resampling is skipped.

- **Grid cell position**: the old code adjusts MRMS grid coordinates from upper-left to center when using AORC (`_da2` lines 601-607). This should be handled by `adjust_gridcell_position()` from 02A before calling bias correction, not inside the bias correction function.

- **No intermediate file writes**: the old code wrote numerous intermediate zarr files to manage memory (`tmp_zarr` pattern throughout `_da2`). The new code should use dask lazy evaluation instead. If memory management is still needed, it should be handled by the workflow orchestration layer (Phase 4), not by the computation functions.

### Success Criteria

- `bias_correct_preciprate()` produces output matching the old algorithm when given the same inputs
- Correction factor is bounded within `[lower_bound, upper_bound]`
- Zero-MRMS / zero-reference edge cases produce correction factor of 1 (no correction)
- Gap filling substitutes reference values where MRMS is zero and reference is non-zero
- Diagnostic DataArrays (correction factor statistics, daily totals, fill fractions) are computed correctly
- `_reference_bias_correction()` replicates the old StageIV-based algorithm for regression testing
- QPE Pass2 path skips unnecessary spatial resampling
- All functions work with dask-backed arrays

---

## Evidence from Codebase

Inspect before implementing:

1. `_old_code_to_refactor/hpc/_da2_resampling_to_same_tstep.py` lines 266-448 — `bias_correct_and_fill_mrms()`. This is the core algorithm (~180 lines). Key steps:
   - Line 275: hourly aggregation of MRMS
   - Line 286: spatial resampling of hourly MRMS to reference grid
   - Lines 297-311: correction factor computation with bounds and zero handling
   - Line 313: spatial upsampling of correction factor back to MRMS resolution
   - Lines 325-347: reference gap filling (where MRMS=0 and ref>0)
   - Lines 360-361: temporal upsampling of correction factor via forward-fill + reindex
   - Line 381: `mrms_corrected = ds_mrms * xds_correction_to_mrms`
   - Line 394: `mrms_filled = mrms_corrected + ref_fill_values`
   - Lines 416-447: diagnostic computation (domain-wide totals, ratios)

2. `_old_code_to_refactor/hpc/_da2_resampling_to_same_tstep.py` lines 450-555 — `process_bias_corrected_dataset()`. Computes correction factor quantiles, mean/min/max daily correction factors, daily totals, reference fill fraction, reference fill hours, and corrected-minus-reference differences.

3. `_old_code_to_refactor/hpc/__utils.py` lines 56-57 — correction factor bounds: `crxn_upper_bound = 20`, `crxn_lower_bound = 0.01`.

4. `_old_code_to_refactor/hpc/__utils.py` lines 78-92 — `process_dans_stageiv()`: StageIV preprocessing (longitude conversion from degrees west to east, negative value clamping, variable renaming, time encoding alignment).

5. `_old_code_to_refactor/hpc/_da2_resampling_to_same_tstep.py` lines 654-688 — reference data loading for both StageIV and AORC paths. The StageIV path includes a 1-hour time shift (`time - pd.Timedelta(1, "hours")`); the AORC path converts negative longitudes to degrees east.

6. `_old_code_to_refactor/hpc/__utils.py` lines 55-56 — `lst_quants = [0.1, 0.5, 0.9]` for correction factor quantiles.

---

## File-by-File Change Plan

### New Files

| File | Purpose |
|------|---------|
| `src/hydro_fetch/process/bias_correction.py` | Bias correction algorithm and diagnostics |
| `tests/test_bias_correction.py` | Unit tests for bias correction |

### Modified Files

| File | Change |
|------|--------|
| `src/hydro_fetch/process/__init__.py` | Ensure module is importable |

---

## Risks and Edge Cases

| Risk | Mitigation |
|------|-----------|
| QPE Pass2 has the same spatial resolution as MRMS PrecipRate — need to verify grid alignment | Check that coordinate values match exactly; if not, `reproject_match()` handles alignment |
| Correction factor can be infinity when MRMS is zero and reference is non-zero | Old code sets factor to 1 when MRMS=0; gap filling handles the non-zero reference separately |
| Division by zero in `reference / mrms` | Use `xr.where(mrms <= 0, 1, reference / mrms)` pattern from old code |
| Very large dask task graphs from multiple spatial resampling + correction steps | The old code managed this with intermediate zarr writes. The new code relies on dask; test with realistic data sizes and add `.persist()` hints if needed |
| Old algorithm behavior when both MRMS and reference are zero | Correction factor = 1 (from the MRMS=0 check), result is 0 * 1 = 0. Correct behavior. |
| Forward-fill of hourly correction factor to 2-min resolution assumes constant correction within the hour | Document this assumption; it matches the old code behavior |
| Difference between StageIV time convention (preceding interval) and MRMS (instantaneous rate) | The old code shifts StageIV time by -1 hour. For QPE Pass2, verify the time convention and apply the appropriate shift. |

---

## Validation Plan

```bash
# Unit tests
conda run -n hydro_fetch pytest tests/test_bias_correction.py -v

# Smoke test
conda run -n hydro_fetch python -c "
from hydro_fetch.process.bias_correction import (
    bias_correct_preciprate,
    compute_correction_diagnostics,
)
print('All imports OK')
"

# Linting
conda run -n hydro_fetch ruff check src/hydro_fetch/process/bias_correction.py
conda run -n hydro_fetch ruff format --check src/hydro_fetch/process/bias_correction.py
```

### Test Cases

1. **Basic correction**: Create synthetic MRMS (2x actual rainfall) and reference data. Verify correction factor ~0.5, corrected values ~reference values.
2. **Zero MRMS, non-zero reference**: Verify gap filling substitutes reference values.
3. **Zero reference, non-zero MRMS**: Verify correction factor is 1 (no correction applied).
4. **Both zero**: Verify result is zero.
5. **Correction factor bounds**: Create data that would produce factor > 20 or < 0.01; verify clamping.
6. **Diagnostic outputs**: Verify mean/max correction factor, daily totals, fill fraction computations.
7. **QPE Pass2 path**: Same spatial resolution as MRMS — verify spatial resampling is skipped.
8. **AORC path**: Different spatial resolution — verify spatial resampling is applied.
9. **Dask compatibility**: All tests with dask-backed arrays.
10. **Regression test against `_reference_bias_correction()`**: Run old StageIV algorithm and new QPE Pass2 algorithm on the same MRMS data, verify structural consistency.

---

## Documentation and Tracker Updates

- Update `full_codebase_refactor.md`: mark `_da2` bias correction portions as ported in tracking table
- Update `work_chunks/README.md`: mark 02C as complete

---

## Definition of Done

- [ ] `src/hydro_fetch/process/bias_correction.py` implemented with `bias_correct_preciprate()` and `compute_correction_diagnostics()`
- [ ] QPE Pass2 is the default reference product; AORC is selectable
- [ ] `_reference_bias_correction()` preserves the old StageIV algorithm for comparison testing
- [ ] Correction factor bounds are enforced from `constants.py`
- [ ] Edge cases (zero MRMS, zero reference, both zero) handled correctly
- [ ] Gap filling inserts reference values where MRMS=0 and reference>0
- [ ] All functions are pure computation — no file I/O
- [ ] All functions work with dask-backed arrays
- [ ] Diagnostic DataArrays (correction factor stats, daily totals, fill fractions) are computed
- [ ] Unit tests cover all edge cases and both reference product paths
- [ ] `ruff check` and `ruff format` pass
- [ ] Type hints and docstrings on all public functions
- [ ] **Move this document to `../implemented/` once all boxes above are checked**
