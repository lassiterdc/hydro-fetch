# Work Chunk 02E: Point Extraction (Gridded Data at Gage Locations)

**Phase**: 2E — Core Computation
**Created**: 2026-03-01

---

## Before Proceeding

- [`full_codebase_refactor.md`](../full_codebase_refactor.md) — master plan
- [`CONTRIBUTING.md`](../../../../CONTRIBUTING.md) — development philosophy
- [`07_old_code_porting_audit.md`](07_old_code_porting_audit.md) — record any deferred decisions

**Prerequisites**: Work chunks 01D (I/O layer), 01E (GIS I/O), and 02A (spatial operations) complete.

---

## Task Understanding

### Requirements

1. **`src/hydro_fetch/process/extraction.py`** — extract gridded precipitation data at point locations:

   - `extract_at_points(ds, points_gdf, buffer_radius, method)` — extract gridded data at point locations defined by a GeoDataFrame. Returns a time series per point location as either a `pd.DataFrame` (one column per gage) or an `xr.Dataset` (with a `station` dimension).

     - `ds`: gridded xarray Dataset with spatial dimensions
     - `points_gdf`: GeoDataFrame with point geometries and an identifier column (e.g., gage ID)
     - `buffer_radius`: radius (in CRS units) to buffer around each point. When >0, the extracted value is the spatial mean within the buffer. When 0, nearest-gridcell extraction.
     - `method`: extraction method — `"nearest"` (single nearest grid cell) or `"buffer_mean"` (average within buffer radius)

   - `align_crs(ds, points_gdf)` — ensure the gridded data and point locations are in the same CRS. Reprojects the points to match the dataset's CRS if they differ. Raises `ProcessingError` if the dataset has no CRS assigned.

2. **Output format**: per-gage time series suitable for export to CSV (one file per gage or a single multi-column CSV). The CSV export itself is handled by the I/O layer (01D), but `extract_at_points()` must return data in a format ready for that export.

