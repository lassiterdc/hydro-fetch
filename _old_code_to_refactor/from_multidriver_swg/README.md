# Code absorbed from `multidriver-swg`

**If you are the `multidriver-swg` session, read § 2 first.** It states what is no longer your purview, and § 3 states what still is. The rest of this document is hydro-fetch's own record.

---

## 1. Provenance

| Field | Value |
|---|---|
| Source repository | `multidriver-swg` |
| Source directory | `_old_code_to_refactor/` |
| Source commit | `1fba5826d024cf10ffb5d31ebd268b2900c48651` (`1fba582`) |
| Source branch | `main` |
| Absorbed on | 2026-08-17 |
| Absorbed by | hydro-fetch project-tier design session, on developer directive |

**The source repository was NOT modified by this absorption.** No file there was edited, deleted, staged, or committed. Its working tree was verified unchanged immediately after the copy. Removing this code from `multidriver-swg` is a separate pass the developer performs; **do not assume it has happened**, and check the tree rather than this sentence.

### Why this code moved

`multidriver-swg` generates stochastic weather from multivariate compound-event analysis. Acquiring and pre-processing the observed hydrologic data that *feeds* that analysis is a different job, and it is hydro-fetch's. The scripts here accumulated in `multidriver-swg` as scope creep.

**The inclusion predicate, so the selection is checkable rather than a matter of taste:**

> Does this script download or process hydrologic data that provides INPUT to `multidriver-swg`?

If yes, it is hydro-fetch's. If it *consumes* such data to do stochastic weather generation, it stays in `multidriver-swg`.

---

## 2. What is NO LONGER `multidriver-swg`'s purview

Four files. Three moved whole; one moved in part.

| Source file | Lines | What it does | Absorption |
|---|---|---|---|
| `_a2_dwnld_aorc_pre_mrms.py` | 94 | Opens the `noaa-nws-aorc-v1-1-1km` S3 zarr store for 1979–present, clips to an AOI derived as a buffered bounding box around the HRSD rain gages, writes a local zarr | **FULL** |
| `_c_gen_ncei_hrly_and_daily_data.py` | 83 | Reads NCEI hourly and daily station summaries, filters to stations with a minimum record length, generates QAQC plots of inter-observation gaps and annual totals | **FULL** |
| `_b_gen_wshed-precip-tseries-from-mrms.py` | 333 | Loads MRMS-at-gages and AORC zarr stores, hexbin-QAQCs bias-corrected vs uncorrected daily totals, matches each SWMM subcatchment to its nearest grid cell, builds per-subcatchment rainfall time series, **and exports SWMM `.dat` files** | **FULL — including the SWMM export.** See § 3.1 |
| `_a_dwnld_and_process_water-level-data.py` | 487 | Downloads NOAA CO-OPS water level + tide predictions for Sewells Point (station `8638610`) from 1927, computes storm surge, exports csv/JSON/shapefile/SWMM `.dat`, compares hourly vs 6-minute distributions, **then selects surge events** | **PARTIAL.** See § 3.2 |

### 2.1 Scope this activates in hydro-fetch

Absorbing `_a_dwnld_and_process_water-level-data.py` **activates the water-level half of hydro-fetch's declared scope.** hydro-fetch's specialist identity has always named water level; until this absorption, nothing in the repo did it. Every prior file here is precipitation. This is not a scope expansion beyond what was declared — it is the first code to occupy declared-but-empty scope, and the refactor's system partition has to account for it.

---

## 3. Partial absorptions — read these carefully

The developer's instruction was that partial absorptions be made **super explicit**. Two files have boundaries.

### 3.1 `_b_gen_wshed-precip-tseries-from-mrms.py` — the SWMM export is OURS, and that is a decision

The final section (`#%% creating .dat files for swmmm` onward, source lines ~295–331) writes SWMM-format `.dat` rainfall files. A reasonable person could call that the *consumer's* job: hydro-fetch produces rainfall, and formatting it for one particular downstream model is the downstream model's business.

**It was ruled hydro-fetch's on 2026-08-17.** The developer's words: *"i DO think that any formatting and/or pre-processing of rainfall data like watershed wide averages is good. Let's scope in formatting for SWMM. This can be refactored and moved later if needed, but let's do it here."*

