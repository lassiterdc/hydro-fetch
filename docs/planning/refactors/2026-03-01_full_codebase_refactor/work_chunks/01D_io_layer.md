# Work Chunk 01D: I/O Layer for zarr, NetCDF, CSV, GRIB2

**Phase**: 1D — Foundation
**Created**: 2026-03-01

---

## Before Proceeding

- [`full_codebase_refactor.md`](../full_codebase_refactor.md) — master plan
- [`CONTRIBUTING.md`](../../../../CONTRIBUTING.md) — development philosophy
- [`07_old_code_porting_audit.md`](07_old_code_porting_audit.md) — record any deferred decisions

**Prerequisites**: Work chunks 01A, 01B, and 01C complete.

---

## Task Understanding

### Requirements

1. **`src/hydro_fetch/io/readers.py`** — consistent interface for reading processed data:
   - `read_zarr(path) -> xr.Dataset` — open a zarr store with dask-backed arrays
   - `read_netcdf(path) -> xr.Dataset` — open a NetCDF file with dask-backed arrays
   - `read_csv(path) -> pd.DataFrame` — read a CSV file (gage-extracted time series)
   - All readers raise `ProcessingError` on failure with the file path in the exception context

2. **`src/hydro_fetch/io/writers.py`** — consistent interface for writing processed data:
   - `write_zarr(ds, path, encoding) -> None` — write xarray Dataset to zarr with compression
   - `write_netcdf(ds, path, encoding) -> None` — write xarray Dataset to NetCDF with compression
   - `write_csv(df, path) -> None` — write pandas DataFrame to CSV
   - Default compression settings sourced from `constants.py` (zarr: zstd via Blosc; NetCDF: zlib)
   - All writers must set xarray attrs for `original_temporal_resolution` and `original_spatial_resolution` per Decision 1 if not already present. These attrs are passed as arguments, not inferred.
   - Include support for writing the `missing_duration_min` DataArray alongside precipitation data per Decision 6

3. **`src/hydro_fetch/process/grib_io.py`** — GRIB2 reading for raw MRMS downloads:
   - `read_grib2(path) -> xr.Dataset` — read a single GRIB2 file using xarray + cfgrib engine
   - `read_grib2_gz(path) -> xr.Dataset` — decompress a `.grib2.gz` file to a temporary location, then read with cfgrib. Clean up the temporary file after reading.
   - Handle the coordinate cleanup that was previously in `__utils.py`'s `remove_vars()` function (drop `step`, `heightAboveSea`, `valid_time` coords; drop `source`, `problems` attrs)
   - Raise `ProcessingError` on corrupt or unreadable GRIB2 files with file path context

4. **`src/hydro_fetch/io/__init__.py`** — re-export all public reader and writer functions

### Key Design Decisions

- **Readers return dask-backed arrays** — all gridded readers open lazily via `chunks="auto"` or explicit chunking. This is consistent with the old code's use of dask for out-of-core processing.
- **Writers accept an optional `encoding` dict** — if not provided, use compression defaults from `constants.py`. This allows callers to override compression settings without modifying the writer.
- **Resolution attrs are required arguments to writers, not inferred** — the writer does not know the product's original resolution. The caller (processing module) passes `original_temporal_resolution` and `original_spatial_resolution` as strings (e.g., `"2min"`, `"1km"`). The writer sets them as dataset attrs.
- **GRIB2 reading is in `process/` not `io/`** — GRIB2 files are raw downloads that require format-specific handling (decompression, coordinate cleanup). This is processing-adjacent, not generic I/O. The `io/` module handles the clean, processed formats (zarr, NetCDF, CSV).
- **Coordinate cleanup from old code is preserved** — `remove_vars()` from `__utils.py` deleted `step`, `heightAboveSea`, `valid_time` coords and `source`, `problems` attrs. This cleanup is applied automatically in `read_grib2()`.

### Success Criteria

- Round-trip test: write a dataset with `write_zarr`, read it back with `read_zarr`, verify data equality
- Round-trip test: write a dataset with `write_netcdf`, read it back with `read_netcdf`, verify data equality
- GRIB2 reader successfully opens a sample GRIB2 file (if available) or raises `ProcessingError` with clear context on failure
- Resolution attrs are preserved through write-read cycle
- `missing_duration_min` DataArray can be included in written datasets and read back

---

## Evidence from Codebase

Inspect before implementing:

1. `_old_code_to_refactor/hpc/__utils.py` lines 71-76 — `define_zarr_compression()` function using `zarr.Blosc(cname="zstd", clevel=5, shuffle=zarr.Blosc.SHUFFLE)`. This is the compression pattern to replicate for zarr output.
2. `_old_code_to_refactor/hpc/__utils.py` lines 36-39 — `coords_to_delete` and `attrs_to_delete` lists used by `remove_vars()`. These define the coordinate cleanup for GRIB2 reading.
3. `_old_code_to_refactor/hpc/__utils.py` lines 135-151 — `remove_vars()` function. Note the bare `except: continue` pattern — the new implementation should check for key existence rather than catching all exceptions.
4. `_old_code_to_refactor/local/__filepaths.py` lines 64-74 — chunking parameters (`size_of_float32`, `MB_per_bit`, `num_lats`, `num_lons`). These inform dask chunk size decisions but belong in constants, not the I/O layer.
5. `full_codebase_refactor.md` Decision 6 — `missing_duration_min` DataArray specification. The I/O layer must support writing and reading this alongside precipitation data.

