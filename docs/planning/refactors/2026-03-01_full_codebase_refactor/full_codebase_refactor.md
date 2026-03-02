# Full Codebase Refactor: SBATCH Scripts to Snakemake-Managed Library

## Task Understanding

### Requirements

1. Refactor `_old_code_to_refactor/` (~7,200 lines across 31 Python files, 20 shell scripts, and 2 utility modules) into a system-agnostic Python library (`hydro_fetch`)
2. Use Pydantic models + YAML configs for all user-defined inputs
3. Implement Snakemake-based workflow orchestration with two run modes:
   - **Local-clip mode**: Downloads one timestep at a time, clips to user-provided AOI polygon, then processes. Designed for local PCs with limited storage.
   - **HPC-CONUS mode**: Downloads and processes full CONUS dataset. Requires ~11 TB storage. Can run on HPC or large local machines.
4. Support HPC execution via SLURM (Snakemake executor plugin) for HPC-CONUS mode
5. Support on-demand data refresh ("download new data since last run")
6. Manage four precipitation products:
   - **MRMS PrecipRate** — highest temporal/spatial resolution, radar-only, no bias correction (GRIB2 from AWS or Mesonet archive)
   - **MRMS MultiSensor_QPE_01H_Pass2** — hourly, gage-corrected (GRIB2.gz from `s3://noaa-mrms-pds/CONUS/MultiSensor_QPE_01H_Pass2_00.00/`)
   - **Bias-corrected MRMS** — PrecipRate corrected using the hourly gage-corrected product (derived product)
   - **AORC precipitation** — independent comparison dataset
7. Support cross-comparison of all four products for validation
8. Output formats: zarr, NetCDF (gridded), CSV (gage-extracted time series)
9. Downstream consumer: `multidriver-swg` consumes processed precipitation outputs
10. Phased implementation with each phase independently testable

### Key Constraints

- **MRMS data cannot be spatially subsetted at download time** — each timestep is full CONUS. This drives the two run modes.
- **MRMS gage-corrected product has latency** — Pass2 has 2-hour latency for gage data incorporation. The pipeline must account for this when determining data availability windows.
- **The correct MRMS download source is AWS S3** (`s3://noaa-mrms-pds/`), accessed via `fsspec` with anonymous S3 access. The old code used NSSL archives and Iowa State Mesonet — both should be replaced or supplemented.
- **Bias correction of high-res PrecipRate using hourly gage-corrected product** is a core capability, not optional. The old code had a version of this but used StageIV as the reference; the new code should use `MultiSensor_QPE_01H_Pass2`.
- **AORC** is kept as an alternative bias correction reference and as a comparison dataset.

### Assumptions

- Single-developer codebase; backward compatibility is not a priority (per `CONTRIBUTING.md`)
- Python ≥3.11, targeting 3.12+
- Conda environment `hydro_fetch` with conda-forge channel
- Snakemake for workflow orchestration (matching ss-fha pattern)
- No editable-install dependencies on sibling repos (hydro-fetch is self-contained)

---

## Evidence from Codebase

### Old Pipeline Flow

The old code implements a linear pipeline orchestrated by SBATCH shell scripts:

```
aa: Download MRMS NSSL reanalysis (2001-2011, tar archives)
ab: Unzip NSSL GRIB files
 b: Download MRMS quantized NetCDF (deprecated — data was unreliable)
 c: Download real-time MRMS PrecipRate from Iowa Mesonet (2012+)
 d: Download AORC precipitation
da: Combine raw MRMS GRIBs → daily NetCDFs formatted for RainyDay
da2: Resample to constant 5-min timestep + bias correction (LARGEST: 863 lines)
da3: QA/QC on resampled data
da3b: QA/QC preprocessing
da3c: Delete flagged bad data
db: Resample to hourly and daily timesteps
db2: Consolidate QA/QC outputs
dc: Combine daily totals → annual NetCDFs
ha: Generate annual statistics NetCDFs
ha2: Generate annual statistics (StageIV variant)
hb: Plot annual statistics
hb2: Plot annual statistics (StageIV variant)
 i: Extract MRMS at rain gage locations
```

