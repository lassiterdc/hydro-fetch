# Work Chunk 07: Old Code Porting Audit

**Phase**: 7 — Audit and Closure
**Created**: 2026-03-01

---

## Before Proceeding

Review the following documents before making any edits to plans or writing any code:

- [`full_codebase_refactor.md`](../full_codebase_refactor.md) — master refactor plan; the tracking table is the primary reference for what was planned to be ported.
- [`CONTRIBUTING.md`](../../../../CONTRIBUTING.md) — development philosophy.

**Prerequisites**: Phase 6 (end-to-end validation) complete.

---

## Task Understanding

### Requirements

1. **Catalog every file in `_old_code_to_refactor/`**: For each Python file, shell script, and utility module, record:
   - Filename and path
   - What it does (one-line summary)
   - Whether it was ported (and to which new module)
   - If not ported: why (superseded, out of scope, or missed)

2. **Cross-reference against Phases 1-6**: Use the tracking table in `full_codebase_refactor.md` and the implemented work chunk documents to verify completeness.

3. **For each unported item, determine disposition**:
   - **Superseded**: functionality is covered by a different, better approach in the new code
   - **Out of scope**: functionality was intentionally excluded from the refactor scope
   - **Missed**: functionality should have been ported but was overlooked
   - **User decision required**: functionality could be ported but the decision is unclear -- flag for the developer

4. **Standing decisions log**: This section accumulates decisions deferred during earlier chunks. Any time a work chunk defers an old-code decision, it should be recorded here.

5. **Shell script audit**: The utility scripts (`__utils.sh`, `__directories.sh`) contain logic (date calculation, directory setup, output archiving) that may not have been captured in the Python refactor. Audit each function for coverage.

6. **Known deferred items** (from master plan):
   - `local/c_download_nexrad_metadata.py` — NEXRAD station metadata lookup. Exploratory utility, not in main pipeline.

### Key Design Decisions

- **This chunk does not implement anything**: It is a pure audit. Code changes happen only if the audit identifies missed items that the developer decides to port.
- **User decision gates**: Each unported item that is not clearly superseded or out of scope requires an explicit decision from the developer: port, defer, or drop.
- **Completeness over speed**: The audit must cover every file, not just the ones in the tracking table. Shell scripts, utility modules, and local scripts all need review.

### Success Criteria

- Every file in `_old_code_to_refactor/` has an entry in the audit table
- Every entry has a disposition (ported, superseded, out of scope, missed, or pending-decision)
- All "missed" items have been either ported or explicitly deferred by the developer
- All "pending-decision" items have been resolved by the developer
- Shell script utility functions are accounted for

---

## Evidence from Codebase

### Files to Audit

**HPC Python Scripts**:

