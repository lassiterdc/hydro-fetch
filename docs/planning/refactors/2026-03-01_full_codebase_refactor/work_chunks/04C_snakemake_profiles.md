# Work Chunk 04C: Snakemake Profiles

**Phase**: 4C — Workflow Orchestration (Profiles)
**Created**: 2026-03-01

---

## Before Proceeding

Review the following documents before making any edits to plans or writing any code:

- [`full_codebase_refactor.md`](../full_codebase_refactor.md) — master refactor plan; update it if any decisions made here affect the overall plan.
- [`CONTRIBUTING.md`](../../../../CONTRIBUTING.md) — development philosophy.
- [`07_old_code_porting_audit.md`](07_old_code_porting_audit.md) — record any deferred old code decisions here.

**Prerequisites**: Work chunk 04A (Snakemake rule templates) complete.

---

## Task Understanding

### Requirements

1. Create a **local profile** at `src/hydro_fetch/workflow/profiles/local/config.yaml`:
   - `cores: 4` (or `all` for auto-detection)
   - No cluster submission — runs on the local machine
   - Default resources per rule type: download rules get low CPU + high network wait; process rules get high CPU + memory
   - `use-conda: false` (environment is pre-configured via the `hydro_fetch` conda env)
   - Reasonable `default-resources` for memory and runtime

2. Create a **SLURM profile** at `src/hydro_fetch/workflow/profiles/slurm/config.yaml`:
   - Uses `snakemake-executor-plugin-slurm` as the executor
   - Partition, account, and time limits are configurable (set sensible defaults, overridable via pipeline YAML)
   - Default resources per rule type: download rules request minimal cores + short walltime; process rules request multiple cores + higher memory + longer walltime
   - `jobs: 100` (or higher) to allow SLURM scheduler to manage concurrency
   - `latency-wait: 120` to handle NFS latency on HPC filesystems

3. The workflow builder (04A/04B) selects the appropriate profile based on `run_mode`:
   - `local_clip` uses the local profile
   - `hpc_conus` uses the SLURM profile (or local profile if user overrides)

4. Profile selection can be overridden via CLI flag (`--profile local` or `--profile slurm`), allowing hpc_conus mode to run locally on a large workstation.

### Key Design Decisions

- **Profiles are shipped with the package**: They live in `src/hydro_fetch/workflow/profiles/` and are referenced by the workflow builder at runtime. They are NOT user-editable in-place; users override settings via their pipeline YAML or CLI flags.
- **Resource defaults are per rule group**: Snakemake profiles support `set-resources` to assign default resources by rule name pattern. Download rules (`download_*`) get `mem_mb=2000, runtime=30`; process rules (`process_*`) get `mem_mb=16000, runtime=120, threads=4`; statistics rules get `mem_mb=8000, runtime=60`.
- **SLURM profile uses the executor plugin**: Snakemake 8+ uses `snakemake-executor-plugin-slurm` instead of the legacy `--cluster` flag. The profile sets `executor: slurm` and configures SLURM-specific options under `default-resources`.
- **Partition/account are not hardcoded**: The SLURM profile uses placeholder values that must be overridden by the user in their pipeline YAML or via environment variables. The config validator warns if SLURM-required fields are missing.

### Success Criteria

- Both profile YAML files are valid Snakemake profile configs (parseable by Snakemake CLI)
- `snakemake --profile src/hydro_fetch/workflow/profiles/local/ --dry-run` succeeds
- Workflow builder automatically selects the correct profile based on run_mode
- SLURM profile includes executor plugin configuration
- Resource allocations differ meaningfully between download and process rules

---

## Evidence from Codebase

Inspect before implementing:

1. `_old_code_to_refactor/hpc/*.sh` — SBATCH headers show resource requests: `--ntasks=1`, `--mem=16G`, `--time=04:00:00`, `--partition=standard`; these inform default resource values
2. `_old_code_to_refactor/hpc/__directories.sh` — references cluster-specific paths and modules
3. `_old_code_to_refactor/hpc/__utils.py` — chunk size parameters (`da_chnk_sz = "10000MB"`) indicating memory requirements for processing rules
4. `src/hydro_fetch/workflow/builder.py` (from 04A/04B) — must be updated to pass profile path to Snakemake invocation
5. `src/hydro_fetch/workflow/rules/download.smk` (from 04A) — rule names follow `download_{product}` pattern for resource matching
6. `src/hydro_fetch/workflow/rules/process.smk` (from 04A) — rule names follow `process_{product}_{step}` pattern
7. Snakemake 8 documentation — profile format and executor plugin configuration
8. `snakemake-executor-plugin-slurm` documentation — SLURM-specific config keys