**Local scripts** mirror some HPC functionality for desktop analysis:
- QA/QC visualization, daily/monthly aggregation, gage-vs-MRMS comparison, NEXRAD metadata download

### Critical Observations

1. **Two completely separate configuration systems** — `hpc/__utils.py` (module-level globals) and `local/__filepaths.py` (return-tuple functions). Neither is complete.
2. **Hardcoded MRMS grid coordinates** — `__utils.py` lines 44-47 define NW/SE corners of the CONUS grid as module-level constants.
3. **Bias correction in `_da2_resampling_to_same_tstep.py`** — 863-line monolith mixing I/O, spatial resampling, bias correction algorithm, and QA/QC. The bias correction reference was StageIV; this must change to `MultiSensor_QPE_01H_Pass2`.
4. **All SBATCH parallelism is file-level** — array jobs process one year or one day at a time. Snakemake can replicate this with wildcard-based rules.
5. **Download scripts use `wget`** — new code should use `fsspec` with S3 filesystem for AWS access (matching the Project Pythia MRMS cookbook pattern).
6. **`cfgrib` is used for GRIB2 reading** — still needed; xarray + cfgrib engine is the standard approach.
7. **Dask is used extensively** for out-of-core processing of large grids. This is appropriate and should be preserved.
8. **The `PrecipRate` product is radar-only** — the old code did not download the gage-corrected MRMS product. The refactor must add this as a new data source.

### Data Sources Reference

| Product | Source URL Pattern | Resolution | Latency | Format |
|---------|-------------------|------------|---------|--------|
| MRMS PrecipRate | `s3://noaa-mrms-pds/CONUS/PrecipRate_00.00/{YYYYMMDD}/` | 1 km × 2 min | Real-time | GRIB2.gz |
| MRMS QPE Pass2 | `s3://noaa-mrms-pds/CONUS/MultiSensor_QPE_01H_Pass2_00.00/{YYYYMMDD}/` | 1 km × 1 hr | 2-hour | GRIB2.gz |
| MRMS NSSL Reanalysis | `griffin-objstore.opensciencedatacloud.org/noaa-mrms-reanalysis/` | varies | Archive | GRIB2 tar |
| MRMS Real-time (Mesonet) | `mtarchive.geol.iastate.edu/{YYYY}/{MM}/{DD}/mrms/ncep/PrecipRate/` | 1 km × 2 min | Archive | GRIB2.gz |
| AORC | TBD — old code had download script but URL not captured | varies | Archive | NetCDF |

