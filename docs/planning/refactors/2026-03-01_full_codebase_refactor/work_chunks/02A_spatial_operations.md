# Work Chunk 02A: Spatial Operations (Clip, Resample, Reproject)

**Phase**: 2A — Core Computation
**Created**: 2026-03-01

---

## Before Proceeding

- [`full_codebase_refactor.md`](../full_codebase_refactor.md) — master plan
- [`CONTRIBUTING.md`](../../../../CONTRIBUTING.md) — development philosophy
- [`07_old_code_porting_audit.md`](07_old_code_porting_audit.md) — record any deferred decisions

**Prerequisites**: Work chunks 01D (I/O layer) and 01E (GIS I/O) complete.

---

## Task Understanding

### Requirements

1. **`src/hydro_fetch/process/spatial.py`** — pure spatial computation functions operating on xarray objects:
   - `clip_to_bounds(ds, bounds, lat_dim, lon_dim)` — clip an xarray Dataset to a bounding box (min_lat, max_lat, min_lon, max_lon). Replaces `clip_ds_to_another_ds()` and `clip_ds_to_transposition_domain()` from the old code.
   - `reproject_match(ds, target_ds, resampling_method)` — reproject and spatially resample `ds` to match the grid of `target_ds` using rioxarray. Replaces `spatial_resampling()` from `__utils.py`.
   - `spatial_resample(ds, target_ds, lat_dim, lon_dim, fill_value)` — higher-level function that clips, sets CRS, and reprojects in one call. Wraps `clip_to_bounds()` + `reproject_match()`.

2. All functions receive xarray Datasets or DataArrays and return xarray objects — no file I/O.

3. Must handle rioxarray CRS assignment, spatial dimension naming (`x`/`y` vs `latitude`/`longitude`), and the `reproject_match` workflow.

4. Must handle the MRMS coordinate convention: the old code stores longitudes in degrees east (converted from degrees west via `360 - x`), and grid cell positions may represent upper-left corners rather than centers (see `_da2` lines 601-607 for the center-adjustment logic).

5. Must handle fill values for areas outside the overlap of source and target grids (old code used `missingfillval=0` and checked for `>=3.403e+37` sentinel values from rasterio).

### Key Design Decisions