| File | Description | Expected Disposition |
|------|-------------|---------------------|
| `hpc/__utils.py` | Module-level constants, utility functions (compression, spatial resampling, coordinate conversion) | Ported to `constants.py`, `config/defaults.py`, `process/spatial.py`, `io/writers.py` |
| `hpc/_da_cmbn_to_dly_ncs_frmtd_for_RainyDay.py` | Combine raw MRMS GRIBs into daily NetCDFs formatted for RainyDay | Ported to `process/grib_io.py`, `process/temporal.py` |
| `hpc/_da2_resampling_to_same_tstep.py` | Resample to constant 5-min timestep + bias correction (863 lines) | Ported to `process/temporal.py`, `process/bias_correction.py`, `process/spatial.py` |
| `hpc/_da3_qaqc_resampling.py` | QA/QC on resampled data | Ported to `process/qaqc.py` |
| `hpc/_da3b_qaqc_preprocessing.py` | QA/QC preprocessing | Ported to `process/qaqc.py` |
| `hpc/_da3c_deleting_questionable_data.py` | Delete flagged bad data | Ported to `process/qaqc.py` |
| `hpc/_db_resampling_to_hourly_and_daily_timesteps.py` | Temporal resampling to hourly and daily | Ported to `process/temporal.py` |
| `hpc/_db2_consolidating_qaqc.py` | Consolidate QA/QC outputs | Verify: ported to `process/qaqc.py` or superseded? |
| `hpc/_dc_combining_daily_totals_in_annual_netcdfs.py` | Combine daily totals into annual NetCDFs | Ported to `process/temporal.py` |
| `hpc/_ha_generate_annual_statistics_netcdfs.py` | Generate annual statistics | Ported to `statistics/annual.py` |
| `hpc/_ha2_generate_annual_statistics_netcdfs_stageIV.py` | Annual statistics (StageIV variant) | Superseded: parameterized version in `statistics/annual.py` replaces product-specific scripts |
| `hpc/_hb_generate_annual_statistics_plots.py` | Plot annual statistics | Ported to `viz/annual_stats.py` |
| `hpc/_hb2_generate_annual_statistics_plots_stageIV.py` | Plot annual statistics (StageIV variant) | Superseded: parameterized version in `viz/annual_stats.py` |
| `hpc/_i_extract_mrms_at_gages.py` | Extract MRMS at rain gage locations | Ported to `process/extraction.py` |
| `hpc/_evaluate_errors.py` | Evaluate processing errors | Verify: ported to `process/qaqc.py` or missed? |

**HPC Shell Scripts**:

| File | Description | Expected Disposition |
|------|-------------|---------------------|
| `hpc/__utils.sh` | Utility functions: `is_first_array_job()`, `archive_previous_script_outfiles()`, `determine_month_and_day()` | Superseded: SLURM array logic replaced by Snakemake; date logic replaced by Python `datetime` |
| `hpc/__directories.sh` | Associative array of all directory paths | Ported to `config/model.py` (YAML config) |
| `hpc/aa_download_mrms_nssl.sh` | Download NSSL reanalysis tars | Ported to `acquire/mrms_legacy.py` |
| `hpc/ab_unzip_mrms_grib_nssl.sh` | Unzip NSSL GRIB files | Ported: integrated into `acquire/mrms_legacy.py` tar extraction |
| `hpc/b_download_mrms_quantized_netcdf.sh` | Download quantized NetCDF (deprecated data) | Superseded: data was unreliable per master plan |
| `hpc/c_download_mrms_mesonet.sh` | Download MRMS from Mesonet | Ported to `acquire/mrms_legacy.py` |
| `hpc/d_download_AORC.sh` | Download AORC | Ported to `acquire/aorc.py` |
| `hpc/da_cmbn_to_dly_ncs_frmtd_for_RainyDay.sh` | SBATCH wrapper for _da Python script | Superseded: Snakemake rules replace SBATCH wrappers |
| `hpc/da2_resampling_to_same_tstep.sh` | SBATCH wrapper for _da2 | Superseded |
| `hpc/da3_qaqc_resampling.sh` | SBATCH wrapper for _da3 | Superseded |
| `hpc/da3b_qaqc_preprocessing.sh` | SBATCH wrapper for _da3b | Superseded |
| `hpc/da3c_deleting_questionable_data.sh` | SBATCH wrapper for _da3c | Superseded |
| `hpc/da3_deleting_scratch.sh` | Delete scratch files | Superseded: Snakemake `temp()` handles this |
| `hpc/db_resampling_to_hourly_and_daily_timesteps.sh` | SBATCH wrapper for _db | Superseded |
| `hpc/db2_consolidationg_qaqc.sh` | SBATCH wrapper for _db2 | Superseded |
| `hpc/g_mrms_delete_raw_data.sh` | Delete raw MRMS data | Superseded: Snakemake `temp()` in local_clip mode |
| `hpc/i_extract_mrms_data_at_gages.sh` | SBATCH wrapper for _i | Superseded |
| `hpc/_script_output_monitoring.sh` | Monitor script outputs | Superseded: Snakemake logging |

**Local Python Scripts**:

| File | Description | Expected Disposition |
|------|-------------|---------------------|
| `local/__filepaths.py` | Local path definitions, constants | Ported to `config/model.py`, `constants.py` |
| `local/a0_qaqc_bias_corrected_mrms_data.py` | QA/QC visualization (hexbin) | Ported to `viz/qaqc.py` |
| `local/a1_created_daily_and_monthly_local_mrms_netcdfs.py` | Daily/monthly aggregation | Ported to `process/temporal.py` |
| `local/a2_create_mrms_vs_gage_csv.py` | MRMS vs gage CSV creation | Ported to `compare/products.py` |
| `local/b_generate_visualizations_of_gaga_vs_mrms_events.py` | Gage vs MRMS event visualization | Ported to `viz/comparison.py` |
| `local/c_download_nexrad_metadata.py` | NEXRAD station metadata lookup | **Known deferred** -- user decision required |
| `local/d_compare_gaga_vs_mrms_events_vs_stageIV.py` | Gage vs MRMS vs StageIV comparison | Ported to `compare/products.py`, `viz/comparison.py` |
| `local/_hb_generate_annual_statistics_plots.py` | Local annual statistics plots | Ported to `viz/annual_stats.py` |

---

## File-by-File Change Plan

### New Files

None -- this is an audit chunk. The audit itself is documented in this file (the tables above are filled in during execution).

### Modified Files

| File | Change |
|------|--------|
| This document | Populate audit tables with actual dispositions after reviewing each file |
| `full_codebase_refactor.md` | Update final tracking table status; mark Phase 7 and overall refactor as complete |

---

## Risks and Edge Cases

| Risk | Mitigation |
|------|-----------|
| Old code contains functionality not described in any planning document | This is exactly what the audit is for -- audit every file, not just tracked ones |
| Some old code functions are partially ported (logic split across new modules) | Cross-reference function-by-function, not just file-by-file, for the large scripts (_da2, __utils.py) |
| Developer may want to defer items indefinitely | Record the decision and rationale; "defer" is a valid outcome but must be explicit |
| `_evaluate_errors.py` and `_db2_consolidating_qaqc.py` may contain non-obvious logic | Read these files in full during the audit to determine if any unique logic was missed |

---

## Validation Plan

```bash
# List all files in old code directory
find _old_code_to_refactor/ -type f | sort

# Verify every file appears in the audit table above
# (manual check during audit)

# Verify all tracking table entries in full_codebase_refactor.md have a final status
```

---

## Documentation and Tracker Updates

- Update `full_codebase_refactor.md`: mark all tracking table entries with final status; mark Phase 7 complete
- This document becomes the definitive record of what was and was not ported

---

## Standing Decisions Log

Record deferred decisions from earlier work chunks here as they arise:

| Date | Source Chunk | Decision | Item | Rationale |
|------|-------------|----------|------|-----------|
| 2026-03-01 | Master plan | Deferred | `local/c_download_nexrad_metadata.py` | NEXRAD station metadata lookup; exploratory utility, not in main pipeline |
| | | | | |

*(Add entries as earlier chunks are implemented and deferral decisions are made)*

---

## Definition of Done

- [ ] Every file in `_old_code_to_refactor/` has an entry in the audit tables
- [ ] Every entry has a disposition: ported (with destination), superseded (with rationale), out of scope, missed, or pending-decision
- [ ] All "missed" items are either ported or explicitly deferred by the developer
- [ ] All "pending-decision" items are resolved by the developer (port, defer, or drop)
- [ ] Shell script utility functions (`__utils.sh`, `__directories.sh`) are individually accounted for
- [ ] `_evaluate_errors.py` and `_db2_consolidating_qaqc.py` are read in full and their logic verified as ported or superseded
- [ ] Standing decisions log is up to date
- [ ] `full_codebase_refactor.md` tracking table has final status for all entries
- [ ] Developer has reviewed and approved all disposition decisions
- [ ] **Move this document to `../implemented/` once all boxes above are checked**