**Key reference**: [AWS MRMS Registry](https://registry.opendata.aws/noaa-mrms-pds/), [Project Pythia MRMS Cookbook](https://projectpythia.org/mrms-cookbook/)

---

## Implementation Strategy

### Chosen Approach

Bottom-up refactor following the ss-fha pattern:

1. **Phase 0**: Data source inventory and YAML config setup — force concrete decisions about MRMS products, download URLs, and output formats before writing code
2. **Phase 1**: Foundation — config model, path management, I/O layer, test infrastructure
3. **Phase 2**: Core computation — bias correction algorithms, temporal resampling, spatial clipping, statistics
4. **Phase 3**: Data acquisition — download managers for each source (MRMS PrecipRate, MRMS QPE, AORC, NSSL reanalysis)
5. **Phase 4**: Orchestration — Snakemake workflow builder, two run modes, CLI entry point
6. **Phase 5**: Visualization and cross-comparison
7. **Phase 6**: Validation — end-to-end test with known dataset
8. **Phase 7**: Old code porting audit — catalog everything in `_old_code_to_refactor/` that wasn't ported, prompt for user decision on each item

### Alternatives Considered

- **Prefect/Airflow for orchestration**: Rejected — Snakemake is already used in ss-fha, matches the file-based DAG pattern of this pipeline, and has native SLURM support.
- **Direct S3 download in each processing script**: Rejected — separate download step allows caching, resumability, and clear separation of network I/O from computation.
- **Single run mode**: Rejected — the CONUS-scale data requires HPC resources, but most users will want a local subset. Both are first-class requirements.

### Trade-offs

- Snakemake adds complexity but provides DAG-based dependency tracking, resumability, and SLURM integration for free.
- Two run modes increase config complexity but are essential for the user's workflow.
- Supporting both zarr and NetCDF output adds I/O code but provides flexibility for downstream consumers.

---

## Target Architecture

```
src/hydro_fetch/
├── __init__.py
├── config/
│   ├── __init__.py
│   ├── model.py              ← Pydantic v2 config models (PipelineConfig, RunMode, ProductConfig)
│   ├── loader.py             ← YAML loading, template filling, validation
│   └── defaults.py           ← Analysis defaults (chunk sizes, compression settings)
├── constants.py              ← Physical constants, MRMS grid bounds, product metadata
├── exceptions.py             ← Custom exceptions (ConfigurationError, DownloadError, etc.)
├── acquire/
│   ├── __init__.py
│   ├── mrms.py               ← MRMS download manager (PrecipRate + QPE Pass2 from AWS S3)
│   ├── mrms_legacy.py        ← Legacy MRMS downloads (NSSL reanalysis, Mesonet archive)
│   ├── aorc.py               ← AORC download manager
│   └── base.py               ← Abstract download manager base class
├── process/
│   ├── __init__.py
│   ├── grib_io.py            ← GRIB2 reading/writing with xarray+cfgrib
│   ├── spatial.py            ← Spatial operations (clip, resample, reproject)
│   ├── temporal.py           ← Temporal resampling (5-min, hourly, daily, monthly, annual)
│   ├── bias_correction.py    ← Bias correction of PrecipRate using QPE Pass2 (or AORC)
│   ├── qaqc.py               ← QA/QC checks and flagging
│   └── extraction.py         ← Extract gridded data at point locations (gage sites)
├── statistics/
│   ├── __init__.py
│   └── annual.py             ← Annual statistics computation
├── compare/
│   ├── __init__.py
│   └── products.py           ← Cross-comparison of MRMS/QPE/AORC/bias-corrected products
├── io/
│   ├── __init__.py
│   ├── readers.py            ← Read zarr/NetCDF/CSV with consistent interface
│   ├── writers.py            ← Write zarr/NetCDF/CSV with compression settings
│   └── gis_io.py             ← Shapefile/raster I/O with optional clipping
├── viz/
│   ├── __init__.py
│   ├── annual_stats.py       ← Annual statistics plots
│   ├── comparison.py         ← Gage vs MRMS vs StageIV vs AORC comparison plots
│   └── qaqc.py               ← QA/QC hexbin plots
├── workflow/
│   ├── __init__.py
│   ├── builder.py            ← Snakemake workflow generation (Snakefile construction)
│   ├── rules/                ← Snakemake rule templates
│   │   ├── download.smk
│   │   ├── process.smk
│   │   ├── statistics.smk
│   │   └── compare.smk
│   └── profiles/             ← Snakemake profiles (local, slurm)
│       ├── local/config.yaml
│       └── slurm/config.yaml
└── cli.py                    ← CLI entry point (hydro-fetch run, hydro-fetch download, etc.)

cases/                        ← Case study configurations
├── norfolk/
│   ├── system.yaml           ← Norfolk-specific geographic parameters
│   └── pipeline.yaml         ← Pipeline config (products, run mode, AOI, output format)

tests/
├── test_config.py
├── test_acquire.py
├── test_process.py
├── test_bias_correction.py
├── test_extraction.py
└── conftest.py
```

---

## Tracking Table

| Old File | New Location | Status | Phase |
|----------|-------------|--------|-------|
| `hpc/__utils.py` | `config/defaults.py`, `constants.py`, `process/spatial.py`, `io/writers.py` | Pending | 1-2 |
| `hpc/__directories.sh` | `config/model.py` (YAML config) | Pending | 1 |
| `local/__filepaths.py` | `config/model.py` (YAML config) | Pending | 1 |
| `hpc/aa_download_mrms_nssl.sh` | `acquire/mrms_legacy.py` | Pending | 3 |
| `hpc/c_download_mrms_mesonet.sh` | `acquire/mrms_legacy.py` | Pending | 3 |
| `hpc/d_download_AORC.sh` | `acquire/aorc.py` | Pending | 3 |
| `hpc/_da_cmbn_to_dly_ncs_frmtd_for_RainyDay.py` | `process/grib_io.py`, `process/temporal.py` | Pending | 2 |
| `hpc/_da2_resampling_to_same_tstep.py` | `process/temporal.py`, `process/bias_correction.py`, `process/spatial.py` | Pending | 2 |
| `hpc/_da3_qaqc_resampling.py` | `process/qaqc.py` | Pending | 2 |
| `hpc/_da3b_qaqc_preprocessing.py` | `process/qaqc.py` | Pending | 2 |
| `hpc/_da3c_deleting_questionable_data.py` | `process/qaqc.py` | Pending | 2 |
| `hpc/_db_resampling_to_hourly_and_daily_timesteps.py` | `process/temporal.py` | Pending | 2 |
| `hpc/_dc_combining_daily_totals_in_annual_netcdfs.py` | `process/temporal.py` | Pending | 2 |
| `hpc/_ha_generate_annual_statistics_netcdfs.py` | `statistics/annual.py` | Pending | 2 |
| `hpc/_ha2_generate_annual_statistics_netcdfs_stageIV.py` | `statistics/annual.py` | Pending | 2 |
| `hpc/_hb_generate_annual_statistics_plots.py` | `viz/annual_stats.py` | Pending | 5 |
| `hpc/_hb2_generate_annual_statistics_plots_stageIV.py` | `viz/annual_stats.py` | Pending | 5 |
| `hpc/_i_extract_mrms_at_gages.py` | `process/extraction.py` | Pending | 2 |
| `hpc/_evaluate_errors.py` | `process/qaqc.py` | Pending | 2 |
| `local/a0_qaqc_bias_corrected_mrms_data.py` | `viz/qaqc.py` | Pending | 5 |
| `local/a1_created_daily_and_monthly_local_mrms_netcdfs.py` | `process/temporal.py` | Pending | 2 |
| `local/a2_create_mrms_vs_gage_csv.py` | `compare/products.py` | Pending | 5 |
| `local/b_generate_visualizations_of_gaga_vs_mrms_events.py` | `viz/comparison.py` | Pending | 5 |
| `local/c_download_nexrad_metadata.py` | Deferred to Phase 7 audit | Deferred | 7 |
| `local/d_compare_gaga_vs_mrms_events_vs_stageIV.py` | `viz/comparison.py`, `compare/products.py` | Pending | 5 |
| `local/_hb_generate_annual_statistics_plots.py` | `viz/annual_stats.py` | Pending | 5 |
| All SBATCH shell scripts | `workflow/rules/*.smk` + Snakemake profiles | Pending | 4 |

---

## Phased Implementation Plan

### Phase 0: Data Source Inventory and Config Setup
**Goal**: Force concrete decisions about MRMS products, download URLs, AOI specification, and output formats before writing code.

| Chunk | Description | Prerequisites |
|-------|-------------|---------------|
| 00 | MRMS product inventory, data sources doc, and YAML config setup | None |

**Deliverables**:
- `docs/data_sources.md` — catalog of all data products the toolkit downloads, with links to source documentation, download endpoints, known data gaps, spatial/temporal resolution, and product-specific notes
- Case study YAML files for Norfolk
- MRMS data gap tracking strategy — how the workflow measures and documents temporal gaps in downloaded data (e.g., per-day missing-duration DataArray, gap report CSV, or similar)
- Product naming conventions and download URL patterns confirmed

### Phase 1: Foundation
**Goal**: Config model, path management, I/O layer, exceptions, test infrastructure.

| Chunk | Description | Prerequisites |
|-------|-------------|---------------|
| 01A | Exceptions and constants | None |
| 01B | Pydantic config model | 01A |
| 01C | Path management | 01A, 01B |
| 01D | I/O layer (readers/writers for zarr, NetCDF, CSV, GRIB2) | 01A, 01B, 01C |
| 01E | GIS I/O (shapefile/raster with clipping) | 01D |
| 01F | Test infrastructure and fixtures | 01A-01E |

### Phase 2: Core Computation
**Goal**: Pure computation modules — no workflow orchestration, no download logic.

| Chunk | Description | Prerequisites |
|-------|-------------|---------------|
| 02A | Spatial operations (clip, resample, reproject) | 01D, 01E |
| 02B | Temporal resampling (5-min → hourly → daily → monthly → annual) | 01D |
| 02C | Bias correction (PrecipRate using QPE Pass2, or AORC) | 02A, 02B |
| 02D | QA/QC checks and flagging | 01D, 02B |
| 02E | Point extraction (gridded data at gage locations) | 01D, 01E, 02A |
| 02F | Annual statistics | 01D, 02B |

### Phase 3: Data Acquisition
**Goal**: Download managers for each data source. Separated from processing so downloads can be cached and resumed.

| Chunk | Description | Prerequisites |
|-------|-------------|---------------|
| 03A | Base download manager (abstract class, retry logic, progress) | 01B, 01C |
| 03B | MRMS download (PrecipRate + QPE Pass2 from AWS S3) | 03A |
| 03C | MRMS legacy downloads (NSSL reanalysis, Mesonet archive) | 03A |
| 03D | AORC download | 03A |

### Phase 4: Workflow Orchestration (Snakemake)
**Goal**: Snakemake rules, two run modes, CLI entry point.

| Chunk | Description | Prerequisites |
|-------|-------------|---------------|
| 04A | Snakemake rule templates (download, process, statistics, compare) | 02*, 03* |
| 04B | Run mode implementation (local-clip vs HPC-CONUS) | 04A |
| 04C | Snakemake profiles (local, SLURM) | 04A |
| 04D | CLI entry point (`hydro-fetch run`, `hydro-fetch download`) | 04A-04C |

### Phase 5: Visualization and Cross-Comparison
**Goal**: All plotting functions and the four-product comparison workflow.

| Chunk | Description | Prerequisites |
|-------|-------------|---------------|
| 05A | Product cross-comparison (MRMS, QPE, AORC, bias-corrected) | 02C, 02E |
| 05B | Annual statistics plots | 02F |
| 05C | QA/QC and gage-comparison visualization | 02D, 02E, 05A |

### Phase 6: End-to-End Validation
**Goal**: Run the complete pipeline on a small test dataset to validate correctness.

| Chunk | Description | Prerequisites |
|-------|-------------|---------------|
| 06 | Norfolk case study validation | All prior phases |

### Phase 7: Old Code Audit and Porting Decisions
**Goal**: Ensure nothing from the old codebase was silently dropped. Audit all old files against what was ported, catalog anything unaddressed, and prompt the user for a decision on each item.

| Chunk | Description | Prerequisites |
|-------|-------------|---------------|
| 07 | Old code porting audit | 06 |

**Process**: This chunk catalogs every file and function in `_old_code_to_refactor/` and cross-references against what was implemented in Phases 1-6. For each unported item, it records:
- What the old code does
- Whether it's been superseded, is out of scope, or was accidentally missed
- User decision: port, defer, or drop

**Standing decisions log**: Any decisions made during earlier work chunks about deferring old code should be recorded in this chunk's doc as they occur. The final pass through this chunk resolves anything that hasn't been addressed yet.

**Known deferred items**:
- `local/c_download_nexrad_metadata.py` — NEXRAD station metadata lookup. Exploratory utility, not in main pipeline. Deferred here for user decision.

---

## Cross-Cutting Decisions

Decisions that affect multiple work chunks. Resolved decisions include rationale; unresolved decisions are flagged.

### Decision 1: Precipitation product naming convention — **RESOLVED**

**Pattern**: `{source}[_{descriptor}][_crctd_w_{correction_source}]_{timestep}`

- `crctd` is reserved for corrections **we** apply. Products that arrive pre-corrected (like AORC, which uses multiple sources internally) are named by source alone.
- `_w_` ("with") identifies the correction reference when we do the correcting.
- Timestep reflects the **current** resolution of the data at that pipeline stage (not the native/original resolution). When temporal resampling produces a new timestep, the product name updates accordingly (e.g., `mrms_crctd_w_pass2_2min` → `mrms_crctd_w_pass2_1hr`).
- Original resolution metadata is stored in xarray dataset attributes (`attrs["original_temporal_resolution"]`, `attrs["original_spatial_resolution"]`).

**Canonical product names (at native resolution)**:

| Name | Description | Source |
|------|-------------|--------|
| `mrms_2min` | MRMS PrecipRate, radar-only, uncorrected | AWS S3 `PrecipRate_00.00` |
| `mrms_pass2_1hr` | MRMS MultiSensor QPE Pass2, gage-corrected by NOAA | AWS S3 `MultiSensor_QPE_01H_Pass2_00.00` |
| `mrms_crctd_w_pass2_2min` | MRMS PrecipRate bias-corrected using Pass2 (derived) | Computed by pipeline |
| `mrms_crctd_w_aorc_2min` | MRMS PrecipRate bias-corrected using AORC (derived) | Computed by pipeline |
| `aorc_1hr` | AORC precipitation (pre-corrected using multiple sources) | AORC download |

**Usage**:
- Config field names: `products.mrms_2min`, `products.mrms_pass2_1hr`, etc.
- Snakemake wildcards: `{product}` with values from the table above
- Output filenames: `mrms_crctd_w_pass2_1hr.zarr` (after resampling from 2min to 1hr)

**Affects**: 00, 01B, 02C, 03A-03D, 04A, 05A

### Decision 2: AOI specification for local-clip mode — **RESOLVED**

**Decision**: AOI is specified as a path to a vector file (GIS data-type agnostic — shapefile, GeoJSON, GeoPackage, or any format readable by `geopandas.read_file()`). The user also specifies a `clip_mode` toggle:
- `clip_mode: bbox` — clip to the bounding box of the AOI polygon. All grid cells within the rectangular extent are retained. Simpler, no masking overhead.
- `clip_mode: mask` — clip to bbox first (for dimension reduction), then mask cells outside the AOI polygon to NaN. Saves space in chunked formats (zarr) where all-NaN chunks compress to near-zero. More accurate for irregular boundaries — prevents out-of-AOI data from being included in statistics.

**Two-step approach**: Both modes first clip to the bounding box (reducing the grid from CONUS to a regional extent). The `mask` mode then applies the polygon mask as a second step. This means `mask` mode is strictly a superset of `bbox` mode.

**Rationale**: GIS-agnostic input supports the most common geospatial formats without requiring format conversion. The two-step clip+mask approach gives both performance and accuracy benefits. Users who just need a rectangular region can skip the masking overhead.

**Affects**: 01B, 01E, 02A, 04B

### Decision 3: Temporal coverage specification — **RESOLVED**

**Decision**: Support both explicit date ranges AND incremental updates:
- `start_date: YYYY-MM-DD` — required; earliest date to include
- `end_date: YYYY-MM-DD | "latest"` — required; `"latest"` means up to the current date (accounting for product latency)
- `incremental: bool` — when `true`, the download manager tracks the last-downloaded date in a state file (`{output_dir}/.download_state.json`) and only fetches data after that date. When `false`, downloads the full `start_date` → `end_date` range, skipping files that already exist locally.

**Rationale**: Explicit date ranges provide predictability; `"latest"` + `incremental: true` enables the on-demand refresh workflow. The state file approach is simple and transparent (user can inspect/edit it). Skipping existing files (even in non-incremental mode) avoids redundant downloads without complex tracking.

**Affects**: 01B, 03A-03D, 04A

### Decision 4: Output directory structure — **RESOLVED**

**Decision**: Flat structure — `outputs/{product_name}.zarr` (or `.nc`, `.csv`). The product name already encodes source, correction status, and timestep (per Decision 1), so subdirectories would be redundant.

**Threshold**: If the number of output files exceeds ~8, revisit and consider subdirectories (e.g., by product source).

**Affects**: 01C, 01D, 04A

### Decision 5: Incremental download strategy — **RESOLVED**

**Decision**: Primary strategy is **Option 2** (check S3 bucket listing against local files; download missing). This handles both new data and retroactively filled-in gaps.

**Implementation**:
- Download manager lists S3 bucket contents for the configured date range
- Compares against local files (by filename match)
- Downloads any files present on S3 but missing locally
- When previously-missing files are filled in retroactively on S3, the next run picks them up automatically
- **Caveat**: Filled-in timesteps require reprocessing of affected daily/aggregate outputs. The download manager should log newly-downloaded files so the user knows which periods need reprocessing. Snakemake's file-timestamp-based rerun triggers may handle this automatically if raw downloads are inputs to processing rules.

**Future enhancement (nice-to-have)**: Option 3 — always re-scan the full date range and skip existing files. This is simpler but slower for large date ranges. Can be added as a `--full-scan` CLI flag.

**Affects**: 03A-03D, 04A

### Decision 6: MRMS data gap tracking — **RESOLVED**

**Decision**: **Per-day missing-duration DataArray** — a DataArray in the final processed dataset showing total missing duration (minutes) per day per grid cell. This integrates gap information directly into the data structure used by downstream consumers.

**Implementation details** (to be refined in work chunk 00):
- DataArray name: `missing_duration_min` (or similar)
- Dimensions: `(time_day, y, x)` — daily aggregation of missing timesteps
- Value: total minutes of missing data for that grid cell on that day
- Computed during the temporal aggregation step (02B) by counting expected vs. actual timesteps per day
- Stored alongside the precipitation data in the same zarr/NetCDF output

**Affects**: 00, 01D, 02B, 02D, 04A

### Decision 7: Bias correction reference product — **RESOLVED**

**Decision**: The primary bias correction reference is `MultiSensor_QPE_01H_Pass2` (gage-corrected hourly MRMS). AORC is available as an alternative reference, selectable via config. The old code used StageIV — this is being replaced.

**Rationale**: QPE Pass2 uses the same MRMS sensor infrastructure, just with gage correction. This makes the correction more directly comparable than using an entirely different product (AORC or StageIV).

**Affects**: 02C, 05A

---

## Risk Table

| Risk | Severity | Mitigation | Lesson source |
|------|----------|------------|---------------|
| MRMS AWS bucket structure changes or product names change | High | Pin product paths in constants; add integration test that validates bucket listing | New |
| Bias correction algorithm may need rethinking for QPE Pass2 (different from StageIV) | High | Implement old StageIV-based correction first as reference, then adapt for QPE Pass2 | ss-fha: ported-function testing |
| Two run modes double the Snakemake rule complexity | Medium | Factor rules into reusable components; run mode affects input/output paths, not computation logic | New |
| CONUS-scale data (11 TB) makes local testing infeasible | Medium | Test both modes locally; store at most 3-5 CONUS files at a time, clear after each test. Benchmark download times and consider caching a few files for downstream workflow tests. Integration tests use Norfolk AOI. | ss-fha: Phase 0 + user constraint |
| Config model complexity grows as products are added | Medium | Identify all config fields in Phase 0; implement incrementally | ss-fha: lesson 4 |
| Download interruptions lose partial progress | Medium | Download manager tracks per-file completion; Snakemake handles rule-level resumability | New |
| MRMS data has known temporal gaps that could silently bias statistics | Medium | Explicitly track and document gaps; QA/QC module flags gap-affected periods; gap report as a pipeline output | New |
| Old code may contain Norfolk-specific hardcoding beyond what's visible | Low | Phase 0 data inventory forces explicit enumeration of all assumptions | ss-fha: Phase 0 |