- **No file I/O**: these functions are pure computation. Data loading and writing are handled by the I/O layer (01D/01E).
- **CRS handling**: functions should accept a `crs` parameter (defaulting to the value from the dataset's `rio.crs` if present). The old code hardcoded `epsg:4326` — the new code should be CRS-agnostic but default to EPSG:4326 for MRMS data.
- **Dimension naming**: the old code renamed `latitude`/`longitude` to `y`/`x` before rioxarray operations, then renamed back. The new code should handle this internally and preserve the caller's dimension names.
- **Resampling method**: the old code used `rasterio.enums.Resampling.average` for downsampling. The new code should accept a `resampling` parameter with `average` as the default, but allow callers to specify `nearest`, `bilinear`, etc.
- **Clip modes**: per Decision 2, support both `bbox` (bounding box only) and `mask` (bbox + polygon mask). The `clip_to_bounds()` function handles bbox; polygon masking is a separate step that uses the AOI from the GIS I/O layer (01E).
- **Grid cell position adjustment**: the old code adjusted MRMS grid coordinates from upper-left to center when using AORC as the bias correction reference. This adjustment should be a separate utility function `adjust_gridcell_position(ds, from_position, to_position, grid_spacing)` rather than embedded in spatial operations.

### Success Criteria

- `clip_to_bounds()` correctly subsets a dataset to a bounding box, dropping out-of-bounds coordinates
- `reproject_match()` reprojects a dataset to match another dataset's grid using rioxarray
- `spatial_resample()` chains clip + reproject in a single call
- All functions preserve xarray attributes and coordinate metadata
- All functions work with dask-backed arrays (lazy evaluation)
- No hardcoded CRS, dimension names, or file paths
- Fill values for out-of-overlap areas are handled without sentinel value hacks (`3.403e+37`)

---

## Evidence from Codebase

Inspect before implementing:

1. `_old_code_to_refactor/hpc/__utils.py` lines 94-129 — `clip_ds_to_another_ds()` and `spatial_resampling()`. These are the primary functions to port.
2. `_old_code_to_refactor/hpc/_da2_resampling_to_same_tstep.py` lines 209-213 — `clip_ds_to_transposition_domain()` clips to a GeoDataFrame's bounds with a buffer. This is a specific use of `clip_to_bounds()`.
3. `_old_code_to_refactor/hpc/_da2_resampling_to_same_tstep.py` lines 601-607 — grid cell position adjustment from upper-left to center when AORC is the bias correction reference.
4. `_old_code_to_refactor/hpc/_da2_resampling_to_same_tstep.py` lines 286, 313, 327, 548 — multiple calls to `spatial_resampling()` for upsampling and downsampling between MRMS and reference grids.
5. `_old_code_to_refactor/hpc/__utils.py` lines 44-47 — MRMS CONUS grid bounds (already captured in constants.py from 01A).
6. `_old_code_to_refactor/hpc/__utils.py` line 128 — fill value handling: `xr.where(xds_to_resampled>=3.403e+37, x=missingfillval, y=xds_to_resampled)`. The `3.403e+37` is rasterio's default nodata for float32. The new code should use `xr.where(xds.isnull(), fill_value, xds)` or rioxarray's built-in nodata handling instead.

---

## File-by-File Change Plan

### New Files

| File | Purpose |
|------|---------|
| `src/hydro_fetch/process/spatial.py` | Spatial operations: clip, reproject, resample |
| `tests/test_spatial.py` | Unit tests for spatial operations |

### Modified Files

| File | Change |
|------|--------|
| `src/hydro_fetch/process/__init__.py` | Ensure module is importable |

---

## Risks and Edge Cases

| Risk | Mitigation |
|------|-----------|
| rioxarray requires `x`/`y` dimension names for spatial operations | Handle dimension renaming internally; restore original names before returning |
| Dask-backed arrays may not work with all rioxarray operations | Test with both in-memory and dask arrays; document any operations that require `.load()` |
| CRS mismatch between MRMS (EPSG:4326) and user-provided AOI polygons | Validate CRS consistency in the function; raise `ProcessingError` on mismatch with actionable message |
| The `3.403e+37` sentinel value from rasterio may appear in unexpected places | Use `rioxarray.set_nodata()` and `xr.where(ds.isnull(), ...)` instead of hardcoded sentinel checks |
| MRMS longitude convention (degrees east, 230-300 range) vs standard (-130 to -60) | Document the expected convention; provide a helper if needed. The old code adds 360 to convert from degrees west — the new code should handle both conventions. |
| Grid cell position (upper-left vs center) affects spatial alignment | Make `adjust_gridcell_position()` explicit and require callers to state their grid cell convention |

---

## Validation Plan

```bash
# Unit tests
conda run -n hydro_fetch pytest tests/test_spatial.py -v

# Smoke test: import and basic function signatures
conda run -n hydro_fetch python -c "
from hydro_fetch.process.spatial import clip_to_bounds, reproject_match, spatial_resample
print('All imports OK')
"

# Linting
conda run -n hydro_fetch ruff check src/hydro_fetch/process/spatial.py
conda run -n hydro_fetch ruff format --check src/hydro_fetch/process/spatial.py
```

### Test Cases

1. **clip_to_bounds**: Create a 10x10 synthetic grid, clip to a 5x5 subregion, verify dimensions and coordinate ranges.
2. **reproject_match**: Create two grids at different resolutions (e.g., 0.01 deg and 0.05 deg), reproject the fine grid to the coarse grid, verify output shape matches target.
3. **spatial_resample**: End-to-end test combining clip + reproject.
4. **Dask compatibility**: Run all tests with dask-backed arrays and verify lazy evaluation is preserved.
5. **Fill value handling**: Verify that areas outside the source grid's extent are filled with the specified fill value (not rasterio sentinel values).

---

## Documentation and Tracker Updates

- Update `full_codebase_refactor.md`: mark `__utils.py` spatial functions as ported in the tracking table
- Update `work_chunks/README.md`: mark 02A as complete

---

## Definition of Done

- [ ] `src/hydro_fetch/process/spatial.py` implemented with `clip_to_bounds()`, `reproject_match()`, `spatial_resample()`
- [ ] `adjust_gridcell_position()` utility implemented for MRMS upper-left-to-center adjustment
- [ ] All functions are pure computation — no file I/O
- [ ] All functions accept and return xarray Datasets/DataArrays
- [ ] All functions work with dask-backed arrays
- [ ] Dimension names are preserved (internal `y`/`x` renaming is transparent to callers)
- [ ] CRS is configurable, not hardcoded
- [ ] Fill values use xarray/rioxarray nodata handling, not sentinel value checks
- [ ] Unit tests pass
- [ ] `ruff check` and `ruff format` pass
- [ ] Type hints and docstrings on all public functions
- [ ] **Move this document to `../implemented/` once all boxes above are checked**
