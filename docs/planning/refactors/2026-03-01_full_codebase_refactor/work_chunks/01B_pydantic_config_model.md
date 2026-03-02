# Work Chunk 01B: Pydantic v2 Config Model

**Phase**: 1B — Foundation
**Created**: 2026-03-01

---

## Before Proceeding

- [`full_codebase_refactor.md`](../full_codebase_refactor.md) — master plan
- [`CONTRIBUTING.md`](../../../../CONTRIBUTING.md) — development philosophy
- [`07_old_code_porting_audit.md`](07_old_code_porting_audit.md) — record any deferred decisions

**Prerequisite**: Work chunk 01A complete.

---

## Task Understanding

### Requirements

1. **`src/hydro_fetch/config/model.py`** — Pydantic v2 models for pipeline and system configuration:
   - `PipelineConfig` — top-level model loaded from `pipeline.yaml`:
     - `run_mode`: Literal["local_clip", "hpc_conus"]
     - `products`: dict mapping canonical product names to enabled/disabled booleans (product names per Decision 1: `mrms_2min`, `mrms_pass2_1hr`, `mrms_crctd_w_pass2`, `mrms_crctd_w_aorc`, `aorc_1hr`)
     - `start_date`: date
     - `end_date`: date | Literal["latest"]
     - `incremental`: bool
     - `output_dir`: Path
     - `output_format`: Literal["zarr", "netcdf"]
     - `study_area_config`: Path — path to the `system.yaml` file
     - `bias_correction_reference`: Literal["pass2", "aorc"] | None
   - `SystemConfig` — loaded from `system.yaml` (referenced by `PipelineConfig.study_area_config`):
     - `study_area_id`: str
     - `crs_epsg`: int
     - `aoi_path`: Path — path to the AOI vector file
     - `clip_mode`: Literal["bbox", "mask"]
     - Geospatial file paths (gage shapefile, coastline, subcatchments, etc.) as optional fields for downstream viz

2. **`src/hydro_fetch/config/loader.py`** — YAML loading functions:
   - `load_pipeline_config(yaml_path: Path) -> PipelineConfig`
   - `load_system_config(yaml_path: Path) -> SystemConfig`
   - Both raise `ConfigurationError` (from `hydro_fetch.exceptions`) on validation failure

3. **`src/hydro_fetch/config/__init__.py`** — public re-exports of `PipelineConfig`, `SystemConfig`, `load_pipeline_config`, `load_system_config`

### Key Design Decisions

- **No defaults for case-study-specific parameters** (per CONTRIBUTING.md "Most function arguments should not have defaults"). Fields like `crs_epsg`, `aoi_path`, `start_date`, `end_date`, `output_dir` must be explicitly set by the user. The only fields with defaults should be those where a default is almost always correct (e.g., `incremental: false`).
- **Product naming per Decision 1** — canonical names are the dict keys in the `products` field. The derived products (`mrms_crctd_w_pass2`, `mrms_crctd_w_aorc`) are toggles for whether the pipeline should compute them, not downloads.
- **AOI per Decision 2** — `aoi_path` points to any vector file readable by `geopandas.read_file()`. `clip_mode` determines bbox vs mask behavior.
- **Temporal coverage per Decision 3** — `end_date` accepts either a date string or the literal `"latest"`. `incremental` is a separate boolean toggle.
- **Single PipelineConfig type** — no discriminated union needed (unlike ss-fha). All run modes share the same config shape; `run_mode` is a simple literal field.
- **Toggle validation** — if `bias_correction_reference` is `"pass2"`, then `products["mrms_pass2_1hr"]` must be `True`. If `"aorc"`, then `products["aorc_1hr"]` must be `True`. If `bias_correction_reference` is set at all, `products["mrms_2min"]` must also be `True` (it is the product being corrected). This is implemented as a Pydantic `model_validator`.
- **Path resolution** — `aoi_path` and other file paths in `SystemConfig` should be resolved relative to the YAML file's parent directory if they are relative paths. The loader handles this.

### Success Criteria

- `PipelineConfig` and `SystemConfig` can be instantiated from Python dicts and from YAML files
- Validation errors produce clear messages (field name, what was wrong, what was expected)
- Toggle validation catches misconfigurations (e.g., bias correction enabled without the reference product)
- Norfolk YAML files from chunk 00 parse successfully through the loader
- All fields are type-annotated; Pyright reports no errors

---

## Evidence from Codebase

Inspect before implementing:

1. `_old_code_to_refactor/hpc/__utils.py` — module-level globals that served as configuration (lines 7-69): `use_quantized_data`, `gage_id_attribute_in_shapefile`, `lst_quants`, `crxn_upper_bound`, `crxn_lower_bound`, `target_tstep`. Determine which belong in config vs constants.
2. `_old_code_to_refactor/local/__filepaths.py` — the `return_*_filepaths()` functions (lines 112-131) show that configuration was previously scattered across function returns. These path patterns inform the `SystemConfig` geospatial file fields.
3. `_old_code_to_refactor/hpc/__utils.py` lines 56-59 — correction factor bounds and target timestep. These are algorithm parameters, not case-study config. They belong in `constants.py` (already handled in 01A), not in the Pydantic model.
4. `cases/norfolk/pipeline.yaml` and `cases/norfolk/system.yaml` (from chunk 00) — the YAML files that these models must parse.
5. `src/hydro_fetch/constants.py` (from chunk 01A) — `PRODUCT_METADATA` registry provides the list of valid canonical product names for validation.

---

## File-by-File Change Plan

### New Files

| File | Purpose |
|------|---------|
| `src/hydro_fetch/config/__init__.py` | Re-export `PipelineConfig`, `SystemConfig`, `load_pipeline_config`, `load_system_config` |
| `src/hydro_fetch/config/model.py` | Pydantic v2 models: `PipelineConfig`, `SystemConfig` |
| `src/hydro_fetch/config/loader.py` | `load_pipeline_config()`, `load_system_config()` with YAML parsing and path resolution |

### Modified Files

| File | Change |
|------|--------|
| None | No existing files are modified in this chunk |

---

## Risks and Edge Cases

| Risk | Mitigation |
|------|-----------|
| Relative path resolution in YAML is fragile if the working directory changes | Loader resolves all relative paths against the YAML file's parent directory at load time, converting to absolute paths |
| `end_date: "latest"` mixes date and string types, complicating the type annotation | Use `date | Literal["latest"]` union type; Pydantic v2 handles this with discriminated parsing. Add a helper property `resolved_end_date` that returns `date.today()` when value is `"latest"` |
| Product names in `products` dict may drift from `PRODUCT_METADATA` keys | Add a `model_validator` that checks all keys in `products` against `PRODUCT_METADATA.keys()` from `constants.py` |
| Users may forget to enable the source product when enabling a derived product | Toggle validation catches this explicitly with a clear error message |
| YAML files from chunk 00 may use field names that differ from the final model | Chunk 00 YAML files have a provisional-schema header comment; update them if needed during this chunk |

---

## Validation Plan

```bash
# Smoke test: models are importable
conda run -n hydro_fetch python -c "
from hydro_fetch.config import PipelineConfig, SystemConfig, load_pipeline_config, load_system_config
print('All config imports OK')
"

# Load Norfolk YAML files
conda run -n hydro_fetch python -c "
from hydro_fetch.config import load_pipeline_config, load_system_config
from pathlib import Path
pc = load_pipeline_config(Path('cases/norfolk/pipeline.yaml'))
sc = load_system_config(Path('cases/norfolk/system.yaml'))
print(f'PipelineConfig: run_mode={pc.run_mode}, products={pc.products}')
print(f'SystemConfig: study_area_id={sc.study_area_id}, crs_epsg={sc.crs_epsg}')
"

# Validation error test: bias correction without reference product
conda run -n hydro_fetch python -c "
from hydro_fetch.config.model import PipelineConfig
from pydantic import ValidationError
try:
    PipelineConfig(
        run_mode='local_clip',
        products={'mrms_2min': True, 'mrms_pass2_1hr': False, 'aorc_1hr': False},
        start_date='2020-01-01',
        end_date='2020-12-31',
        incremental=False,
        output_dir='/tmp/test',
        output_format='zarr',
        study_area_config='/tmp/system.yaml',
        bias_correction_reference='pass2',
    )
    print('ERROR: should have raised ValidationError')
except ValidationError as e:
    print(f'Correctly caught: {e}')
"

# ruff
conda run -n hydro_fetch ruff check src/hydro_fetch/config/
conda run -n hydro_fetch ruff format --check src/hydro_fetch/config/
```

---

## Documentation and Tracker Updates

- Update `full_codebase_refactor.md`: mark Phase 1B as in-progress/complete
- Update `work_chunks/README.md`: mark 01B status

---

## Definition of Done

- [ ] `src/hydro_fetch/config/model.py` implemented with `PipelineConfig` and `SystemConfig`
- [ ] All required fields have no defaults; only universally-correct defaults are provided
- [ ] `products` field validates keys against `PRODUCT_METADATA` from `constants.py`
- [ ] Toggle validation: bias correction reference requires corresponding source product enabled
- [ ] `end_date` accepts both date values and `"latest"` literal
- [ ] `src/hydro_fetch/config/loader.py` implemented with `load_pipeline_config()` and `load_system_config()`
- [ ] Loader resolves relative paths against YAML file's parent directory
- [ ] Loader raises `ConfigurationError` on validation failure with clear context
- [ ] `src/hydro_fetch/config/__init__.py` re-exports all public symbols
- [ ] Norfolk YAML files from chunk 00 parse successfully
- [ ] `ruff check` and `ruff format` pass
- [ ] Pyright reports no errors on config module
- [ ] **Move this document to `../implemented/` once all boxes above are checked**
