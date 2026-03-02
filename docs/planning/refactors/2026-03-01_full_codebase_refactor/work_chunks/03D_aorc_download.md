# Work Chunk 03D: AORC Download

**Phase**: 3D — Data Acquisition (AORC)
**Created**: 2026-03-01

---

## Before Proceeding

Review the following documents before making any edits to plans or writing any code:

- [`full_codebase_refactor.md`](../full_codebase_refactor.md) — master refactor plan; update it if any decisions made here affect the overall plan.
- [`CONTRIBUTING.md`](../../../../CONTRIBUTING.md) — development philosophy.
- [`07_old_code_porting_audit.md`](07_old_code_porting_audit.md) — record any deferred old code decisions here.

**Prerequisites**: Work chunk 03A (base download manager) complete.

---

## Task Understanding

### Requirements

1. **`src/hydro_fetch/acquire/aorc.py`** — concrete download manager for AORC precipitation data:
   - `AORCDownloadManager` subclass of `BaseDownloadManager`
   - Source: `s3://noaa-nws-aorc-v1-1-1km/{YYYY}.zarr/` (AWS S3, anonymous access)
   - AWS registry: https://registry.opendata.aws/noaa-nws-aorc/
   - Data format: Zarr stores, one per year
   - Download via `aws s3 sync` equivalent using `fsspec` or `s3fs` — sync entire yearly Zarr directory to local storage
   - Incremental mode: only download Zarr stores for years not already present locally (or use `s3 sync` semantics to update partial downloads)

2. **AORC-specific considerations**:
   - AORC data is already in Zarr format — no GRIB2 handling needed
   - Each year is a single Zarr store (directory of chunks), not individual timestep files
   - The download unit is a full year, not individual dates
   - The old script used `aws s3 sync --no-sign-request` — the new code should replicate this behavior using `fsspec`/`s3fs`

### Key Design Decisions

- **Zarr sync, not file-by-file download**: AORC Zarr stores are chunked datasets. The natural download unit is the entire Zarr store for a year. Use `s3fs` to mirror the Zarr directory structure locally, similar to `aws s3 sync`.
- **Year-based iteration**: Unlike MRMS (date-based), AORC downloads are year-based. The `list_remote_files` method returns available year directories. The `download_date_range` method is overridden to iterate by year.
- **No decompression step**: AORC data arrives as Zarr — it can be read directly by xarray without any format conversion.
- **Large downloads**: Each year of AORC data may be several GB. Progress reporting is important. Consider chunked transfer with progress bar.

### Success Criteria

- Can list available AORC years on the S3 bucket (integration test, network required)
- Can download a single year's Zarr store (or a subset of its chunks for testing)
- Incremental mode correctly skips already-downloaded years
- Downloaded Zarr store is openable by `xr.open_zarr()`

---

## Evidence from Codebase

Inspect before implementing:

1. `_old_code_to_refactor/hpc/d_download_AORC.sh`:
   - `aws s3 sync --no-sign-request s3://noaa-nws-aorc-v1-1-1km/${YEAR}.zarr/ ./data/${YEAR}.zarr/ --quiet`
   - SLURM array over years (`START_YEAR + TASK_ID - 1`)
   - Size estimation: `aws s3 ls --recursive` to compute total size
   - Progress monitoring: background loop checking `du -sh`
   - Registry metadata: `https://registry.opendata.aws/noaa-nws-aorc/`
2. `src/hydro_fetch/constants.py` (from 01A) — `PRODUCT_METADATA` entry for `aorc_1hr` with S3 bucket path
3. `src/hydro_fetch/acquire/base.py` (from 03A) — base class methods to override for year-based (vs date-based) iteration

---

## File-by-File Change Plan

### New Files

| File | Purpose |
|------|---------|
| `src/hydro_fetch/acquire/aorc.py` | `AORCDownloadManager` — downloads AORC Zarr stores from AWS S3 |

### Modified Files

| File | Change |
|------|--------|
| `src/hydro_fetch/acquire/__init__.py` | Export `AORCDownloadManager` |
| `full_codebase_refactor.md` | Update Phase 3 status; update tracking table for `d_download_AORC.sh` |

---

## Risks and Edge Cases

| Risk | Mitigation |
|------|-----------|
| AORC Zarr stores are large (several GB per year); download may take hours | Progress reporting; resume capability via `s3 sync` semantics (skip already-transferred chunks) |
| Zarr directory sync is more complex than single-file download | Use `s3fs` recursive copy or implement chunk-by-chunk sync with `fsspec`; alternatively, shell out to `aws s3 sync` as a pragmatic fallback if fsspec sync is unreliable |
| AORC bucket name or structure may change (`noaa-nws-aorc-v1-1-1km` includes version) | Pin bucket name in constants; document the version dependency |
| Partial Zarr download produces a corrupted store | Use a completion marker (e.g., `.download_complete` file in the Zarr directory) to distinguish complete from partial downloads |
| AORC data resolution or variables may differ from expectations | Validate downloaded Zarr by opening with xarray and checking expected variables (precipitation) and dimensions |

---

## Validation Plan

```bash
# Import test
conda run -n hydro_fetch python -c "
from hydro_fetch.acquire.aorc import AORCDownloadManager
print('Import OK')
"

# Integration test: list available years (requires network)
# conda run -n hydro_fetch python -c "
# from hydro_fetch.acquire.aorc import AORCDownloadManager
# manager = AORCDownloadManager(...)
# years = manager.list_available_years()
# print(f'Available years: {years}')
# "

# Integration test: download and validate a small portion
# conda run -n hydro_fetch python -c "
# import xarray as xr
# ds = xr.open_zarr('path/to/downloaded/2024.zarr')
# print(ds)
# print(ds.data_vars)
# "

# Unit tests
conda run -n hydro_fetch pytest tests/test_acquire.py -v -k "aorc"

# Ruff
conda run -n hydro_fetch ruff check src/hydro_fetch/acquire/aorc.py
conda run -n hydro_fetch ruff format --check src/hydro_fetch/acquire/aorc.py
```

---

## Documentation and Tracker Updates

- Update `full_codebase_refactor.md`: mark 03D status; update tracking table for `d_download_AORC.sh`
- Confirm AORC URL is no longer TBD in master plan (should have been resolved in chunk 00)

---

## Definition of Done

- [ ] `src/hydro_fetch/acquire/aorc.py` implements `AORCDownloadManager`
- [ ] Downloads Zarr stores from `s3://noaa-nws-aorc-v1-1-1km/{YYYY}.zarr/`
- [ ] Year-based iteration (overrides date-based default from base class)
- [ ] Incremental mode: skip already-complete yearly Zarr stores
- [ ] Completion marker for partial download detection
- [ ] Progress reporting for large Zarr sync operations
- [ ] Downloaded Zarr validated with `xr.open_zarr()`
- [ ] No shell-out to `aws` CLI — all access via `fsspec`/`s3fs`
- [ ] Unit tests with mocked S3 filesystem
- [ ] `ruff check` and `ruff format` pass
- [ ] **Move this document to `../implemented/` once all boxes above are checked**
