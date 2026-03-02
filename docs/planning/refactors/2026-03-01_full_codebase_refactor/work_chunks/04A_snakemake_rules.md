# Work Chunk 04A: Snakemake Rule Templates

**Phase**: 4A — Workflow Orchestration (Rules)
**Created**: 2026-03-01

---

## Before Proceeding

Review the following documents before making any edits to plans or writing any code:

- [`full_codebase_refactor.md`](../full_codebase_refactor.md) — master refactor plan; update it if any decisions made here affect the overall plan.
- [`CONTRIBUTING.md`](../../../../CONTRIBUTING.md) — development philosophy.
- [`07_old_code_porting_audit.md`](07_old_code_porting_audit.md) — record any deferred old code decisions here.

**Prerequisites**: All Phase 2 (02A-02F) and Phase 3 (03A-03D) work chunks complete.

---

## Task Understanding

### Requirements

1. **`src/hydro_fetch/workflow/builder.py`** — Snakemake workflow builder:
   - Reads `PipelineConfig` (from 01B) and generates a Snakefile
   - Determines which rules to include based on config (enabled products, run mode, output formats)
   - Resolves wildcards: `{product}` maps to canonical product names from Decision 1
   - Provides `build_workflow(config_path) -> Path` returning path to generated Snakefile

2. **`src/hydro_fetch/workflow/rules/download.smk`** — download rules:
   - One rule per download source (mrms_s3, mrms_nssl, mrms_mesonet, aorc)
   - Rule inputs: pipeline config
   - Rule outputs: raw downloaded files (or download completion marker)
   - Calls Python functions from `hydro_fetch.acquire` module

3. **`src/hydro_fetch/workflow/rules/process.smk`** — processing rules:
   - Rules for: clip to AOI, temporal resampling, bias correction, QA/QC
   - DAG: `raw_download → clip_to_aoi → bias_correct → temporal_resample → qaqc`
   - Each rule calls functions from `hydro_fetch.process` module
   - Rules are parameterized by `{product}` wildcard

4. **`src/hydro_fetch/workflow/rules/statistics.smk`** — statistics rules:
   - Rules for: annual statistics computation, point extraction at gage locations
   - DAG: `processed_data → annual_statistics`, `processed_data → point_extraction`
   - Calls functions from `hydro_fetch.statistics` and `hydro_fetch.process.extraction`

5. **`src/hydro_fetch/workflow/rules/compare.smk`** — comparison rules:
   - Rules for: cross-product comparison, visualization
   - DAG: `processed_products → product_comparison → comparison_plots`
   - Calls functions from `hydro_fetch.compare` and `hydro_fetch.viz`

6. **Overall DAG**:
   ```
   download → clip/process → bias_correct → temporal_resample → statistics → compare
   ```

### Key Design Decisions

- **Rules call Python functions, not scripts**: Each Snakemake rule uses `run:` or `script:` directives that import and call hydro_fetch module functions. This keeps all logic in the library and makes it testable outside Snakemake.
- **Wildcard-based parameterization**: The `{product}` wildcard resolves to canonical product names (`mrms_2min`, `mrms_pass2_1hr`, `aorc_1hr`, `mrms_crctd_w_pass2_2min`, `mrms_crctd_w_aorc_2min`). This replaces the old SBATCH array-job pattern.
- **builder.py generates the Snakefile**: Rather than a static Snakefile, the builder reads the config and assembles rules dynamically. This allows the rule set to vary by run mode and enabled products.
- **File-based DAG tracking**: Snakemake's native file-timestamp mechanism triggers re-execution when inputs change. Newly-downloaded files (from 03A manifest) automatically trigger reprocessing of affected rules.

### Success Criteria

- `build_workflow()` generates a syntactically valid Snakefile
- Generated Snakefile includes only rules relevant to the configured products
- Snakemake dry-run (`snakemake -n`) succeeds with the generated Snakefile
- DAG is correct: processing depends on download, statistics depend on processing, comparison depends on statistics
- Each rule correctly references hydro_fetch module functions

---

## Evidence from Codebase

Inspect before implementing:

1. `_old_code_to_refactor/hpc/__directories.sh` — old directory structure and data flow; maps to Snakemake input/output paths
2. All SBATCH shell scripts (`da_`, `da2_`, `da3_`, `db_`, `dc_`, `ha_`, `hb_`, `i_`) — each becomes one or more Snakemake rules
3. Old pipeline flow from master plan: `aa → ab → c → d → da → da2 → da3 → db → dc → ha → hb → i`
4. `src/hydro_fetch/config/model.py` (from 01B) — `PipelineConfig` fields that control which rules are generated
5. Snakemake documentation for workflow module patterns: https://snakemake.readthedocs.io/

---

## File-by-File Change Plan

### New Files

| File | Purpose |
|------|---------|
| `src/hydro_fetch/workflow/__init__.py` | Package init |
| `src/hydro_fetch/workflow/builder.py` | Workflow builder: config → Snakefile generation |
| `src/hydro_fetch/workflow/rules/download.smk` | Download rules for each data source |
| `src/hydro_fetch/workflow/rules/process.smk` | Processing rules (clip, resample, bias correct, QA/QC) |
| `src/hydro_fetch/workflow/rules/statistics.smk` | Statistics computation rules |
| `src/hydro_fetch/workflow/rules/compare.smk` | Cross-product comparison rules |

### Modified Files

| File | Change |
|------|--------|
| `full_codebase_refactor.md` | Update Phase 4 status; update tracking table for all SBATCH shell scripts |

---

## Risks and Edge Cases

| Risk | Mitigation |
|------|-----------|
| Snakemake rule syntax is tightly coupled to file paths — changes in 01C path management ripple here | builder.py uses path management module to resolve all paths; no hardcoded paths in .smk files |
| Dynamic Snakefile generation is harder to debug than static rules | Generate to a readable file; include comments in generated output; support `--dry-run` for validation |
| Product wildcard explosion: 5 products x multiple timesteps x multiple dates | Use Snakemake's `expand()` judiciously; ensure only configured products generate rules |
| Snakemake version compatibility | Pin minimum Snakemake version in pyproject.toml; test with current conda-forge version |
| Derived products (bias-corrected) depend on two upstream products being downloaded and processed | DAG must express multi-input dependencies (e.g., bias correction depends on both PrecipRate and QPE Pass2) |

---

## Validation Plan

```bash
# Import test
conda run -n hydro_fetch python -c "
from hydro_fetch.workflow.builder import build_workflow
print('Import OK')
"

# Generate Snakefile from test config and validate syntax
conda run -n hydro_fetch python -c "
from hydro_fetch.workflow.builder import build_workflow
snakefile = build_workflow('cases/norfolk/pipeline.yaml')
print(f'Generated: {snakefile}')
"

# Snakemake dry-run
conda run -n hydro_fetch snakemake -s <generated_snakefile> -n --quiet

# Unit tests
conda run -n hydro_fetch pytest tests/test_workflow.py -v

# Ruff
conda run -n hydro_fetch ruff check src/hydro_fetch/workflow/
conda run -n hydro_fetch ruff format --check src/hydro_fetch/workflow/
```

---

## Documentation and Tracker Updates

- Update `full_codebase_refactor.md`: mark 04A status; update tracking table for all SBATCH scripts → Snakemake rules
- Update `work_chunks/README.md`

---

## Definition of Done

- [ ] `builder.py` generates a Snakefile from `PipelineConfig`
- [ ] `download.smk` has rules for MRMS (S3), MRMS (legacy), and AORC downloads
- [ ] `process.smk` has rules for clipping, temporal resampling, bias correction, QA/QC
- [ ] `statistics.smk` has rules for annual statistics and point extraction
- [ ] `compare.smk` has rules for cross-product comparison
- [ ] All rules call hydro_fetch Python functions (no inline logic in .smk files)
- [ ] `{product}` wildcard correctly parameterizes rules
- [ ] DAG dependencies are correct (dry-run succeeds)
- [ ] Generated Snakefile is human-readable with comments
- [ ] Unit tests for builder and rule generation
- [ ] `ruff check` and `ruff format` pass
- [ ] **Move this document to `../implemented/` once all boxes above are checked**