**Record this as a decision with stated reversibility, not as an open question.** The distinction matters to you: an undecided seam would mean you should keep thinking about it. A decided-and-reversible one means you should not — it is settled unless and until it is revisited, and the revisiting is hydro-fetch's to initiate.

Nothing in this file is left behind.

### 3.2 `_a_dwnld_and_process_water-level-data.py` — the event-selection tail is STILL YOURS

This file has three parts. **The third is not hydro-fetch's**, and the source file says so itself.

| Source lines | Section | Whose |
|---|---|---|
| ~1–251 | **Acquisition.** Download CO-OPS `water_level`, `predictions`, `hourly_height`, `high_low`; concatenate; compute `surge_ft = waterlevel_ft - tide_ft`; convert EST→UTC; export csv + metadata JSON + gage shapefile + SWMM `.dat` | **hydro-fetch** |
| ~252–362 | **Characterization.** Cramér–von Mises and rank-sum comparison of hourly vs 6-minute surge distributions, walking forward a year at a time until the two are not distinguishable | **hydro-fetch** — this is QAQC of the product's own fitness, which a data producer owes its consumers |
| ~364–end | **Event selection.** `surge_event_selection()`, threshold search targeting ~5 events/year, event summary + time-series export, hourly-vs-6-min event cross-check | **`multidriver-swg` — NOT absorbed as scope.** The source file's own section header reads `#%% transferred to script b2` |

**The code is physically present in the copied file but is NOT claimed.** It was retained unmodified so the file stays readable end to end and so the boundary is visible in context rather than asserted in prose. If `_b2_event_selection.py` already carries this logic — and its author's own comment says it was transferred there — then **this tail is dead weight here and live code there.** Confirm against `_b2` rather than trusting either comment.

The four `f_water_level_*_event_*` path constants that this tail writes are carried in `_paths.py` for the same reason, and flagged there identically.

---

## 4. What made this "self-contained", and what it cost

Every absorbed script began with `from _inputs import *`, and `_a2` also with `from _utils import *`. Those two modules are `multidriver-swg`'s shared surface and are **not** absorbed: `_inputs.py` is 203 lines and `_utils.py` is 2,393.

A bare copy would have produced four files that cannot resolve their own constants. A wholesale vendor would have imported ~180 irrelevant symbols — vine-copula parameters, SST realization counts, event thresholds — plus a hard-coded personal Dropbox path, into a repo intended to be public.

**What was done instead:** each script's *actual* symbol usage was traced by reading the script, and only those symbols were vendored into two new local modules.

| New file | Replaces | Contents |
|---|---|---|
| `_paths.py` | `_inputs.py` (203 lines) | ~40 constants, only those referenced. One value scrubbed, two defects annotated |
| `_local_utils.py` | `_utils.py` (2,393 lines) | **One function**, `define_zarr_compression`, reproduced byte-for-byte |

**One symbol from 2,393 lines.** The star-import concealed that ratio completely — which is itself the finding: `from _utils import *` in a 94-line download script imported an entire modelling library to obtain six lines of zarr encoding config.

### 4.1 Edits made to the four scripts — the complete list

Nothing else was touched. Every other line is byte-identical to source.

| File | Edits |
|---|---|
| `_a2_dwnld_aorc_pre_mrms.py` | Provenance header comment; `_inputs` → `_paths`; `_utils` → `_local_utils` |
| `_b_gen_wshed-precip-tseries-from-mrms.py` | Provenance header comment; `_inputs` → `_paths` |
| `_a_dwnld_and_process_water-level-data.py` | Provenance header comment; `_inputs` → `_paths` |
| `_c_gen_ncei_hrly_and_daily_data.py` | Provenance header comment; broken `def_inputs_for_c` import replaced with five direct imports (see § 5.1) |

### 4.2 Scrubbed value

`_inputs.py` line 201 defined a rain-gage directory as an absolute path into a personal Dropbox folder on a Windows drive letter. It is replaced in `_paths.py` with an environment-variable placeholder, because a machine-specific path may not enter a tracked file in a repo intended to be public.

**This constant is the most instructive artifact in the absorption.** `_a2` uses it to derive its clip AOI as a buffered bounding box around those gages. That is a **project definition** — *which location are we producing data for* — hard-coded inside toolkit code. It is precisely what a hydro-fetch "project" is meant to hold, and it demonstrates the failure mode by example rather than by argument.

