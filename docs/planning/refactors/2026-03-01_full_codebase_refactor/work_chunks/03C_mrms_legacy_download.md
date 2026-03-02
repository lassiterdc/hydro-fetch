# Work Chunk 03C: MRMS Legacy Download (NSSL Reanalysis + Mesonet Archive)

**Phase**: 3C — Data Acquisition (MRMS Historical/Legacy Sources)
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

1. **`src/hydro_fetch/acquire/mrms_legacy.py`** — concrete download managers for historical MRMS data sources that are not available on the primary AWS S3 bucket:

   **NSSL Reanalysis (2001-2011)**:
   - `NSSLDownloadManager` subclass of `BaseDownloadManager`
   - Source: `https://griffin-objstore.opensciencedatacloud.org/noaa-mrms-reanalysis/MRMS_PrecipRate_{YYYY}.tar`
   - Downloads tar archives, one per year (years 2001-2011)
   - After download: extract tar, then delete the tar file (matching old script behavior)
   - Output: GRIB2 files organized by year

   **Mesonet Archive (2012+)**:
   - `MesonetDownloadManager` subclass of `BaseDownloadManager`
   - Source: `https://mtarchive.geol.iastate.edu/{YYYY}/{MM}/{DD}/mrms/ncep/PrecipRate/`
   - Downloads `.grib2.gz` files, one per timestep
   - Old script: scraped HTML directory listing to enumerate files, then downloaded each with `wget` + `gunzip` pipe
   - New approach: use `fsspec` HTTP filesystem or `urllib` to list and download files; decompress `.gz` on download (matching old behavior) or keep compressed (matching 03B pattern — decide during implementation)

2. **These are fallback/historical sources**: The primary download path is AWS S3 (03B). These legacy managers are used only for historical data that predates the AWS bucket or for users who prefer the Mesonet archive.

### Key Design Decisions

- **Port shell script logic to Python**: The old code used `wget -q -c` (NSSL) and `wget` with HTML scraping (Mesonet). The new code replaces these with Python-native HTTP access via `fsspec` or `urllib`.
- **NSSL tar handling**: Download tar, extract all GRIB2 files, delete tar. Use Python's `tarfile` module. The base class atomic write pattern applies to the tar file; individual GRIB2 files extracted from the tar do not need atomic writes (the tar is the completion unit).
- **Mesonet directory listing**: The old script used `wget` to download an HTML directory listing, then `grep` to extract `.grib2.gz` filenames. The new code should use `fsspec`'s HTTP filesystem to list directory contents, or parse the HTML listing with a lightweight approach.
- **Decompression decision**: The old Mesonet script decompressed `.gz` files on download (`gunzip -c > ${local_filename}`). For consistency with 03B (which keeps files compressed), prefer keeping files compressed and letting the processing layer handle decompression. However, if NSSL GRIB2 files are already uncompressed, document the inconsistency.

### Success Criteria

- NSSL manager can download and extract a tar archive for a single year (integration test)
- Mesonet manager can list and download files for a single day (integration test)
- Both managers respect incremental mode (skip existing files)
- Both managers integrate with the base class retry and progress reporting
- Shell script logic is fully replaced — no `wget`, `gunzip`, or HTML scraping via subprocess

---

## Evidence from Codebase

Inspect before implementing:

1. `_old_code_to_refactor/hpc/aa_download_mrms_nssl.sh`:
   - URL: `https://griffin-objstore.opensciencedatacloud.org/noaa-mrms-reanalysis/MRMS_PrecipRate_{year}.tar`
   - Years 2001-2011 (SLURM array 1-11)
   - `wget -q -c --no-check-certificate` → download tar
   - `tar -xf` → extract
   - `rm` → delete tar
2. `_old_code_to_refactor/hpc/c_download_mrms_mesonet.sh`:
   - URL: `https://mtarchive.geol.iastate.edu/{YYYY}/{MM}/{DD}/mrms/ncep/PrecipRate/`
   - HTML directory listing → grep for `.grib2.gz` → per-file download
   - `wget -q -O - "$load_url" | gunzip -c > "${local_filename}"` — download and decompress in one pipe
   - Skip files that already exist locally
   - Date filtering: `not_before_date` and `TODAYS_DATE` bounds
