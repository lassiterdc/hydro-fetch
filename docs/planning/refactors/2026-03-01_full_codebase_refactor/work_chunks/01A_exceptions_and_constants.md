# Work Chunk 01A: Exceptions and Constants

**Phase**: 1A — Foundation
**Created**: 2026-03-01

---

## Before Proceeding

- [`full_codebase_refactor.md`](../full_codebase_refactor.md) — master plan
- [`CONTRIBUTING.md`](../../../../CONTRIBUTING.md) — development philosophy
- [`07_old_code_porting_audit.md`](07_old_code_porting_audit.md) — record any deferred decisions

**Prerequisite**: Work chunk 00 complete.

---

## Task Understanding

### Requirements

1. **`src/hydro_fetch/exceptions.py`** — custom exception hierarchy:
   - `HydroFetchError` — base exception for all hydro_fetch errors
   - `ConfigurationError` — invalid config, missing required fields, incompatible options
   - `DownloadError` — network failures, S3 access errors, missing remote files
   - `ProcessingError` — data processing failures (corrupt files, unexpected dimensions)
   - `ValidationError` — QA/QC validation failures

2. **`src/hydro_fetch/constants.py`** — physical constants, MRMS grid metadata, product catalog:
   - MRMS CONUS grid bounds (from `__utils.py` lines 44-47)
   - Product metadata registry: canonical names → S3 paths, native resolution, expected timestep count
   - Standard compression settings (from `__utils.py` `define_zarr_compression`)
   - Physical constants (e.g., `MM_PER_INCH = 25.4` from `__filepaths.py`)
   - Correction factor bounds (from `__utils.py` lines 56-57)

### Key Design Decisions

- Exceptions must include context (file paths, return codes) per `CONTRIBUTING.md` "Preserve context in exceptions"
- All module-level constants from `__utils.py` and `__filepaths.py` that are not case-study-specific belong here
- Product metadata is a dict-of-dicts (or dataclass) mapping canonical names to their properties — this becomes the single source of truth for product info used by download managers and config validation

### Success Criteria

- All exceptions are importable: `from hydro_fetch.exceptions import ConfigurationError`
- All constants are importable: `from hydro_fetch.constants import MRMS_CONUS_BOUNDS`
- Product metadata can be looked up by canonical name

---

## Evidence from Codebase

Inspect before implementing:

1. `_old_code_to_refactor/hpc/__utils.py` — grid coordinates (lines 44-47), compression settings (line 71-76), correction bounds (lines 56-57), chunking parameters (lines 50-66)
2. `_old_code_to_refactor/local/__filepaths.py` — `MM_PER_INCH = 25.4` (line 87), chunking parameters (lines 64-74)
3. `docs/data_sources.md` (from chunk 00) — product catalog to encode in constants

---

## File-by-File Change Plan

### New Files

| File | Purpose |
|------|---------|
| `src/hydro_fetch/exceptions.py` | Custom exception hierarchy with context preservation |
| `src/hydro_fetch/constants.py` | Physical constants, MRMS grid bounds, product metadata registry |

### Modified Files

| File | Change |
|------|--------|
| `src/hydro_fetch/__init__.py` | Remove placeholder `hello()` function; add `__version__` only |

---

## Risks and Edge Cases

| Risk | Mitigation |
|------|-----------|
| Constants from old code may be Norfolk-specific | Only promote truly universal constants; case-study values go in YAML config |
| Product metadata registry may grow; simple dict may not scale | Start with dict-of-dicts; promote to dataclass or NamedTuple if it grows beyond 5-6 products |

---

## Validation Plan

```bash
conda run -n hydro_fetch python -c "
from hydro_fetch.exceptions import HydroFetchError, ConfigurationError, DownloadError, ProcessingError, ValidationError
from hydro_fetch.constants import MRMS_CONUS_BOUNDS, PRODUCT_METADATA
print('All imports OK')
print(f'Products: {list(PRODUCT_METADATA.keys())}')
"
```

---

## Definition of Done

- [ ] `src/hydro_fetch/exceptions.py` implemented with full hierarchy
- [ ] Each exception class accepts context kwargs and formats them into the message
- [ ] `src/hydro_fetch/constants.py` implemented with MRMS grid bounds, product metadata, compression defaults
- [ ] Product metadata registry maps canonical names to S3 paths, native resolution, format
- [ ] No Norfolk-specific values in constants (those go in YAML config)
- [ ] Placeholder `hello()` removed from `__init__.py`
- [ ] All imports pass smoke test
- [ ] `ruff check` and `ruff format` pass
- [ ] **Move this document to `../implemented/` once all boxes above are checked**
