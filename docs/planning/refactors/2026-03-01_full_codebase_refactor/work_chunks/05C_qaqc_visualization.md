# Work Chunk 05C: QA/QC and Comparison Visualization

**Phase**: 5C — Visualization and Cross-Comparison (QA/QC and Gage Comparison)
**Created**: 2026-03-01

---

## Before Proceeding

Review the following documents before making any edits to plans or writing any code:

- [`full_codebase_refactor.md`](../full_codebase_refactor.md) — master refactor plan; update it if any decisions made here affect the overall plan.
- [`CONTRIBUTING.md`](../../../../CONTRIBUTING.md) — development philosophy.
- [`07_old_code_porting_audit.md`](07_old_code_porting_audit.md) — record any deferred old code decisions here.

**Prerequisites**: Work chunks 02D (QA/QC), 02E (point extraction), and 05A (product comparison) complete.

---

## Task Understanding

### Requirements

1. **`src/hydro_fetch/viz/qaqc.py`** — QA/QC visualization functions:
   - **Hexbin plots**: gage observation vs gridded product values, with density coloring. Ported from `local/a0_qaqc_bias_corrected_mrms_data.py`.
   - **Multi-panel QA/QC maps**: spatial maps of QA/QC variables (correction factors, missing duration, flagged cells) for each date or aggregation period. Ported from `local/a0_*`.
   - **Data gap visualization**: spatial and temporal maps showing `missing_duration_min` from Decision 6. Highlights periods and regions with poor data coverage.

2. **`src/hydro_fetch/viz/comparison.py`** — gage-vs-gridded comparison visualization:
   - **Event-level scatter plots**: gage event total vs gridded product event total, with 1:1 line and linear regression. Ported from `local/b_generate_visualizations_of_gaga_vs_mrms_events.py`.
   - **Per-gage time series**: overlay of gage observation and gridded product time series at individual gage locations.
   - **Spatial map of per-gage bias**: map showing bias (gridded minus gage) at each gage location, colored by magnitude.
   - **Cross-product comparison panels**: side-by-side scatter plots for the same gage data compared against multiple products (e.g., raw MRMS vs corrected MRMS vs AORC).

3. **Porting scope**:
   - `local/a0_qaqc_bias_corrected_mrms_data.py` -> `viz/qaqc.py`
   - `local/b_generate_visualizations_of_gaga_vs_mrms_events.py` -> `viz/comparison.py`
   - Comparison visualization logic from `local/d_compare_gaga_vs_mrms_events_vs_stageIV.py` -> `viz/comparison.py` (metric computation is in 05A `compare/products.py`)

### Key Design Decisions

- **Separation of computation and visualization**: Comparison metrics are computed in `compare/products.py` (05A). This module only handles plotting. The viz module consumes DataFrames/Datasets of pre-computed metrics.
- **Parameterized for any product**: All plotting functions accept product name as a parameter for titles, legends, and filenames. No hardcoding to MRMS or StageIV.
- **Consistent style**: All plots use a shared matplotlib style configuration (font sizes, figure dimensions, DPI). Consider a `viz/_style.py` module or matplotlib style file.
- **Old code used `from __filepaths import *`**: All filepath logic is replaced by the config/path management modules (01B, 01C). No star imports.

### Success Criteria

- Hexbin plot: can generate gage-vs-gridded density plot for any product
- Event scatter: can plot event totals with regression line and 1:1 reference
- Gap visualization: spatial map of missing duration is readable and informative
- Multi-product panels: can show 2-5 products side-by-side
- All plots save to configured output directory with descriptive filenames

---

## Evidence from Codebase

Inspect before implementing:

1. `_old_code_to_refactor/local/a0_qaqc_bias_corrected_mrms_data.py`:
   - `plot_multipanel_plot()`: iterates over aggregation coordinates, creates multi-panel subplots
   - Uses `plt.subplots()` with dynamic grid sizing (`ncols = ceil(sqrt(len(vars)))`)
   - Loads zarr files of bias-corrected MRMS QA/QC data
   - Plots correction factors, precipitation values, anomalies