---

## 5. Defects found in the source

Both were found by reading, not by running. Neither is a criticism of the source — this is undocumented research code that did its job — but a refactor that assumes these scripts *work today* will be wrong.

### 5.1 `_c_gen_ncei_hrly_and_daily_data.py` could never have run as committed

Line 2 reads `from _inputs import def_inputs_for_c`. **`_inputs.py` defines no functions at all** — verified with `grep "^def \|^class " _inputs.py`, which returns no matches. The module is a flat list of constants. This file raised `ImportError` on its second line.

The same fossil appears in `_b_gen_wshed-...` as a commented-out `def_inputs_for_b()` call and in `_a_dwnld_...` as a commented-out `def_inputs_for_a()` call, so `_inputs.py` evidently once exposed per-script accessor functions and was flattened without updating `_c`.

**Handling:** repaired, because there was no working behavior to preserve and "self-contained" would otherwise be meaningless for this file. A second-order problem surfaced in the process: the removed call unpacked a name `f_hourlyprecip`, which **also does not exist** in the source module. `_paths.py` aliases it to `f_hourlyprecip_airport` — the only hourly-precipitation candidate present — and flags that as an **inference to confirm against the actual data**, not a fact.

### 5.2 `_a_dwnld_and_process_water-level-data.py` raises `NameError` partway through

It defines `surge_event_selection()` (source line ~369) and then calls **`wlevel_event_selection(...)`** at source lines ~442, ~452, and ~453. No such name is defined or imported anywhere in the file.

**Handling:** preserved as-is, deliberately. Repairing it would change behavior in a file nobody has successfully run, and would erase evidence the refactor needs. It also falls in the § 3.2 tail that is not hydro-fetch's scope anyway — so repairing it here would mean editing code we are explicitly not claiming.

### 5.3 The root path depends on the current working directory

`_inputs.py` resolved its root as `str(Path(os.getcwd()).parents[1])` — two directories above wherever the interpreter was launched. **Every path in the module inherited that**, so the same script wrote to different locations under different invocations, silently.

**Handling:** preserved, with an environment-variable escape hatch so the module can be imported for reading without reproducing the dependence. Absent the variable, the original behavior stands. Repairing it properly is an architectural decision (a project config declaring its own roots), not a shim decision.

---

## 6. What this directory is, and what it is not

**It is not a library.** It is legacy reference material staged for refactor, exactly like the rest of `_old_code_to_refactor/`. The two shim modules exist so the four scripts can be *read and traced in isolation*; they are not a path-management design and should not be extended into one.

**Overlap with existing hydro-fetch legacy code — check before refactoring.** This repo already carries `_old_code_to_refactor/hpc/d_download_AORC.sh`, a SLURM/shell AORC downloader. `_a2_dwnld_aorc_pre_mrms.py` is a *second* AORC acquisition path, Python and S3-zarr-based. **These two have not been reconciled.** Whether they are redundant, complementary, or targeting different AORC products is an open question for the refactor's AORC work chunk, and nobody should assume the answer.

Known related work chunks in the refactor plan: `03D aorc download`, `02E point extraction`, `01C path management`, `01E gis io`.

---

## 7. For the `multidriver-swg` session — the short version

- **Gone from your purview:** AORC S3 download + clip; NOAA CO-OPS water-level/tide/surge **acquisition and characterization**; NCEI station-data loading and QAQC; MRMS→subcatchment watershed rainfall averaging; **and SWMM rainfall formatting** (ruled hydro-fetch's, reversibly).
- **Still yours:** everything in `_a_dwnld_and_process_water-level-data.py` from `#%% transferred to script b2` onward — surge event selection, thresholds, event summaries and time series. The physical lines exist in our copy for readability; the *scope* did not transfer. Check whether `_b2_event_selection.py` already supersedes them.
- **Still yours, untouched:** `_b2`–`_b7`, `_d_build_water_level_generator.py`, `__ref_ams_functions.py`, `_inputs.py`, `_utils.py`.
- **We did not modify your repo.** Verify that yourself rather than taking this line for it.
- **Two of the four scripts are broken as committed in your tree** (§ 5.1, § 5.2). If your refactor plan has chunks that assume they run, those chunks rest on a false premise — and that is true on your side whether or not the code moves.
