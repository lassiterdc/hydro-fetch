# Work Chunk 00: Data Source Inventory and Config Setup

**Phase**: 0 — Pre-Implementation (Data Inventory and Config)
**Created**: 2026-03-01

---

## Before Proceeding

Review the following documents before making any edits to plans or writing any code:

- [`full_codebase_refactor.md`](../full_codebase_refactor.md) — master refactor plan; update it if any decisions made here affect the overall plan.
- [`CONTRIBUTING.md`](../../../../CONTRIBUTING.md) — project development philosophy.
- [`07_old_code_porting_audit.md`](07_old_code_porting_audit.md) — record any deferred old code decisions here.

**Prerequisite**: None — this is the first task.

---

## Task Understanding

### Requirements

1. **`docs/data_sources.md`** — catalog of all precipitation data products the toolkit downloads, including:
   - Product name (per Decision 1 naming convention)
   - Source organization and data program
   - Download endpoint / URL pattern
   - Spatial resolution, temporal resolution, latency
   - File format
   - Known data gaps and quality notes
   - Links to official documentation
   - Notes on the correct product to use (e.g., Pass2 vs Pass1 vs radar-only)

2. **`cases/norfolk/system.yaml`** — Norfolk-specific geographic parameters:
   - `crs_epsg` (to be confirmed from old code shapefiles)
   - AOI path (shapefile or GeoJSON for Norfolk watershed/study area)
   - `clip_mode: bbox` or `mask`

3. **`cases/norfolk/pipeline.yaml`** — Pipeline configuration:
   - Which products to download (`mrms_2min`, `mrms_pass2_1hr`, `aorc_1hr`)
   - Date range (`start_date`, `end_date`)
   - Run mode (`local_clip` or `hpc_conus`)
   - Output format (zarr, netcdf)
   - Output directory
   - Incremental download toggle

4. **MRMS data gap tracking strategy** — design the `missing_duration_min` DataArray:
   - Exact variable name, dimensions, units
   - How expected timestep count is determined per product
   - Where in the pipeline it is computed
   - How it is stored (same file as precipitation data, or separate)

5. **Download URL pattern confirmation** — verify all S3 bucket paths and file naming patterns by examining actual bucket contents or documentation.

### Key Design Decisions

- **No code is written in this chunk.** Deliverables are YAML files, documentation, and design decisions only.
- Product naming convention follows Decision 1 from the master plan.
- AOI specification follows Decision 2 (GIS-agnostic vector file + `clip_mode`).
- Temporal coverage follows Decision 3 (`start_date` / `end_date` / `"latest"` / `incremental`).

### Success Criteria

- All data products are cataloged with verified download endpoints
- Norfolk YAML files parse without error via `python -c "import yaml; yaml.safe_load(open('...'))"`
- Data gap tracking strategy is documented with enough detail for 02B implementation
- AORC download endpoint is identified (currently TBD in master plan)

---

## Evidence from Codebase

Before proceeding, inspect:

1. `_old_code_to_refactor/hpc/__utils.py` — hardcoded MRMS grid coordinates (lines 44-47), chunking parameters, bias correction settings
2. `_old_code_to_refactor/hpc/__directories.sh` — all directory paths and data flow
3. `_old_code_to_refactor/local/__filepaths.py` — local path definitions, StageIV references
4. `_old_code_to_refactor/hpc/aa_download_mrms_nssl.sh` — NSSL reanalysis download URL
5. `_old_code_to_refactor/hpc/c_download_mrms_mesonet.sh` — Mesonet download URL pattern
6. `_old_code_to_refactor/hpc/d_download_AORC.sh` — AORC download URL (currently TBD)
7. `_old_code_to_refactor/hpc/_da2_resampling_to_same_tstep.py` — bias correction parameters and StageIV references
8. AWS MRMS Registry: https://registry.opendata.aws/noaa-mrms-pds/
9. Project Pythia MRMS Cookbook: https://projectpythia.org/mrms-cookbook/

---

## File-by-File Change Plan

### New Files

| File | Purpose |
|------|---------|
| `docs/data_sources.md` | Comprehensive catalog of all precipitation data products |
| `cases/norfolk/system.yaml` | Norfolk geographic parameters (CRS, AOI, clip mode) |
| `cases/norfolk/pipeline.yaml` | Pipeline config (products, dates, run mode, outputs) |

### Modified Files

| File | Change |
|------|--------|
| `full_codebase_refactor.md` | Update AORC source URL (currently TBD); update Phase 0 status |
| `work_chunks/README.md` | Mark 00 as complete |

---

## Risks and Edge Cases

| Risk | Mitigation |
|------|-----------|
| AORC download URL not found in old code | Search the download shell script; if URL is missing, web search for current AORC data access |
| S3 bucket paths may have changed since MRMS Cookbook was written | Verify by listing bucket contents with `aws s3 ls --no-sign-request` or `fsspec` |
| Norfolk AOI shapefile may not exist in this repo | Check if old code references a Norfolk shapefile; if not, note as a data gap |
| YAML schema is provisional — field names may change in 01B | Add header comment noting provisional status, same pattern as ss-fha chunk 00 |

---

## Validation Plan

```bash
# Each YAML parses without error
python -c "import yaml; yaml.safe_load(open('cases/norfolk/system.yaml'))"
python -c "import yaml; yaml.safe_load(open('cases/norfolk/pipeline.yaml'))"

# data_sources.md exists and has content for each product
wc -l docs/data_sources.md  # should be substantial
```

---

## Documentation and Tracker Updates

- Update `full_codebase_refactor.md`: resolve AORC URL TBD, update Phase 0 section
- Update `work_chunks/README.md`: mark 00 as complete

---

## Definition of Done

- [ ] `docs/data_sources.md` created with entries for all 5 products (mrms_2min, mrms_pass2_1hr, mrms_crctd_w_pass2, mrms_crctd_w_aorc, aorc_1hr)
- [ ] Each product entry includes: source, URL pattern, resolution, format, known gaps, documentation links
- [ ] AORC download endpoint identified and documented (no longer TBD)
- [ ] `cases/norfolk/system.yaml` created with CRS and AOI specification
- [ ] `cases/norfolk/pipeline.yaml` created with products, date range, run mode, output config
- [ ] Data gap tracking strategy documented (variable name, dimensions, computation location)
- [ ] All YAML files pass `yaml.safe_load()` without error
- [ ] Each YAML has a provisional-schema header comment
- [ ] `full_codebase_refactor.md` updated with resolved items
- [ ] **Move this document to `../implemented/` once all boxes above are checked**