3. `_old_code_to_refactor/hpc/ab_unzip_mrms_grib_nssl.sh` — separate unzip step for NSSL data (may contain additional logic to inspect)
4. `_old_code_to_refactor/hpc/__utils.sh` — `determine_month_and_day()` function: converts SLURM array task ID to month/day. This logic is unnecessary in Python (use `datetime` module).

---

## File-by-File Change Plan

### New Files

| File | Purpose |
|------|---------|
| `src/hydro_fetch/acquire/mrms_legacy.py` | `NSSLDownloadManager` and `MesonetDownloadManager` — historical MRMS download sources |

### Modified Files

| File | Change |
|------|--------|
| `src/hydro_fetch/acquire/__init__.py` | Export legacy download managers |
| `full_codebase_refactor.md` | Update Phase 3 status; update tracking table for `aa_download_mrms_nssl.sh` and `c_download_mrms_mesonet.sh` |

---

## Risks and Edge Cases

| Risk | Mitigation |
|------|-----------|
| NSSL archive server (`griffin-objstore.opensciencedatacloud.org`) may be unreliable or offline | Retry with backoff; document that this is a one-time historical download — once data is fetched, it is cached locally |
| Mesonet HTML directory listing format may change | Parse defensively; raise `DownloadError` with context if expected pattern not found |
| NSSL tar files are large (one per year of CONUS data) | Progress reporting for tar download; consider streaming extraction with `tarfile` to avoid buffering entire archive in memory |
| Mesonet server may rate-limit requests | Add configurable delay between file downloads; retry with backoff |
| Inconsistency between NSSL (uncompressed GRIB2) and Mesonet (compressed .grib2.gz) output formats | Document clearly; processing layer (grib_io) must handle both compressed and uncompressed GRIB2 |
| `ab_unzip_mrms_grib_nssl.sh` may contain additional extraction logic beyond `tar -xf` | Inspect this script before implementing; port any additional logic |

---

## Validation Plan

```bash
# Import test
conda run -n hydro_fetch python -c "
from hydro_fetch.acquire.mrms_legacy import NSSLDownloadManager, MesonetDownloadManager
print('Import OK')
"

# Unit tests with mocked HTTP responses
conda run -n hydro_fetch pytest tests/test_acquire.py -v -k "legacy or nssl or mesonet"

# Integration test (network required): list Mesonet files for a single day
# conda run -n hydro_fetch python -c "
# from hydro_fetch.acquire.mrms_legacy import MesonetDownloadManager
# manager = MesonetDownloadManager(...)
# files = manager.list_remote_files(date(2024, 1, 1))
# print(f'Found {len(files)} files')
# "

# Ruff
conda run -n hydro_fetch ruff check src/hydro_fetch/acquire/mrms_legacy.py
conda run -n hydro_fetch ruff format --check src/hydro_fetch/acquire/mrms_legacy.py
```

---

## Documentation and Tracker Updates

- Update `full_codebase_refactor.md`: mark 03C status; update tracking table rows for `aa_download_mrms_nssl.sh`, `ab_unzip_mrms_grib_nssl.sh`, `c_download_mrms_mesonet.sh`
- Update `07_old_code_porting_audit.md` if any old script logic is intentionally not ported

---

## Definition of Done

- [ ] `NSSLDownloadManager` implemented: downloads tar, extracts GRIB2, deletes tar
- [ ] `MesonetDownloadManager` implemented: lists files via HTTP directory, downloads `.grib2.gz`
- [ ] Both classes extend `BaseDownloadManager` and inherit retry, progress, atomic write logic
- [ ] Incremental mode: skip already-downloaded files
- [ ] No subprocess calls to `wget`, `gunzip`, `tar`, or `grep` — all logic is Python-native
- [ ] `__utils.sh` `determine_month_and_day()` logic replaced by Python `datetime`
- [ ] Unit tests with mocked HTTP responses for both managers
- [ ] Integration test for at least one manager (download 1-2 files)
- [ ] `ruff check` and `ruff format` pass
- [ ] **Move this document to `../implemented/` once all boxes above are checked**
