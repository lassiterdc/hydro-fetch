# Work Chunk 03A: Base Download Manager

**Phase**: 3A — Data Acquisition (Foundation)
**Created**: 2026-03-01

---

## Before Proceeding

Review the following documents before making any edits to plans or writing any code:

- [`full_codebase_refactor.md`](../full_codebase_refactor.md) — master refactor plan; update it if any decisions made here affect the overall plan.
- [`CONTRIBUTING.md`](../../../../CONTRIBUTING.md) — development philosophy.
- [`07_old_code_porting_audit.md`](07_old_code_porting_audit.md) — record any deferred old code decisions here.

**Prerequisites**: Work chunks 01B (Pydantic config model) and 01C (path management) complete.

---

## Task Understanding

### Requirements

1. **`src/hydro_fetch/acquire/base.py`** — abstract base class for all download managers:
   - Abstract methods: `list_remote_files(date_range)`, `download_file(remote_path, local_path)`, `local_file_exists(remote_path)`
   - Concrete methods inherited by all subclasses:
     - **Retry with exponential backoff**: configurable max retries, base delay, max delay; uses `tenacity` or hand-rolled decorator
     - **Progress reporting**: tqdm-based progress bar for multi-file downloads; optional quiet mode
     - **Per-file completion tracking**: atomic write pattern (download to `.tmp`, rename on success) to prevent partial files from being treated as complete
     - **Incremental download via S3 listing comparison** (Decision 5): list remote files for configured date range, compare against local files by filename, download any missing
     - **New-file logging**: log all newly-downloaded files to a manifest (e.g., `{output_dir}/.newly_downloaded.json`) so downstream processing knows which periods need reprocessing
   - Uses `fsspec` with `s3fs` for S3 access (anonymous, no credentials needed)
   - Respects `PipelineConfig.incremental` and `PipelineConfig.start_date` / `end_date` from the config model (01B)
   - Uses path management (01C) to resolve local download directories

2. **`src/hydro_fetch/acquire/__init__.py`** — package init; exports base class and (eventually) concrete managers.

### Key Design Decisions

- **fsspec for all remote access**: S3 access uses `s3fs` via `fsspec` with `anon=True`. This replaces `wget` from the old shell scripts. Legacy HTTP sources (NSSL, Mesonet) use `fsspec` with the HTTP filesystem or fall back to `urllib`.
- **No credentials required**: All S3 buckets used by this project are public (anonymous access). The base class should not include credential management.
- **Atomic writes**: Files are downloaded to a `.tmp` suffix and renamed on completion. This prevents Snakemake or subsequent pipeline stages from picking up partial downloads.
- **Date-based iteration**: The base class provides a `download_date_range(start, end)` method that iterates over dates, calls `list_remote_files` for each date, and downloads missing files. Subclasses only need to implement the product-specific listing and path logic.
- **Newly-downloaded manifest**: After each download run, a JSON manifest of newly-downloaded files is written. This is consumed by Snakemake rules to determine which processing steps need to be re-executed.

### Success Criteria

- Base class is importable: `from hydro_fetch.acquire.base import BaseDownloadManager`
- A mock subclass can be instantiated and exercised in a unit test
- Retry logic is testable (mock a transient failure, verify retry count)
- Atomic write pattern verified (interrupted download does not leave a non-`.tmp` file)
- Incremental mode: given a list of local files and remote files, correctly identifies the delta

---

## Evidence from Codebase

Inspect before implementing:

1. `_old_code_to_refactor/hpc/aa_download_mrms_nssl.sh` — `wget -q -c` for download with resume; tar extraction; per-year iteration via SLURM array
2. `_old_code_to_refactor/hpc/c_download_mrms_mesonet.sh` — `wget` with per-file existence check (`if [[ ! -f "${local_filename}" ]]`); directory listing via HTML scraping; download + gunzip pipe
3. `_old_code_to_refactor/hpc/d_download_AORC.sh` — `aws s3 sync` for AORC zarr download from `s3://noaa-nws-aorc-v1-1-1km/`
4. `src/hydro_fetch/constants.py` (from 01A) — `PRODUCT_METADATA` dict with S3 paths and file patterns
5. `src/hydro_fetch/config/model.py` (from 01B) — `PipelineConfig` with `start_date`, `end_date`, `incremental` fields
6. Decision 5 in master plan — incremental download via S3 listing comparison

---

## File-by-File Change Plan

### New Files

| File | Purpose |
|------|---------|
| `src/hydro_fetch/acquire/__init__.py` | Package init; export `BaseDownloadManager` |
| `src/hydro_fetch/acquire/base.py` | Abstract base class with retry, progress, incremental download, atomic writes |

### Modified Files

| File | Change |
|------|--------|
| `full_codebase_refactor.md` | Update Phase 3 status; mark 03A as in-progress/complete |

---

## Risks and Edge Cases

| Risk | Mitigation |
|------|-----------|
| fsspec S3 listing may be slow for buckets with thousands of files per day (PrecipRate has ~720 files/day) | Use `s3fs.S3FileSystem.ls()` with prefix filtering; consider caching listing results per date |
| Network interruptions during large downloads | Retry with exponential backoff handles transient failures; atomic writes prevent corruption |
| `.newly_downloaded.json` manifest grows unbounded across runs | Overwrite (not append) on each run; previous manifest is replaced. If append behavior is needed later, add rotation. |
| fsspec/s3fs version incompatibilities | Pin minimum versions in pyproject.toml; test with current conda-forge versions |
| Legacy HTTP sources (NSSL, Mesonet) do not support S3 listing | Base class `list_remote_files` is abstract; HTTP subclasses implement their own listing strategy (HTML scraping or known URL patterns) |

---

## Validation Plan

```bash
# Imports work
conda run -n hydro_fetch python -c "
from hydro_fetch.acquire.base import BaseDownloadManager
print('Import OK')
print('Abstract methods:', [m for m in dir(BaseDownloadManager) if not m.startswith('_')])
"

# Unit tests pass
conda run -n hydro_fetch pytest tests/test_acquire.py -v -k "base"

# Ruff passes
conda run -n hydro_fetch ruff check src/hydro_fetch/acquire/
conda run -n hydro_fetch ruff format --check src/hydro_fetch/acquire/
```

---

## Documentation and Tracker Updates

- Update `full_codebase_refactor.md`: mark 03A status
- Update `work_chunks/README.md`: mark 03A as complete

---

## Definition of Done

- [ ] `src/hydro_fetch/acquire/base.py` implemented with abstract base class
- [ ] Retry with exponential backoff (configurable retries, delay)
- [ ] Progress reporting via tqdm (optional quiet mode)
- [ ] Atomic write pattern (`.tmp` → rename)
- [ ] Per-file completion tracking (skip files that already exist locally)
- [ ] S3 listing comparison for incremental downloads (Decision 5)
- [ ] Newly-downloaded file manifest written after each run
- [ ] `download_date_range()` iterates dates and delegates to abstract methods
- [ ] fsspec with `anon=True` for S3 access
- [ ] Unit tests for retry logic, atomic writes, incremental delta detection
- [ ] `ruff check` and `ruff format` pass
- [ ] **Move this document to `../implemented/` once all boxes above are checked**
