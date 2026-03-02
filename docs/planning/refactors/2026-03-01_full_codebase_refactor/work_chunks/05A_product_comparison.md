# Work Chunk 05A: Product Cross-Comparison

**Phase**: 5A — Visualization and Cross-Comparison (Computation)
**Created**: 2026-03-01

---

## Before Proceeding

Review the following documents before making any edits to plans or writing any code:

- [`full_codebase_refactor.md`](../full_codebase_refactor.md) — master refactor plan; update it if any decisions made here affect the overall plan.
- [`CONTRIBUTING.md`](../../../../CONTRIBUTING.md) — development philosophy.
- [`07_old_code_porting_audit.md`](07_old_code_porting_audit.md) — record any deferred old code decisions here.

**Prerequisites**: Work chunks 02C (bias correction) and 02E (point extraction) complete.

---

## Task Understanding

### Requirements

1. Create `src/hydro_fetch/compare/products.py` — a pure computation module that compares precipitation products at gage locations:
   - Compare up to 4 products at the same set of gage sites: `mrms_2min`, `mrms_pass2_1hr`, `mrms_crctd_w_pass2_2min` (or `mrms_crctd_w_aorc_2min`), and `aorc_1hr`
   - All products must first be extracted at gage locations (02E) and resampled to a common temporal resolution before comparison
   - Compute comparison metrics: bias (mean error), relative bias (percent bias), RMSE, correlation coefficient (Pearson), scatter index, and Nash-Sutcliffe efficiency (NSE)
   - Produce comparison DataFrames suitable for downstream plotting (05B/05C) and export to CSV

2. Create `src/hydro_fetch/compare/__init__.py` — package init; exports comparison functions.

3. Port logic from old code:
   - `_old_code_to_refactor/local/a2_create_mrms_vs_gage_csv.py` — extracts MRMS at gage locations and creates comparison CSVs with timezone handling
   - `_old_code_to_refactor/local/d_compare_gaga_vs_mrms_events_vs_stageIV.py` — multi-product event-level comparison at gage sites (MRMS vs gage vs StageIV); StageIV references must be replaced with `mrms_pass2_1hr` or `aorc_1hr` per Decision 7

4. This module is **pure computation**: no plotting, no direct file I/O. Accepts DataFrames/xarray objects as input and returns DataFrames as output. File reading/writing is the caller's responsibility via the I/O layer (01D).

### Key Design Decisions

- **Common temporal resolution**: Before comparison, all products must be at the same timestep. For `mrms_2min` vs `aorc_1hr`, this means aggregating 2-min data to hourly. The comparison module accepts pre-resampled data — callers handle resampling via 02B before calling comparison functions.
- **Gage data as ground truth**: Gage observations are the reference for all bias/error metrics. Products are compared TO gages (gage is always the "observed" term in metric formulas). Product-to-product metrics are also computed for completeness.
- **Event-based and continuous metrics**: Support both continuous time-series comparison (full period statistics) and event-based comparison (per-storm metrics using a precipitation threshold to define events). The old code in `d_compare_gaga_vs_mrms_events_vs_stageIV.py` had event detection logic that should be ported.
- **Output format**: Comparison results are returned as pandas DataFrames with a consistent long-format schema: columns for `gage_id`, `product`, `metric`, `value`, `time_period`. This tabular format is easy to pivot for plotting and export to CSV.
- **No StageIV references**: The old code compared against StageIV. In the refactored pipeline, `mrms_pass2_1hr` replaces StageIV as the gage-corrected reference product (Decision 7). AORC is available as an alternative reference.

### Success Criteria

- `from hydro_fetch.compare.products import compute_comparison_metrics` is importable
- Given two aligned time series (product and gage), correctly computes bias, relative bias, RMSE, correlation, scatter index, and NSE
- Event detection identifies precipitation events above a configurable threshold
- Output DataFrames have a consistent, documented schema
- Metrics match hand-computed values for a small synthetic test dataset
- No plotting code in this module — pure computation only

---

## Evidence from Codebase

Inspect before implementing:

1. `_old_code_to_refactor/local/a2_create_mrms_vs_gage_csv.py` — creates MRMS-vs-gage CSV by extracting gridded MRMS at gage locations; contains gage data loading, spatial matching, timezone handling (UTC), and CSV writing logic
2. `_old_code_to_refactor/local/d_compare_gaga_vs_mrms_events_vs_stageIV.py` — multi-product event comparison; contains event detection (threshold-based), per-event accumulation totals (`n_largest = 15`), `scipy.stats` for statistical comparisons, and scatter/map plotting (plotting not ported here)
3. `_old_code_to_refactor/hpc/_i_extract_mrms_at_gages.py` — HPC version of gage extraction; contains nearest-gridcell lookup logic (ported in 02E)
4. `src/hydro_fetch/process/extraction.py` (from 02E) — point extraction module; provides the extracted time series this module consumes
5. `src/hydro_fetch/process/temporal.py` (from 02B) — temporal resampling; callers use this to align product resolutions before comparison
6. `src/hydro_fetch/process/bias_correction.py` (from 02C) — produces the `mrms_crctd_w_pass2_2min` and `mrms_crctd_w_aorc_2min` products compared here
7. Decision 1 in master plan — canonical product names (`mrms_2min`, `mrms_pass2_1hr`, `mrms_crctd_w_pass2_2min`, `mrms_crctd_w_aorc_2min`, `aorc_1hr`)
8. Decision 7 in master plan — bias correction reference product (QPE Pass2 replaces StageIV)

