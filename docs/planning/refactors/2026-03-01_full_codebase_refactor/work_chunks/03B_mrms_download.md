# Work Chunk 03B: MRMS Download (AWS S3)

**Phase**: 3B — Data Acquisition (MRMS Primary)
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

1. **`src/hydro_fetch/acquire/mrms.py`** — concrete download manager for MRMS products from AWS S3:
   - **`MRMSDownloadManager`** subclass of `BaseDownloadManager`
   - Downloads two products:
     - `mrms_2min` (PrecipRate): `s3://noaa-mrms-pds/CONUS/PrecipRate_00.00/{YYYYMMDD}/`
     - `mrms_pass2_1hr` (MultiSensor QPE Pass2): `s3://noaa-mrms-pds/CONUS/MultiSensor_QPE_01H_Pass2_00.00/{YYYYMMDD}/`
   - Files are `.grib2.gz` — download as-is (decompression happens in processing phase)
   - Implements `list_remote_files(date)` using `s3fs.S3FileSystem.ls()` with date-based prefix
   - Implements `local_file_exists(remote_path)` mapping S3 key to local path
   - Date range iteration: for each date in `[start_date, end_date]`, list S3 bucket contents and download missing files
   - Incremental mode: compare S3 listing against local directory contents; download only missing files
   - Product selection: only download products enabled in the pipeline config

2. **File naming**: Local files retain their S3 filename. Directory structure mirrors S3 date-based organization: `{download_dir}/{product_name}/{YYYYMMDD}/{filename}.grib2.gz`

### Key Design Decisions

- **One class handles both MRMS products**: The S3 bucket structure is identical for PrecipRate and QPE Pass2 — only the product path prefix differs. A single `MRMSDownloadManager` class accepts the product name and resolves the S3 prefix from `PRODUCT_METADATA` in `constants.py`.
- **Files stay compressed**: `.grib2.gz` files are not decompressed during download. Decompression is a processing step (Phase 2 grib_io module handles this transparently via xarray+cfgrib).
- **PrecipRate volume**: ~720 files per day (one every 2 minutes). A full year is ~263,000 files. The download manager must handle this volume gracefully (batch listing, progress reporting).
- **QPE Pass2 volume**: ~24 files per day (one per hour). Much more manageable.

### Success Criteria

- Can list files for a single date on the MRMS S3 bucket (integration test, network required)
- Can download 1-2 files for a single day and verify they are valid `.grib2.gz`
- Incremental mode correctly skips already-downloaded files
- Both `mrms_2min` and `mrms_pass2_1hr` products are supported
- Newly-downloaded files are logged to the manifest

---

## Evidence from Codebase

Inspect before implementing:

1. `_old_code_to_refactor/hpc/c_download_mrms_mesonet.sh` — old download logic: HTML directory listing scraping, per-file wget+gunzip, existence check before download. This approach is being replaced by S3 listing via fsspec.
2. `src/hydro_fetch/constants.py` (from 01A) — `PRODUCT_METADATA` with S3 paths: `s3://noaa-mrms-pds/CONUS/PrecipRate_00.00/` and `s3://noaa-mrms-pds/CONUS/MultiSensor_QPE_01H_Pass2_00.00/`
3. `src/hydro_fetch/acquire/base.py` (from 03A) — `BaseDownloadManager` with `list_remote_files`, `download_file`, `download_date_range`
4. AWS MRMS Registry: https://registry.opendata.aws/noaa-mrms-pds/ — confirms bucket structure and anonymous access
5. Master plan Data Sources Reference table — S3 URL patterns, file formats, resolutions

---

## File-by-File Change Plan

### New Files

| File | Purpose |
|------|---------|
| `src/hydro_fetch/acquire/mrms.py` | `MRMSDownloadManager` — downloads MRMS PrecipRate and QPE Pass2 from AWS S3 |

### Modified Files

| File | Change |
|------|--------|
| `src/hydro_fetch/acquire/__init__.py` | Export `MRMSDownloadManager` |
| `full_codebase_refactor.md` | Update Phase 3 status |

---

## Risks and Edge Cases

| Risk | Mitigation |
|------|-----------|
| S3 bucket may have missing dates (data gaps) | `list_remote_files` returns empty list for missing dates; log a warning but do not raise an error. Data gap tracking (Decision 6) handles this downstream. |
| PrecipRate has ~720 files/day — listing may be slow | Use S3 prefix filtering (`ls` with prefix `CONUS/PrecipRate_00.00/YYYYMMDD/`); single API call per date |
| S3 file names may change format over time | Pin expected filename pattern in constants; raise `DownloadError` if unexpected filenames encountered |
| Network throttling on high-volume downloads | Respect retry backoff from base class; optionally add configurable concurrency limit |
| QPE Pass2 has 2-hour latency for the most recent day | Document in data_sources.md; download manager does not special-case this — it downloads whatever is available on S3 for the requested date range |

---

## Validation Plan

```bash
# Import test
conda run -n hydro_fetch python -c "
from hydro_fetch.acquire.mrms import MRMSDownloadManager
print('Import OK')
"

# Integration test: list files for a single date (requires network)
conda run -n hydro_fetch python -c "
from hydro_fetch.acquire.mrms import MRMSDownloadManager
# This test requires network access
# manager = MRMSDownloadManager(product='mrms_2min', ...)
# files = manager.list_remote_files(date(2024, 1, 1))
# print(f'Found {len(files)} files')
"

# Unit tests
conda run -n hydro_fetch pytest tests/test_acquire.py -v -k "mrms"

# Ruff
conda run -n hydro_fetch ruff check src/hydro_fetch/acquire/mrms.py
conda run -n hydro_fetch ruff format --check src/hydro_fetch/acquire/mrms.py
```

---

## Documentation and Tracker Updates

- Update `full_codebase_refactor.md`: mark 03B status
- Update tracking table: old Mesonet download → new `acquire/mrms.py`

---

## Definition of Done

- [ ] `src/hydro_fetch/acquire/mrms.py` implements `MRMSDownloadManager`
- [ ] Supports both `mrms_2min` and `mrms_pass2_1hr` products
- [ ] `list_remote_files` uses S3 listing with date-based prefix
- [ ] `download_file` downloads `.grib2.gz` via fsspec with atomic write
- [ ] Date range iteration with incremental skip logic
- [ ] Local directory structure mirrors S3 date organization
- [ ] Integration test: download 1-2 files for a single day, verify format
- [ ] Unit tests with mocked S3 filesystem
- [ ] Newly-downloaded files logged to manifest
- [ ] `ruff check` and `ruff format` pass
- [ ] **Move this document to `../implemented/` once all boxes above are checked**
