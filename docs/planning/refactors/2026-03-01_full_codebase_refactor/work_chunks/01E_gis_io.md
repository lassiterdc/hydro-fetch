# Work Chunk 01E: GIS I/O with Clipping

**Phase**: 1E — Foundation
**Created**: 2026-03-01

---

## Before Proceeding

- [`full_codebase_refactor.md`](../full_codebase_refactor.md) — master plan
- [`CONTRIBUTING.md`](../../../../CONTRIBUTING.md) — development philosophy
- [`07_old_code_porting_audit.md`](07_old_code_porting_audit.md) — record any deferred decisions

**Prerequisite**: Work chunk 01D complete.

---

## Task Understanding

### Requirements

1. **`src/hydro_fetch/io/gis_io.py`** — GIS vector I/O and spatial clipping:
   - `read_vector(path) -> gpd.GeoDataFrame` — GIS-agnostic vector file reader supporting shapefile, GeoJSON, GeoPackage, and any format readable by `geopandas.read_file()`. Raises `ProcessingError` with file path context on failure.
   - `clip_to_aoi(ds, aoi_gdf, clip_mode) -> xr.Dataset` — clip an xarray Dataset to an area of interest:
     - **Step 1 (both modes)**: clip to the bounding box of the AOI polygon. This reduces the grid from CONUS-scale to a regional extent.
     - **Step 2 (mask mode only)**: apply the polygon mask, setting cells outside the AOI to NaN.
     - `clip_mode` is `Literal["bbox", "mask"]` per Decision 2.
   - `reproject_to_match(gdf, target_crs) -> gpd.GeoDataFrame` — reproject a GeoDataFrame to match a target CRS. Used when the AOI CRS differs from the data CRS.

### Key Design Decisions

- **Two-step clipping per Decision 2** — `mask` mode is a superset of `bbox` mode. Both always start with bounding box clipping (for dimension reduction), then `mask` optionally applies the polygon mask. This means calling `clip_to_aoi` with `clip_mode="mask"` on CONUS data first extracts the bbox region, then masks. This is more efficient than masking the full CONUS grid.
- **CRS handling** — the AOI vector file may be in a different CRS than the gridded data (which is typically EPSG:4326 for MRMS). The clipping function must detect CRS mismatch and reproject the AOI to match the data before clipping. The data is never reprojected to match the AOI — always the other way around.
- **GIS-agnostic input per Decision 2** — `read_vector()` uses `geopandas.read_file()` which handles format detection automatically. No format-specific code paths.
- **rioxarray for spatial operations** — the old code used `rioxarray` for CRS assignment and spatial operations (`rio.write_crs`, `rio.set_spatial_dims`, `rio.reproject_match`). The clipping implementation should use `rioxarray.clip_box()` for bbox clipping and `rioxarray.clip()` for polygon masking.
- **No defaults for function arguments** per CONTRIBUTING.md.

### Success Criteria

- `read_vector()` successfully reads shapefiles, GeoJSON, and GeoPackage files
- `clip_to_aoi()` with `clip_mode="bbox"` produces a dataset with spatial dimensions reduced to the AOI bounding box
- `clip_to_aoi()` with `clip_mode="mask"` produces a dataset where cells outside the AOI polygon are NaN
- CRS mismatch between AOI and data is handled automatically (AOI is reprojected to match data)
- Clipping a CONUS-extent dataset to Norfolk-extent produces a dataset with substantially fewer grid cells

---

## Evidence from Codebase

Inspect before implementing:

1. `_old_code_to_refactor/hpc/__utils.py` lines 94-103 — `clip_ds_to_another_ds()` function. This implements bbox clipping using xarray `.where()` with coordinate comparisons. The new implementation should use `rioxarray.clip_box()` for a cleaner approach.
2. `_old_code_to_refactor/hpc/__utils.py` lines 105-129 — `spatial_resampling()` function using `rioxarray`. Shows the pattern of renaming lat/lon to y/x, writing CRS, setting spatial dims, and using `rio.reproject_match()`. The CRS handling pattern (EPSG:4326, rename to x/y) is relevant.
3. `_old_code_to_refactor/local/__filepaths.py` lines 41-45 — shapefile paths for Norfolk (coastline, subcatchments, rain gages, states). The AOI file referenced in `system.yaml` will be one of these or a dedicated study area boundary.
4. `_old_code_to_refactor/hpc/__utils.py` line 13 — `f_shp_sst_transom` points to a transposition domain shapefile in EPSG:4326. This confirms that at least some AOI files use geographic coordinates.
5. `full_codebase_refactor.md` Decision 2 — AOI specification: GIS-agnostic vector file + clip_mode toggle.

---

## File-by-File Change Plan

### New Files

