# Work Chunk 06: End-to-End Case Study Validation

**Phase**: 6 — Validation
**Created**: 2026-03-01

---

## Before Proceeding

Review the following documents before making any edits to plans or writing any code:

- [`full_codebase_refactor.md`](../full_codebase_refactor.md) — master refactor plan; update it if any decisions made here affect the overall plan.
- [`CONTRIBUTING.md`](../../../../CONTRIBUTING.md) — development philosophy.
- [`07_old_code_porting_audit.md`](07_old_code_porting_audit.md) — record any deferred old code decisions here.

**Prerequisites**: All prior phases (0-5) complete.

---

## Task Understanding

### Requirements

1. **Norfolk case study -- local_clip mode**:
   - Run the complete pipeline using `cases/norfolk/pipeline.yaml` in `local_clip` mode
   - Small date range (e.g., 3-5 days) to keep download volume manageable
   - AOI: Norfolk study area polygon
   - Validate: all configured products are downloaded, clipped, processed, and output
   - Verify raw CONUS files are deleted after clipping (temp file behavior)
   - Check output file naming matches Decision 1 conventions
   - Verify output values are physically reasonable (precipitation rates > 0, within expected ranges)

2. **Small CONUS subset -- hpc_conus mode**:
   - Run pipeline in `hpc_conus` mode for the same date range
   - Do not process full CONUS (too large for validation); instead, validate that the workflow structure is correct via dry-run, then process a small date range
   - Verify that output products are generated for the full grid
   - Compare selected outputs (at Norfolk AOI extent) against `local_clip` outputs -- should be numerically identical within the AOI

3. **Incremental download validation**:
   - Run the pipeline once for a date range
   - Run again with the same date range
   - Verify no files are re-downloaded (incremental mode)
   - Run again with an extended date range
   - Verify only the new dates are downloaded

4. **Output validation**:
   - All expected products generated (per pipeline config)
   - Correct file naming: `{product_name}_{timestep}.zarr` (or `.nc`)
   - Output metadata: check xarray attrs for `original_temporal_resolution`, `original_spatial_resolution`
   - `missing_duration_min` variable present in processed outputs (Decision 6)
   - Comparison metrics produced (from 05A)
   - Visualization plots generated (from 05B, 05C)

5. **Comparison against old code** (where feasible):
   - If old code outputs are available for Norfolk, compare selected metrics
   - This is a sanity check, not a regression test -- the new code uses different products (QPE Pass2 vs StageIV)

### Key Design Decisions

- **This is a validation chunk, not a code-writing chunk**: The primary deliverable is evidence that the pipeline works correctly. Code changes are limited to bug fixes discovered during validation.
- **Small date range**: The validation uses 3-5 days of data to keep download times reasonable while still exercising the full pipeline.
- **Numerical identity within AOI**: `local_clip` and `hpc_conus` outputs should match within the AOI extent. Small floating-point differences from processing order may be acceptable -- document any differences found.
- **Bug fixes go back to the originating chunk**: If validation reveals a bug in, e.g., the bias correction module, the fix is implemented and documented as a revision to chunk 02C, not in this chunk.

### Success Criteria

- Complete pipeline run succeeds in `local_clip` mode without errors
- Complete pipeline run succeeds in `hpc_conus` mode (dry-run for full, actual run for small date range)
- Incremental download verified (no re-downloads on second run)
- All expected output files are generated with correct naming
- Output values are physically reasonable
- `local_clip` and `hpc_conus` outputs match within AOI extent
- At least one visualization plot is generated successfully

---

## Evidence from Codebase

Inspect before running:

1. `cases/norfolk/pipeline.yaml` (from 00) -- pipeline configuration to use
2. `cases/norfolk/system.yaml` (from 00) -- Norfolk geographic parameters
3. All `src/hydro_fetch/` modules -- the code under test
4. `tests/` -- existing tests should pass before validation
5. Old code outputs (if available on disk) for comparison reference

---

## File-by-File Change Plan

### New Files

| File | Purpose |
|------|---------|
| `cases/norfolk/pipeline_validation.yaml` | Validation-specific config: small date range, both run modes |
| `tests/test_e2e_validation.py` | End-to-end validation test script (can be run manually or via pytest) |

### Modified Files

| File | Change |
|------|--------|
| Any module with bugs discovered during validation | Bug fixes -- documented as revisions to originating chunk |
| `full_codebase_refactor.md` | Update Phase 6 status |

---

## Risks and Edge Cases

| Risk | Mitigation |
|------|-----------|
| Validation requires network access for downloads | Run on a machine with internet; cache downloaded files for re-runs |
| Validation date range may fall in a data gap | Choose a date range known to have complete data (check S3 bucket listing first) |
| Full CONUS processing in hpc_conus mode is too slow for validation | Use dry-run for DAG validation; only process full grid for 1-2 days maximum |
| Old code outputs may not be available for comparison | Comparison against old code is best-effort; primary validation is internal consistency |
| Bug fixes discovered during validation may cascade across modules | Fix root causes, not symptoms; update originating chunk docs |

---

## Validation Plan

```bash
# 1. Ensure all existing tests pass
conda run -n hydro_fetch pytest tests/ -v

# 2. Run pipeline in local_clip mode
conda run -n hydro_fetch hydro-fetch run cases/norfolk/pipeline_validation.yaml --profile local

# 3. Verify outputs
conda run -n hydro_fetch python -c "
import xarray as xr
from pathlib import Path
output_dir = Path('outputs/')  # adjust based on config
for f in output_dir.glob('*.zarr'):
    ds = xr.open_zarr(f)
    print(f'{f.name}: {list(ds.data_vars)}, time range: {ds.time.values[0]} - {ds.time.values[-1]}')
"

# 4. Test incremental download
conda run -n hydro_fetch hydro-fetch download cases/norfolk/pipeline_validation.yaml
# Check logs for "no new files to download" or equivalent

# 5. Run hpc_conus mode dry-run
# (modify pipeline_validation.yaml to hpc_conus mode)
conda run -n hydro_fetch hydro-fetch run cases/norfolk/pipeline_validation_hpc.yaml --dry-run

# 6. Compare local_clip vs hpc_conus outputs at Norfolk extent
conda run -n hydro_fetch python -c "
import xarray as xr
# Compare outputs from both modes
# ds_local = xr.open_zarr('outputs_local/...')
# ds_hpc = xr.open_zarr('outputs_hpc/...')
# diff = (ds_local - ds_hpc).max()
# assert diff < 1e-6
"
```

---

## Documentation and Tracker Updates

- Update `full_codebase_refactor.md`: mark Phase 6 status
- Document any bugs found and fixed (with references to originating chunks)
- Record validation results (pass/fail for each criterion)

---

## Definition of Done

- [ ] Pipeline runs successfully in `local_clip` mode with Norfolk AOI and small date range
- [ ] Pipeline runs successfully in `hpc_conus` mode (dry-run + small actual run)
- [ ] Incremental download verified: no re-downloads on second run
- [ ] All expected output products generated with correct naming (Decision 1)
- [ ] Output metadata includes resolution attributes
- [ ] `missing_duration_min` variable present in processed outputs
- [ ] Output values are physically reasonable (documented spot checks)
- [ ] `local_clip` and `hpc_conus` outputs match within AOI (documented comparison)
- [ ] At least one visualization plot generated successfully
- [ ] All existing pytest tests still pass
- [ ] Any bugs discovered are fixed and documented in originating chunk
- [ ] Validation results documented
- [ ] **Move this document to `../implemented/` once all boxes above are checked**
