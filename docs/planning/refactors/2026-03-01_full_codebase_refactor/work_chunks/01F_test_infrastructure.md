# Work Chunk 01F: Test Infrastructure and Fixtures

**Phase**: 1F — Foundation
**Created**: 2026-03-01

---

## Before Proceeding

- [`full_codebase_refactor.md`](../full_codebase_refactor.md) — master plan
- [`CONTRIBUTING.md`](../../../../CONTRIBUTING.md) — development philosophy
- [`07_old_code_porting_audit.md`](07_old_code_porting_audit.md) — record any deferred decisions

**Prerequisites**: Work chunks 01A through 01E complete.

---

## Task Understanding

### Requirements

1. **`tests/conftest.py`** — shared test fixtures for the entire test suite:
   - `sample_precip_dataset` — small synthetic xarray Dataset with precipitation-like data. Dimensions: `(time, latitude, longitude)` with ~10 timesteps, ~5x5 spatial grid. Includes realistic coordinate values (lat/lon in Norfolk-like range). Has `original_temporal_resolution` and `original_spatial_resolution` attrs set.
   - `sample_precip_dataset_with_gaps` — same as above but with some timesteps missing (NaN), for testing `missing_duration_min` computation.
   - `tmp_output_dir` — `tmp_path`-based fixture returning a temporary directory for output files. Cleaned up automatically by pytest.
   - `sample_pipeline_yaml` / `sample_system_yaml` — fixtures that write minimal valid YAML configs to a temporary directory and return the file paths. These use the minimal required fields from `PipelineConfig` and `SystemConfig`.
   - `sample_aoi_gdf` — a small GeoDataFrame with a single polygon (Norfolk-like bounding box) in EPSG:4326.
   - `norfolk_pipeline_yaml` / `norfolk_system_yaml` — paths to the actual Norfolk YAML files in `cases/norfolk/`. These are for smoke tests only (they may reference files that don't exist in the test environment).

2. **`tests/test_config.py`** — tests for the config model and loader:
   - Test `PipelineConfig` instantiation from a valid dict
   - Test `SystemConfig` instantiation from a valid dict
   - Test `load_pipeline_config()` from a YAML file
   - Test `load_system_config()` from a YAML file
   - Test validation errors: missing required fields, invalid `run_mode`, invalid `output_format`, invalid `clip_mode`
   - Test toggle validation: bias correction enabled without the reference product
   - Test `end_date: "latest"` parsing
   - Test relative path resolution in loader
   - Norfolk YAML smoke tests: parametrized over all YAML files in `cases/norfolk/`, verify they parse without error

3. **`tests/test_io.py`** — tests for the I/O layer:
   - Round-trip test: zarr write then read, verify data equality and attrs preservation
   - Round-trip test: NetCDF write then read, verify data equality and attrs preservation
   - Round-trip test: CSV write then read, verify DataFrame equality
   - Test that `missing_duration_min` DataArray survives round-trip
   - Test that compression is applied (zarr store size < uncompressed size)
   - Test that `ProcessingError` is raised for nonexistent files
   - Test GRIB2 reader coordinate cleanup (if a sample GRIB2 file is available; otherwise mark as `pytest.mark.skip` with reason)

### Key Design Decisions

- **Synthetic data over real data** — tests use small synthetic datasets, not real MRMS data. This keeps the test suite fast and avoids storing large binary files in the repo. Real data is tested only in Phase 6 (end-to-end validation).
- **Norfolk YAML smoke tests are parametrized** — use `pytest.mark.parametrize` with `glob("cases/norfolk/*.yaml")` to automatically test all YAML files. This ensures new configs are tested without updating the test file.
- **Testing constraint: max 3-5 CONUS files locally** — per the master plan risk table. Tests that touch real data must clean up after themselves. This chunk does not involve real data, but the constraint is documented in `conftest.py` for future chunks.
- **Fixtures produce minimal valid objects** — fixtures use the smallest possible data that exercises the code path. This avoids tests that are slow due to unnecessary data size.
- **No mocking of I/O in I/O tests** — `test_io.py` tests actual file reads/writes to temporary directories. These are integration tests for the I/O layer, not unit tests.

### Success Criteria

- `pytest tests/test_config.py` passes with all config tests green
- `pytest tests/test_io.py` passes with all I/O round-trip tests green
- Norfolk YAML smoke tests are discovered and run automatically
- All fixtures are importable in any test file via `conftest.py`
- Test suite runs in under 30 seconds

---

## Evidence from Codebase

Inspect before implementing:

1. `cases/norfolk/pipeline.yaml` and `cases/norfolk/system.yaml` (from chunk 00) — the YAML files that Norfolk smoke tests will parse.
2. `src/hydro_fetch/config/model.py` (from chunk 01B) — the Pydantic models that config tests will exercise. Review all validators and required fields to ensure tests cover them.
3. `src/hydro_fetch/io/writers.py` (from chunk 01D) — the writer function signatures. Round-trip tests must match these exactly.
4. `src/hydro_fetch/io/readers.py` (from chunk 01D) — the reader function signatures.
5. `src/hydro_fetch/process/grib_io.py` (from chunk 01D) — GRIB2 reader. Determine if a sample GRIB2 file is available for testing or if this test should be skipped.
6. `_old_code_to_refactor/hpc/__utils.py` lines 44-47 — MRMS CONUS grid bounds. Use these to create realistic (but much smaller) synthetic coordinate arrays for test fixtures.

---

## File-by-File Change Plan

### New Files

| File | Purpose |
|------|---------|
| `tests/conftest.py` | Shared fixtures: synthetic datasets, temp dirs, sample YAML configs, sample AOI |
| `tests/test_config.py` | Config model and loader tests, Norfolk YAML smoke tests |
| `tests/test_io.py` | I/O round-trip tests for zarr, NetCDF, CSV |

### Modified Files

| File | Change |
|------|--------|
| None | No existing files are modified in this chunk |

---

## Risks and Edge Cases

| Risk | Mitigation |
|------|-----------|
| Norfolk YAML files may reference AOI files that don't exist on the test machine | Smoke tests only verify YAML parsing (Pydantic validation), not file existence of referenced paths. Use `model_config` or a test flag to skip file-existence validators if needed. |
| `cfgrib` / `eccodes` may not be available in the test environment | GRIB2 test is marked `pytest.mark.skip` with reason if cfgrib is not importable |
| Temporary directories may not be cleaned up if a test crashes | Use pytest's built-in `tmp_path` fixture which handles cleanup. Avoid creating files outside `tmp_path`. |
| Norfolk YAML glob may find zero files if chunk 00 is incomplete | Add an explicit assertion: `assert len(yaml_files) > 0, "No Norfolk YAML files found — is chunk 00 complete?"` |
| Test fixtures may become stale as the config model evolves in later chunks | Keep fixtures minimal — only set required fields. Add new fixture variants in later chunks' test files rather than modifying conftest. |

---

## Validation Plan

```bash
# Run all tests
conda run -n hydro_fetch pytest tests/test_config.py tests/test_io.py -v

# Verify fixture availability
conda run -n hydro_fetch pytest tests/conftest.py --collect-only

# Verify Norfolk smoke tests are discovered
conda run -n hydro_fetch pytest tests/test_config.py -k "norfolk" --collect-only

# Timing check
conda run -n hydro_fetch pytest tests/test_config.py tests/test_io.py --durations=10

# ruff
conda run -n hydro_fetch ruff check tests/
conda run -n hydro_fetch ruff format --check tests/
```

---

## Documentation and Tracker Updates

- Update `work_chunks/README.md`: mark 01F status

---

## Definition of Done

- [ ] `tests/conftest.py` implemented with all shared fixtures
- [ ] `sample_precip_dataset` fixture produces a valid xarray Dataset with precipitation-like data and resolution attrs
- [ ] `sample_precip_dataset_with_gaps` fixture includes NaN timesteps for gap testing
- [ ] `sample_pipeline_yaml` and `sample_system_yaml` fixtures produce minimal valid YAML files
- [ ] `sample_aoi_gdf` fixture produces a small GeoDataFrame polygon
- [ ] `tests/test_config.py` implemented with model, loader, validation, and Norfolk smoke tests
- [ ] Toggle validation test: bias correction reference requires corresponding source product
- [ ] Norfolk YAML smoke tests are parametrized and auto-discover all YAML files in `cases/norfolk/`
- [ ] `tests/test_io.py` implemented with zarr, NetCDF, and CSV round-trip tests
- [ ] Round-trip tests verify both data equality and attrs preservation
- [ ] `missing_duration_min` DataArray round-trip is tested
- [ ] GRIB2 test is either implemented (if sample file available) or skipped with reason
- [ ] All tests pass: `pytest tests/test_config.py tests/test_io.py`
- [ ] Test suite runs in under 30 seconds
- [ ] `ruff check` and `ruff format` pass on `tests/`
- [ ] **Move this document to `../implemented/` once all boxes above are checked**