---

## File-by-File Change Plan

### New Files

| File | Purpose |
|------|---------|
| `src/hydro_fetch/workflow/profiles/local/config.yaml` | Local execution profile: limited cores, no cluster submission, conservative memory defaults |
| `src/hydro_fetch/workflow/profiles/slurm/config.yaml` | SLURM execution profile: executor plugin, resource defaults, partition/account placeholders, NFS latency tolerance |

### Modified Files

| File | Change |
|------|--------|
| `src/hydro_fetch/workflow/builder.py` | Add `_resolve_profile_path()` method; pass `--profile` to Snakemake invocation; support `--profile` CLI override |
| `src/hydro_fetch/config/model.py` | Add optional `slurm_partition`, `slurm_account`, `slurm_time_limit` fields to config model for user overrides |
| `full_codebase_refactor.md` | Update Phase 4 status; mark 04C as in-progress/complete |

---

## Risks and Edge Cases

| Risk | Mitigation |
|------|-----------|
| Snakemake profile format changes between versions 8.x releases | Pin minimum Snakemake version; use only documented profile keys; add integration test that validates profile parsing |
| SLURM partition/account names vary across HPC systems | Do not hardcode — use placeholders (`YOUR_ACCOUNT_HERE`); config validator emits a clear error if SLURM profile is selected but partition/account are not set |
| `snakemake-executor-plugin-slurm` not installed in local environments | Detect at runtime; raise a clear error with install instructions if SLURM profile is selected but plugin is missing |
| NFS latency causes Snakemake to think output files are missing | `latency-wait: 120` in SLURM profile; can be overridden if needed |
| Local profile with `cores: all` may overwhelm machines with many cores during I/O-bound download rules | Download rules explicitly set `threads: 1` in their resource block regardless of profile; local profile can also cap with `cores: 4` as default |

---

## Validation Plan

```bash
# Verify profile YAML files are valid
conda run -n hydro_fetch python -c "
import yaml
from pathlib import Path
for profile in ['local', 'slurm']:
    p = Path('src/hydro_fetch/workflow/profiles') / profile / 'config.yaml'
    cfg = yaml.safe_load(p.read_text())
    print(f'{profile}: {list(cfg.keys())}')
    print(f'  Valid YAML: OK')
"

# Snakemake can parse the local profile (dry run with a minimal Snakefile)
conda run -n hydro_fetch snakemake --profile src/hydro_fetch/workflow/profiles/local/ --dry-run -s /dev/null 2>&1 || echo "Expected: needs Snakefile"

# Unit tests
conda run -n hydro_fetch pytest tests/test_workflow.py -v -k "profile"

# Ruff passes
conda run -n hydro_fetch ruff check src/hydro_fetch/workflow/
conda run -n hydro_fetch ruff format --check src/hydro_fetch/workflow/
```

---

## Definition of Done

- [ ] `src/hydro_fetch/workflow/profiles/local/config.yaml` created with cores, default resources, no cluster
- [ ] `src/hydro_fetch/workflow/profiles/slurm/config.yaml` created with executor plugin, resource defaults, partition/account placeholders
- [ ] Resource defaults differ by rule group (download vs process vs statistics)
- [ ] SLURM profile sets `latency-wait` for NFS
- [ ] Workflow builder resolves and passes profile path to Snakemake
- [ ] Profile selection is automatic (based on run_mode) with CLI override support
- [ ] Config model includes optional SLURM override fields (partition, account, time limit)
- [ ] Config validator warns/errors if SLURM profile selected without required fields
- [ ] Both profile YAMLs parse correctly
- [ ] Unit tests for profile resolution and override logic
- [ ] `ruff check` and `ruff format` pass
- [ ] **Move this document to `../implemented/` once all boxes above are checked**