2. `_old_code_to_refactor/local/b_generate_visualizations_of_gaga_vs_mrms_events.py`:
   - Loads gage event CSV and MRMS at-gage xarray datasets
   - Creates time masks to exclude problematic years (2012-2014)
   - `inches_per_mm = 1/25.4` for unit conversion
   - Plots use matplotlib with LaTeX text rendering (`plt.rcParams['text.usetex'] = True`)
   - Customized font sizes: title=16, axes=14, ticks=12, legend=16
3. `_old_code_to_refactor/local/d_compare_gaga_vs_mrms_events_vs_stageIV.py`:
   - Similar imports and style to `b_*`
   - `n_largest = 15` -- shows largest events
   - Uses scipy.stats for regression
   - Event comparison with three datasets simultaneously
   - Uses cartopy for spatial plots with coastline and subcatchment overlays
4. Old code matplotlib parameters: `text.usetex = True`, various `rc` settings for font sizes

---

## File-by-File Change Plan

### New Files

| File | Purpose |
|------|---------|
| `src/hydro_fetch/viz/qaqc.py` | QA/QC visualization: hexbin plots, QA/QC maps, data gap visualization |
| `src/hydro_fetch/viz/comparison.py` | Comparison visualization: event scatter, per-gage time series, spatial bias maps, multi-product panels |

### Modified Files

| File | Change |
|------|--------|
| `src/hydro_fetch/viz/__init__.py` | Export visualization functions |
| `full_codebase_refactor.md` | Update Phase 5 status; update tracking table for `local/a0_*`, `local/b_*`, `local/d_*` |

---

## Risks and Edge Cases

| Risk | Mitigation |
|------|-----------|
| LaTeX text rendering (`text.usetex = True`) requires a LaTeX installation | Make LaTeX rendering optional (default off); use matplotlib's built-in mathtext for simple formatting |
| Old code has Norfolk-specific gage IDs and event indices hardcoded | Parameterize all gage and event selection; no hardcoded IDs |
| Large number of gages or events produces unreadable plots | Add configurable `n_largest` parameter; support pagination or summary views for large datasets |
| Unit conversion (mm to inches) is scattered in old code | Centralize unit conversion in constants or a utility; use explicit parameter for output units |
| Cartopy coastline/subcatchment shapefiles may not be available | Fall back to cartopy built-in coastlines; subcatchment overlay is optional |

---

## Validation Plan

```bash
# Import test
conda run -n hydro_fetch python -c "
from hydro_fetch.viz.qaqc import plot_hexbin_comparison
from hydro_fetch.viz.comparison import plot_event_scatter
print('Import OK')
"

# Generate test plots with synthetic data
conda run -n hydro_fetch python -c "
import numpy as np
import pandas as pd
# Create synthetic gage vs gridded data
# df = pd.DataFrame({'gage_mm': np.random.exponential(5, 100), 'gridded_mm': np.random.exponential(5, 100)})
# plot_hexbin_comparison(df, 'gage_mm', 'gridded_mm', product_name='test', output_path='/tmp/test_hexbin.png')
"

# Unit tests
conda run -n hydro_fetch pytest tests/test_viz.py -v -k "qaqc or comparison"

# Ruff
conda run -n hydro_fetch ruff check src/hydro_fetch/viz/
conda run -n hydro_fetch ruff format --check src/hydro_fetch/viz/
```

---

## Documentation and Tracker Updates

- Update `full_codebase_refactor.md`: mark 05C status; mark Phase 5 complete; update tracking table for `local/a0_*`, `local/b_*`, `local/d_*`
- Record in `07_old_code_porting_audit.md` any old visualization logic intentionally not ported

---

## Definition of Done

- [ ] `src/hydro_fetch/viz/qaqc.py` implements hexbin plots, QA/QC maps, and data gap visualization
- [ ] `src/hydro_fetch/viz/comparison.py` implements event scatter, per-gage time series, spatial bias maps, multi-product panels
- [ ] All plotting functions parameterized by product name (not hardcoded to MRMS/StageIV)
- [ ] LaTeX rendering is optional (not required)
- [ ] No hardcoded gage IDs, event indices, or Norfolk-specific values
- [ ] Unit conversion centralized (not scattered `inches_per_mm` constants)
- [ ] Configurable plot parameters (figure size, DPI, n_largest, colorbar bounds)
- [ ] Plots save to configured output directory
- [ ] Unit tests with synthetic data
- [ ] `ruff check` and `ruff format` pass
- [ ] **Move this document to `../implemented/` once all boxes above are checked**