| File | Purpose |
|------|---------|
| `src/hydro_fetch/io/gis_io.py` | `read_vector`, `clip_to_aoi`, `reproject_to_match` |

### Modified Files

| File | Change |
|------|--------|
| `src/hydro_fetch/io/__init__.py` | Add re-exports for `read_vector`, `clip_to_aoi` |

---

## Risks and Edge Cases

| Risk | Mitigation |
|------|-----------|
| AOI polygon has no CRS metadata (missing `.prj` file for shapefiles) | Raise `ConfigurationError` if `gdf.crs` is None, with a message telling the user to assign a CRS to their vector file |
| AOI polygon extends beyond the data grid extent | `clip_box` will clip to the intersection. If the AOI is entirely outside the data extent, the resulting dataset will have zero-length spatial dimensions — detect this and raise `ProcessingError` |
| Multi-polygon AOI (e.g., archipelago study area) | `clip_box` uses the total bounds of all geometries; `clip` (mask) uses the union. Both handle multi-polygon natively via geopandas/rioxarray |
| `rioxarray` not installed or not imported | `rioxarray` is an accessor-based library — it must be imported (`import rioxarray`) even if not referenced directly. Add the import in `gis_io.py` with a comment explaining this. |
| Large CONUS grids may be slow to mask with complex polygons | The two-step approach (bbox first, then mask) mitigates this by reducing the grid size before polygon operations |
| Coordinate naming inconsistency — MRMS uses `latitude`/`longitude`, rioxarray expects `x`/`y` | Handle coordinate renaming within `clip_to_aoi` (rename lat/lon to y/x before rioxarray operations, rename back after). Follow the pattern in the old code's `spatial_resampling()`. |

---

## Validation Plan

```bash
# Smoke test: imports
conda run -n hydro_fetch python -c "
from hydro_fetch.io.gis_io import read_vector, clip_to_aoi, reproject_to_match
print('All GIS I/O imports OK')
"

# Test with synthetic data and a simple polygon
conda run -n hydro_fetch python -c "
import xarray as xr
import numpy as np
import geopandas as gpd
from shapely.geometry import box
from hydro_fetch.io.gis_io import clip_to_aoi

# Create a synthetic CONUS-like dataset (small for testing)
lat = np.arange(20, 55, 0.5)
lon = np.arange(230, 300, 0.5)
ds = xr.Dataset(
    {'precip': (['latitude', 'longitude'], np.random.rand(len(lat), len(lon)))},
    coords={'latitude': lat, 'longitude': lon},
)
ds = ds.rio.write_crs('EPSG:4326')
ds = ds.rio.set_spatial_dims(x_dim='longitude', y_dim='latitude')

# Create a small AOI polygon (Norfolk-like extent)
aoi = gpd.GeoDataFrame(geometry=[box(283, 36, 284, 37)], crs='EPSG:4326')

# Bbox clip
ds_bbox = clip_to_aoi(ds, aoi, 'bbox')
assert ds_bbox.sizes['latitude'] < ds.sizes['latitude']
print(f'bbox clip: {ds.sizes} -> {ds_bbox.sizes}')

# Mask clip
ds_mask = clip_to_aoi(ds, aoi, 'mask')
assert ds_mask.sizes['latitude'] < ds.sizes['latitude']
print(f'mask clip: {ds.sizes} -> {ds_mask.sizes}')
print('Clipping tests passed')
"

# ruff
conda run -n hydro_fetch ruff check src/hydro_fetch/io/gis_io.py
conda run -n hydro_fetch ruff format --check src/hydro_fetch/io/gis_io.py
```

---

## Documentation and Tracker Updates

- Update `work_chunks/README.md`: mark 01E status

---

## Definition of Done

- [ ] `src/hydro_fetch/io/gis_io.py` implemented with `read_vector`, `clip_to_aoi`, `reproject_to_match`
- [ ] `read_vector` handles shapefile, GeoJSON, GeoPackage via `geopandas.read_file()`
- [ ] `read_vector` raises `ProcessingError` on failure with file path context
- [ ] `read_vector` raises `ConfigurationError` if the loaded GeoDataFrame has no CRS
- [ ] `clip_to_aoi` implements two-step clipping: bbox first, then optional mask
- [ ] `clip_to_aoi` detects and handles CRS mismatch (reprojects AOI to match data)
- [ ] `clip_to_aoi` raises `ProcessingError` if the result has zero-length spatial dimensions
- [ ] Coordinate naming (latitude/longitude vs y/x) is handled internally
- [ ] `rioxarray` import is present with explanatory comment
- [ ] `io/__init__.py` updated with re-exports
- [ ] All functions have docstrings and type annotations
- [ ] `ruff check` and `ruff format` pass
- [ ] Pyright reports no errors
- [ ] **Move this document to `../implemented/` once all boxes above are checked**