3. **CRS alignment**: the old code (`_i` line 50) buffers gage points by 2500 (meters, in the gage shapefile's native CRS) then reprojects to EPSG:4326 for clipping. The new code should handle CRS alignment explicitly.

4. **Gage identifier**: the old code references `gage_id_attribute_in_shapefile = "MONITORING"` (`__utils.py` line 28). The new code should accept the identifier column name as a parameter.

5. All functions are pure computation, except that `align_crs()` may trigger a CRS reprojection of the GeoDataFrame.

### Key Design Decisions

- **Buffer-based extraction vs nearest-cell**: the old code buffers gage points by 2500m before clipping the MRMS grid to the buffered extent (`_i` line 50: `gdf_clip = gpd.read_file(shp_gages).buffer(2500).to_crs("EPSG:4326")`). This creates a rectangular clip region, not a per-gage extraction. The new code should support true per-point extraction with configurable buffer radius for spatial averaging.
- **Clip-then-extract vs direct extraction**: the old code clips the entire MRMS grid to the gage-area bounding box, then works with the clipped subset. The new code should still clip first for performance (reducing a CONUS grid to the gage region), then extract per-point values. The clip step uses `clip_to_bounds()` from 02A.
- **QA/QC variable handling**: the old code (`_i` lines 100-117) separates data into rain rate time series (with `time` dimension) and QA/QC variables (without `time` dimension, expanded to have a `date` dimension). The new code should handle both types of variables.
- **Coordinate duplicate handling**: the old code (`_i` lines 70-97) checks for and repairs coordinate duplicates by substituting coordinates from a reference dataset. This should be delegated to `check_coordinate_duplicates()` from 02D.
- **Output structure**: return an xarray Dataset with dimensions `(time, station)` where `station` is indexed by the gage identifier. This is more flexible than a DataFrame and can be easily converted to CSV via the I/O layer.

### Success Criteria

- `extract_at_points()` correctly extracts time series from gridded data at specified point locations
- Buffer-based extraction computes the spatial mean within the buffer radius
- Nearest-cell extraction returns the value of the closest grid cell
- CRS alignment handles mismatched CRS between grid and points
- Output has a `station` dimension indexed by the gage identifier column
- Works with dask-backed arrays
- No hardcoded gage IDs, shapefile paths, or CRS values

---

## Evidence from Codebase

Inspect before implementing:

1. `_old_code_to_refactor/hpc/_i_extract_mrms_at_gages.py` — main extraction script:
   - Line 28-29: shapefile and output paths passed via `sys.argv`
   - Line 50: `gdf_clip = gpd.read_file(shp_gages).buffer(2500).to_crs("EPSG:4326")` — buffer gages and reproject
   - Line 51: `minx, miny, maxx, maxy = gdf_clip.total_bounds` — get bounding box
   - Lines 70-86: coordinate duplicate detection and reference coordinate substitution
   - Lines 87-117: iterate over daily files, clip to gage bounding box (`rio.clip_box()`), handle bias-corrected vs non-bias-corrected structures, separate rain rate and QA/QC variables
   - Line 99: `ds_day = ds_day.rio.clip_box(minx+360, miny, maxx+360, maxy)` — note the `+360` for longitude convention
   - Lines 120-128: chunk specification for output
   - Lines 131-143: export rain data and QA/QC data as separate yearly zarr files

2. `_old_code_to_refactor/hpc/__utils.py` line 28: `gage_id_attribute_in_shapefile = "MONITORING"` — hardcoded gage ID column name

3. `_old_code_to_refactor/hpc/_i_extract_mrms_at_gages.py` lines 100-117 — handling datasets where `bias_corrected == False`: fills missing variables with NaN to maintain consistent structure across days. This is an I/O concern, not an extraction concern.

---

## File-by-File Change Plan

### New Files

| File | Purpose |
|------|---------|
| `src/hydro_fetch/process/extraction.py` | Point extraction from gridded data |
| `tests/test_extraction.py` | Unit tests for point extraction |

### Modified Files

| File | Change |
|------|--------|
| `src/hydro_fetch/process/__init__.py` | Ensure module is importable |

---

## Risks and Edge Cases

| Risk | Mitigation |
|------|-----------|
| Buffer radius in meters vs degrees — depends on CRS | If CRS is geographic (degrees), convert buffer radius from meters to approximate degrees. Document the limitation and recommend projected CRS for precise buffering. |
| MRMS longitude convention (degrees east, 230-300) requires `+360` adjustment | Handle this in `align_crs()` or delegate to the spatial operations module. Do not hardcode `+360`. |
| Large number of gage points could make per-point extraction slow | Clip the grid to the gage bounding box first (using 02A), then extract. For very large point sets, consider vectorized extraction. |
| Dask arrays and per-point `.sel(method="nearest")` may not be efficient | Test with dask; if slow, consider loading a spatially-clipped subset into memory first. |
| Gage shapefile may use a projected CRS while MRMS is EPSG:4326 | `align_crs()` handles this by reprojecting points to the dataset's CRS. |
| Empty extraction (no data at a gage location) should return NaN, not error | Ensure `sel(method="nearest")` returns NaN for out-of-bounds points; raise a warning if any gage falls outside the grid extent. |

---

## Validation Plan

```bash
# Unit tests
conda run -n hydro_fetch pytest tests/test_extraction.py -v

# Smoke test
conda run -n hydro_fetch python -c "
from hydro_fetch.process.extraction import extract_at_points, align_crs
print('All imports OK')
"

# Linting
conda run -n hydro_fetch ruff check src/hydro_fetch/process/extraction.py
conda run -n hydro_fetch ruff format --check src/hydro_fetch/process/extraction.py
```

### Test Cases

1. **Nearest-cell extraction**: Create a 10x10 grid with known values and 3 point locations. Extract using `method="nearest"`. Verify values match the nearest grid cell.
2. **Buffer extraction**: Create a fine grid, place a point at a known location, extract with buffer_radius > 0. Verify the result is the spatial mean of cells within the buffer.
3. **CRS alignment**: Create a grid in EPSG:4326 and points in EPSG:32618 (UTM zone 18N). Verify `align_crs()` reprojects points correctly.
4. **Missing CRS**: Create a grid with no CRS set. Verify `ProcessingError` is raised with actionable message.
5. **Out-of-bounds gage**: Place a point outside the grid extent. Verify NaN is returned with a warning.
6. **Multiple gages**: Extract at 10 points, verify output has `(time, station)` dimensions with 10 stations.
7. **Gage ID column**: Verify the station dimension is indexed by the user-specified identifier column.
8. **Dask compatibility**: Run with dask-backed grid data.

---

## Documentation and Tracker Updates

- Update `full_codebase_refactor.md`: mark `_i_extract_mrms_at_gages.py` as ported in tracking table
- Update `work_chunks/README.md`: mark 02E as complete

---

## Definition of Done

- [ ] `src/hydro_fetch/process/extraction.py` implemented with `extract_at_points()` and `align_crs()`
- [ ] Supports both `nearest` and `buffer_mean` extraction methods
- [ ] CRS alignment between grid and point data is handled automatically
- [ ] Output has `(time, station)` dimensions indexed by user-specified gage identifier
- [ ] No hardcoded shapefile paths, gage IDs, or CRS values
- [ ] Works with dask-backed arrays
- [ ] Unit tests cover nearest, buffer, CRS alignment, out-of-bounds, and multi-gage cases
- [ ] `ruff check` and `ruff format` pass
- [ ] Type hints and docstrings on all public functions
- [ ] **Move this document to `../implemented/` once all boxes above are checked**
