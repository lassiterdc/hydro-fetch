# Work Chunk 05B: Annual Statistics Plots

**Phase**: 5B — Visualization and Cross-Comparison (Annual Statistics)
**Created**: 2026-03-01

---

## Before Proceeding

Review the following documents before making any edits to plans or writing any code:

- [`full_codebase_refactor.md`](../full_codebase_refactor.md) — master refactor plan; update it if any decisions made here affect the overall plan.
- [`CONTRIBUTING.md`](../../../../CONTRIBUTING.md) — development philosophy.
- [`07_old_code_porting_audit.md`](07_old_code_porting_audit.md) — record any deferred old code decisions here.

**Prerequisites**: Work chunk 02F (annual statistics computation) complete.

---

## Task Understanding

### Requirements

1. **`src/hydro_fetch/viz/annual_stats.py`** — generate annual statistics visualizations:

   **Plot types**:
   - **Spatial maps of annual statistics**: max precipitation, mean annual total, standard deviation — rendered as CONUS or AOI-extent maps using cartopy
   - **Anomaly maps**: deviation of each year from the multi-year mean
   - **Time series of annual totals**: line/bar chart of spatially-averaged annual precipitation over the analysis period
   - **Multi-panel comparison**: side-by-side annual statistics maps for different products

2. **Porting from old code**:
   - `hpc/_hb_generate_annual_statistics_plots.py` — MRMS annual statistics plots (CONUS extent)
   - `hpc/_hb2_generate_annual_statistics_plots_stageIV.py` — StageIV variant (replace StageIV with QPE Pass2/AORC)
   - `local/_hb_generate_annual_statistics_plots.py` — local variant (AOI extent)

3. **Map rendering**:
   - Uses matplotlib + cartopy for geographic projections
   - State boundaries overlay (from shapefile)
   - Configurable colorbar (percentile-based bounds from old code: `cbar_percentile = 0.98`)
   - Plot size and font parameters configurable (old code: `plt_hb_width = 14`)

4. **`src/hydro_fetch/viz/__init__.py`** — package init.

### Key Design Decisions

- **Unified plotting function**: Instead of separate scripts for MRMS vs StageIV vs local, a single parameterized function accepts any product's annual statistics dataset and produces standardized plots. Product name is used for titles and filenames.
- **Cartopy for maps**: Consistent with old code. Requires state boundary shapefile and optionally a NEXRAD boundary shapefile as inputs.
- **Configurable plot parameters**: Plot dimensions, colorbar percentiles, rounding intervals, and font sizes are passed as arguments (not hardcoded module-level globals as in old code).
- **Output format**: Plots saved as PNG (configurable DPI). Output directory from pipeline config.

### Success Criteria

- Can generate spatial map of annual max precipitation for a product
- Can generate anomaly maps (year vs multi-year mean)
- Can generate time series of annual totals
- Plots include state boundaries and proper geographic projection
- Plot function works for any product (not hardcoded to MRMS or StageIV)

---

## Evidence from Codebase

Inspect before implementing:

1. `_old_code_to_refactor/hpc/_hb_generate_annual_statistics_plots.py`:
   - Imports: xarray, matplotlib, geopandas, rioxarray, dask
   - Loads annual statistics NetCDF (`mrms_nc_preciprate_yearly_singlefile.nc`)
   - Loads state shapefile and NEXRAD boundary shapefile
   - Chunking parameters from `__utils.py` (`return_chunking_parameters("hb")`)
   - Colorbar: percentile-based (`cbar_percentile = 0.98`, `nearest_int_for_rounding = 50`)
   - Plot dimensions: `width = __utils.plt_hb_width` (14)
   - Excludes 2013-2014 from mean for anomaly plots
2. `_old_code_to_refactor/hpc/_hb2_generate_annual_statistics_plots_stageIV.py` — identical structure, different input dataset
3. `_old_code_to_refactor/local/_hb_generate_annual_statistics_plots.py` — similar but for AOI extent
4. `_old_code_to_refactor/hpc/__utils.py` lines 67-69 — plot parameters: `cbar_percentile`, `nearest_int_for_rounding`, `plt_hb_width`, `plt_hb_height`
5. `src/hydro_fetch/statistics/annual.py` (from 02F) — produces the datasets that this module visualizes

---

## File-by-File Change Plan

### New Files

| File | Purpose |
|------|---------|
| `src/hydro_fetch/viz/__init__.py` | Package init |
| `src/hydro_fetch/viz/annual_stats.py` | Annual statistics visualization functions |

### Modified Files

| File | Change |
|------|--------|
| `full_codebase_refactor.md` | Update Phase 5 status; update tracking table for `_hb*` scripts |

---

## Risks and Edge Cases

| Risk | Mitigation |
|------|-----------|
| Cartopy requires external data (coastlines, state boundaries) | Ship required shapefiles in the cases directory or use cartopy's built-in natural earth features; document shapefile requirements |
| CONUS-extent plots are very large in memory | Use dask for lazy loading of annual statistics; compute colorbar bounds on a sample, then render with full data |
| Colorbar percentile approach may produce poor bounds for skewed distributions | Allow user override of vmin/vmax in addition to percentile-based automatic bounds |
| Old code excludes 2013-2014 from anomaly computation — Norfolk-specific? | Make year exclusion configurable (list of years to exclude from mean computation), not hardcoded |
| StageIV-specific plots must be replaced but not lost | Port the parameterized version; record in 07 audit that StageIV-specific variant is superseded by the generic version |

---

## Validation Plan

```bash
# Import test
conda run -n hydro_fetch python -c "
from hydro_fetch.viz.annual_stats import plot_annual_statistics_map
print('Import OK')
"

# Generate a test plot with synthetic data
conda run -n hydro_fetch python -c "
import xarray as xr
import numpy as np
# Create synthetic annual stats dataset
# ds = xr.Dataset(...)
# plot_annual_statistics_map(ds, product_name='test', output_dir='/tmp/test_plots')
"

# Unit tests (check that functions run without error on synthetic data)
conda run -n hydro_fetch pytest tests/test_viz.py -v -k "annual"

# Ruff
conda run -n hydro_fetch ruff check src/hydro_fetch/viz/
conda run -n hydro_fetch ruff format --check src/hydro_fetch/viz/
```

---

## Documentation and Tracker Updates

- Update `full_codebase_refactor.md`: mark 05B status; update tracking table for `_hb_generate_annual_statistics_plots.py`, `_hb2_generate_annual_statistics_plots_stageIV.py`, `local/_hb_generate_annual_statistics_plots.py`
- Record in `07_old_code_porting_audit.md` that StageIV-specific plot script is superseded by parameterized version

---

## Definition of Done

- [ ] `src/hydro_fetch/viz/annual_stats.py` implements annual statistics plotting functions
- [ ] Spatial maps: annual max, mean total, standard deviation, anomalies
- [ ] Time series: annual totals over analysis period
- [ ] Multi-panel comparison across products
- [ ] Uses cartopy for geographic projection with state boundaries
- [ ] Colorbar bounds configurable (percentile-based + manual override)
- [ ] Plot parameters configurable (no hardcoded globals)
- [ ] Works for any product (parameterized by product name)
- [ ] Year exclusion for anomaly computation is configurable
- [ ] Unit tests with synthetic data
- [ ] `ruff check` and `ruff format` pass
- [ ] **Move this document to `../implemented/` once all boxes above are checked**