---

## File-by-File Change Plan

### New Files

| File | Purpose |
|------|---------|
| `src/hydro_fetch/compare/__init__.py` | Package init; export `compute_comparison_metrics`, `detect_events`, `compute_event_metrics` |
| `src/hydro_fetch/compare/products.py` | Comparison metrics (bias, relative bias, RMSE, correlation, NSE, scatter index), event detection, per-event accumulation, multi-product comparison DataFrame generation |

### Modified Files

| File | Change |
|------|--------|
| `full_codebase_refactor.md` | Update Phase 5 status; mark 05A as in-progress/complete; update tracking table for `local/a2_*` and `local/d_compare_*` |
| `07_old_code_porting_audit.md` | Record that `a2_create_mrms_vs_gage_csv.py` computation logic is ported; record that `d_compare_gaga_vs_mrms_events_vs_stageIV.py` computation logic is ported with StageIV replaced by Pass2/AORC; note that plotting from both files is deferred to 05B/05C |

---

## Risks and Edge Cases

| Risk | Mitigation |
|------|-----------|
| Temporal alignment errors: comparing products at different timesteps produces meaningless metrics | Require that inputs are pre-aligned to a common time index; raise `ValueError` if time dimensions do not match |
| Missing data in one product but not another skews metrics | Drop NaN-paired observations before computing metrics; report the fraction of valid observation pairs alongside each metric |
| Event detection threshold is subjective and may differ from old code | Make threshold configurable with a sensible default (e.g., 0.1 mm/hr); document the old code's threshold value for reference |
| Old code's StageIV comparison logic may not map cleanly to Pass2 | Pass2 is hourly like StageIV and shares the same MRMS spatial grid; the comparison logic should port directly with only the data source changing |
| Large number of gages times products times metrics produces wide DataFrames | Use long-format DataFrames (one row per gage-product-metric combination); pivot to wide format only for specific plotting needs in 05B/05C |
| Gage data format/source is not yet defined in the new pipeline | The comparison module accepts pandas DataFrames as input — gage data loading is the caller's responsibility. Document the expected input schema (columns: `time`, `gage_id`, `precip_mm`) |

---

## Validation Plan

```bash
# Imports work
conda run -n hydro_fetch python -c "
from hydro_fetch.compare.products import compute_comparison_metrics, detect_events
print('Import OK')
"

# Unit tests with synthetic data
conda run -n hydro_fetch pytest tests/test_compare.py -v

# Verify metrics against hand-computed values
conda run -n hydro_fetch python -c "
import numpy as np
import pandas as pd
from hydro_fetch.compare.products import compute_comparison_metrics

obs = pd.Series([1.0, 2.0, 3.0, 4.0, 5.0])
pred = pd.Series([1.1, 2.2, 2.8, 4.1, 5.3])
metrics = compute_comparison_metrics(obs, pred)
print(f'Bias: {metrics[\"bias\"]:.4f}')
print(f'RMSE: {metrics[\"rmse\"]:.4f}')
print(f'Correlation: {metrics[\"correlation\"]:.4f}')
print(f'NSE: {metrics[\"nse\"]:.4f}')

# Identical inputs should give perfect scores
perfect = compute_comparison_metrics(obs, obs)
assert perfect['bias'] == 0.0
assert perfect['rmse'] == 0.0
assert perfect['correlation'] == 1.0
assert perfect['nse'] == 1.0
print('Perfect-score sanity check: PASSED')
"

# Ruff passes
conda run -n hydro_fetch ruff check src/hydro_fetch/compare/
conda run -n hydro_fetch ruff format --check src/hydro_fetch/compare/
```

---

## Definition of Done

- [ ] `src/hydro_fetch/compare/__init__.py` created with exports
- [ ] `src/hydro_fetch/compare/products.py` implemented with comparison metric functions
- [ ] Metrics computed: bias, relative bias, RMSE, Pearson correlation, scatter index, Nash-Sutcliffe efficiency
- [ ] Event detection with configurable precipitation threshold
- [ ] Per-event accumulation and metric computation ported from old code
- [ ] Multi-product comparison: accepts list of product DataFrames + gage DataFrame, returns unified comparison DataFrame
- [ ] Output DataFrames have consistent long-format schema (`gage_id`, `product`, `metric`, `value`, `time_period`)
- [ ] No plotting code — pure computation only
- [ ] Handles NaN/missing data gracefully (drop pairs, report valid fraction)
- [ ] Raises `ValueError` on temporal misalignment between inputs
- [ ] Unit tests with synthetic data verify metric correctness (including perfect-score edge case)
- [ ] Old code references documented in `07_old_code_porting_audit.md` (StageIV replaced with Pass2/AORC)
- [ ] `ruff check` and `ruff format` pass
- [ ] **Move this document to `../implemented/` once all boxes above are checked**