---

## File-by-File Change Plan

### New Files

| File | Purpose |
|------|---------|
| `src/hydro_fetch/io/__init__.py` | Re-export reader and writer functions |
| `src/hydro_fetch/io/readers.py` | `read_zarr`, `read_netcdf`, `read_csv` |
| `src/hydro_fetch/io/writers.py` | `write_zarr`, `write_netcdf`, `write_csv` with compression and attrs |
| `src/hydro_fetch/process/__init__.py` | Empty init for process subpackage |
| `src/hydro_fetch/process/grib_io.py` | `read_grib2`, `read_grib2_gz` with coordinate cleanup |

### Modified Files

| File | Change |
|------|--------|
| None | No existing files are modified in this chunk |

---

## Risks and Edge Cases

| Risk | Mitigation |
|------|-----------|
| `cfgrib` may not be installed or may have eccodes dependency issues | Document the conda dependency (`eccodes` from conda-forge); raise `ProcessingError` with a helpful message if import fails |
| Large zarr writes may fail mid-write, leaving a corrupt store | Document that callers should write to a temporary path and rename atomically. This is a caller responsibility, not a writer concern. |
| Compression defaults in `constants.py` may use APIs that change between zarr v2 and v3 | Pin zarr version in conda environment; add a comment noting the zarr version dependency |
| `.grib2.gz` decompression creates temporary files that could leak if the process crashes | Use `tempfile.NamedTemporaryFile` with a try/finally block for cleanup |
| NetCDF encoding for time coordinates can be tricky (cf. old code `time_encoding` in `process_dans_stageiv`) | Use xarray's default CF-compliant time encoding; only override if specific issues arise |

---

## Validation Plan

```bash
# Smoke test: imports
conda run -n hydro_fetch python -c "
from hydro_fetch.io import read_zarr, read_netcdf, read_csv, write_zarr, write_netcdf, write_csv
from hydro_fetch.process.grib_io import read_grib2, read_grib2_gz
print('All I/O imports OK')
"

# Round-trip test: zarr
conda run -n hydro_fetch python -c "
import xarray as xr
import numpy as np
from pathlib import Path
import tempfile
from hydro_fetch.io import write_zarr, read_zarr

ds = xr.Dataset({'precip': (['time', 'y', 'x'], np.random.rand(10, 5, 5))})
with tempfile.TemporaryDirectory() as td:
    p = Path(td) / 'test.zarr'
    write_zarr(ds, p, original_temporal_resolution='2min', original_spatial_resolution='1km')
    ds2 = read_zarr(p)
    assert np.allclose(ds['precip'].values, ds2['precip'].values)
    assert ds2.attrs['original_temporal_resolution'] == '2min'
    print('zarr round-trip OK')
"

# Round-trip test: netcdf
conda run -n hydro_fetch python -c "
import xarray as xr
import numpy as np
from pathlib import Path
import tempfile
from hydro_fetch.io import write_netcdf, read_netcdf

ds = xr.Dataset({'precip': (['time', 'y', 'x'], np.random.rand(10, 5, 5))})
with tempfile.TemporaryDirectory() as td:
    p = Path(td) / 'test.nc'
    write_netcdf(ds, p, original_temporal_resolution='1hr', original_spatial_resolution='1km')
    ds2 = read_netcdf(p)
    assert np.allclose(ds['precip'].values, ds2['precip'].values)
    assert ds2.attrs['original_temporal_resolution'] == '1hr'
    print('NetCDF round-trip OK')
"

# ruff
conda run -n hydro_fetch ruff check src/hydro_fetch/io/ src/hydro_fetch/process/grib_io.py
conda run -n hydro_fetch ruff format --check src/hydro_fetch/io/ src/hydro_fetch/process/grib_io.py
```

---

## Documentation and Tracker Updates

- Update `work_chunks/README.md`: mark 01D status

---

## Definition of Done

- [ ] `src/hydro_fetch/io/readers.py` implemented with `read_zarr`, `read_netcdf`, `read_csv`
- [ ] All gridded readers return dask-backed arrays (lazy loading)
- [ ] All readers raise `ProcessingError` on failure with file path context
- [ ] `src/hydro_fetch/io/writers.py` implemented with `write_zarr`, `write_netcdf`, `write_csv`
- [ ] Writers apply compression defaults from `constants.py` when encoding is not provided
- [ ] Writers set `original_temporal_resolution` and `original_spatial_resolution` attrs
- [ ] Writers support `missing_duration_min` DataArray in the dataset
- [ ] `src/hydro_fetch/process/grib_io.py` implemented with `read_grib2`, `read_grib2_gz`
- [ ] GRIB2 reader applies coordinate cleanup (drops `step`, `heightAboveSea`, `valid_time`, `source`, `problems`)
- [ ] `.grib2.gz` reader handles decompression with proper temporary file cleanup
- [ ] `src/hydro_fetch/io/__init__.py` re-exports all public symbols
- [ ] `src/hydro_fetch/process/__init__.py` created
- [ ] `ruff check` and `ruff format` pass
- [ ] Pyright reports no errors
- [ ] **Move this document to `../implemented/` once all boxes above are checked**
