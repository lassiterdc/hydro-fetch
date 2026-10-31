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
| Absorbed by | hydro-fetch's project-level design work, on developer directive |

**The source repository was NOT modified by this absorption.** No file there was edited, deleted, staged, or committed. Its working tree was verified unchanged immediately after the copy. Removing this code from `multidriver-swg` is a separate pass the developer performs; **do not assume it has happened**, and check the tree rather than this sentence.

### Why this code moved

`multidriver-swg` generates stochastic weather from multivariate compound-event analysis. Acquiring and pre-processing the observed hydrologic data that *feeds* that analysis is a different job, and it is hydro-fetch's. The scripts here accumulated in `multidriver-swg` as scope creep.

**The inclusion predicate, so the selection is checkable rather than a matter of taste:**

> Does this script download or process hydrologic data that provides INPUT to `multidriver-swg`?

If yes, it is hydro-fetch's. If it *consumes* such data to do stochastic weather generation, it stays in `multidriver-swg`.

---

## 2. What is NO LONGER `multidriver-swg`'s purview

Four files. Three moved whole; one moved in part.

The unit-by-unit record of what `multidriver-swg` handed over in these four files is § 8.

| Source file | Lines | What it does | Absorption |
|---|---|---|---|
| `_a2_dwnld_aorc_pre_mrms.py` | 94 | Opens the `noaa-nws-aorc-v1-1-1km` S3 zarr store for 1979–present, clips to an AOI derived as a buffered bounding box around the HRSD rain gages, writes a local zarr | **FULL** |
| `_c_gen_ncei_hrly_and_daily_data.py` | 83 | Reads NCEI hourly and daily station summaries, filters to stations with a minimum record length, generates QAQC plots of inter-observation gaps and annual totals | **FULL** |
| `_b_gen_wshed-precip-tseries-from-mrms.py` | 333 | Loads MRMS-at-gages and AORC zarr stores, hexbin-QAQCs bias-corrected vs uncorrected daily totals, matches each SWMM subcatchment to its nearest grid cell, builds per-subcatchment rainfall time series, **and exports SWMM `.dat` files** | **FULL — including the SWMM export.** See § 3.1 |
| `_a_dwnld_and_process_water-level-data.py` | 487 | Downloads NOAA CO-OPS water level + tide predictions for Sewells Point (station `8638610`) from 1927, computes storm surge, exports csv/JSON/shapefile/SWMM `.dat`, compares hourly vs 6-minute distributions, **then selects surge events** | **PARTIAL.** See § 3.2 |

### 2.1 Scope this activates in hydro-fetch

Absorbing `_a_dwnld_and_process_water-level-data.py` **activates the water-level half of hydro-fetch's declared scope.** That scope has always included water level; until this absorption, nothing in the repo did it. Every prior file here is precipitation. This is not a scope expansion beyond what was declared — it is the first code to occupy declared-but-empty scope, and the refactor's system partition has to account for it.

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
| ~1–283 | **Acquisition.** Download CO-OPS `water_level`, `predictions`, `hourly_height`, `high_low`; concatenate; compute `surge_ft = waterlevel_ft - tide_ft`; convert EST→UTC; export csv + metadata JSON + gage shapefile + SWMM `.dat` | **hydro-fetch** |
| ~283–362 | **Characterization.** Cramér–von Mises and rank-sum comparison of hourly vs 6-minute surge distributions, walking forward a year at a time until the two are not distinguishable | **hydro-fetch** — this is QAQC of the product's own fitness, which a data producer owes its consumers |
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

**Handling:** repaired, because there was no working behavior to preserve and "self-contained" would otherwise be meaningless for this file. A second-order problem surfaced in the process: the removed call unpacked a name `f_hourlyprecip`, which **also does not exist** in the source module.

**CORRECTED 2026-08-17 — the alias in `_paths.py` is probably WRONG, not merely unconfirmed.** Review on the `multidriver-swg` side narrowed it: `_c` reads `f_daily_summaries` (the **multi-station** daily file) and its whole purpose is `find_stations_with_min_record_length` **across stations**, which is meaningless against a one-station airport export; `_c:105` further expects a `STATION_NAME` column a single-airport export would not need. The `_airport` suffix marks the single-station members of a pair. So `f_hourlyprecip` was almost certainly a **multi-station hourly** file that `_inputs.py` never defined, and aliasing it to `f_hourlyprecip_airport` pairs a multi-station daily with a single-station hourly. **Treat the alias as a placeholder for a missing constant, not as a probable match.**

### 5.2 `_a_dwnld_and_process_water-level-data.py` raises `NameError` partway through

It defines `surge_event_selection()` (source line ~369) and then calls **`wlevel_event_selection(...)`** at source lines ~442, ~452, and ~453. No such name is defined or imported anywhere in the file.

**Handling:** preserved as-is, deliberately. Repairing it would change behavior in a file nobody has successfully run, and would erase evidence the refactor needs. It also falls in the § 3.2 tail that is not hydro-fetch's scope anyway — so repairing it here would mean editing code we are explicitly not claiming.

### 5.3 The root path depends on the current working directory

`_inputs.py` resolved its root as `str(Path(os.getcwd()).parents[1])` — two directories above wherever the interpreter was launched. **Every path in the module inherited that**, so the same script wrote to different locations under different invocations, silently.

**Handling:** preserved, with an environment-variable escape hatch so the module can be imported for reading without reproducing the dependence. Absent the variable, the original behavior stands. Repairing it properly is an architectural decision (a project config declaring its own roots), not a shim decision.

---

### 5.4 A lat/lon transposition writes the gage shapefile to the wrong hemisphere

`_a_dwnld_and_process_water-level-data.py:257` (absorbed copy):

```python
gdf = gp.GeoDataFrame(df, geometry=gp.points_from_xy(df.lat, df.lng))
```

`points_from_xy(x, y)` takes **x first**, and x must be longitude. Passing `lat` as `x` writes the Sewells Point gage shapefile with transposed coordinates — the gage lands in the Indian Ocean. No retained `multidriver-swg` script reads `f_out_a_shp`, which is why this has never bitten anyone, but it sits in the acquisition section hydro-fetch has claimed and it will bite the first person who opens that shapefile.

**Found in review on the `multidriver-swg` side, not by the absorbing agent.** It is recorded here because the original list of three was asserted as complete and was not.

### 5.5 The SWMM export writes `.dat` files for columns that are not gages

`_b_gen_wshed-precip-tseries-from-mrms.py:317`:

```python
gage_ids = df_mrms_tseries.columns
```

That column set includes `rain_mean` **and** `bias_corrected`. The loop then writes a `.dat` per column, emitting a spurious `b_mrms_rainfall_in_per_hr_rain_mean.dat` (the watershed mean masquerading as a gage) and a `b_mrms_rainfall_in_per_hr_bias_corrected.dat` (a boolean divided by 25.4, filtered to `> 0`, written as inches of rain). **Since the SWMM formatting was scoped into hydro-fetch, this is now hydro-fetch's defect.**

Root cause, and it is architectural rather than local: **the code has no first-class notion of "which columns are grid cells."** `multidriver-swg`'s `_utils.py:117` independently guesses the same thing by negation (`[col for col in ... if 'mm_per_hr' not in col]`), which means any column added to `mrms_rainfall.csv` is silently averaged into the rainfall. Two repos, two guesses, both wrong in different ways. The grid-cell column set is a real entity that currently exists only as an implicit convention re-derived at three call sites.

### 5.6 A fourth broken script — in `multidriver-swg`'s tree, not absorbed

`_d_build_water_level_generator.py:12` carries the `def_inputs_for_*` fossil **live** and uncommented: `from _inputs import def_inputs_for_d`. Since `_inputs.py` defines zero functions, `_d` raises `ImportError` on line 12 and could never have run as committed. It also unpacks `f_realizations`, `sst_tstep_min`, and `dir_time_series`, none of which exist as constants (only the near-misses `f_realizations_hrly` and `sst_hrly_tstep_min` do).

Not absorbed and not hydro-fetch's to fix — recorded because §5.1's framing implied the fossil had been traced to completion, and it had not.

## 5A. The NCEI absorption is INCOMPLETE — correction to §2

**Recorded 2026-08-17 after review.** Applying the inclusion predicate to what actually happens with NCEI data gives a different answer than the original selection did.

`_c_gen_ncei_hrly_and_daily_data.py` **persists nothing.** Its two output-path imports (`fld_out_c_plts`, `fld_out_c_processed_data`) are never used; the file ends having produced two in-memory DataFrames and a set of unsaved figures. It is an interactive exploration script and produces **zero artifacts `multidriver-swg` consumes.**

Meanwhile the NCEI processing that **does** feed the pipeline is `_utils.process_ncei_data` (`multidriver-swg/_old_code_to_refactor/_utils.py:1991`), called at `_b2:70` — inches→mm, per-timestep→per-hour, EST→UTC, resample-to-target-step, `years_to_exclude` filter. Zero stochastic content. Under the stated predicate it is hydro-fetch's, and it was **not** absorbed. The `999.99` missing-sentinel handling at `_b2:34` belongs with it.

**Disposition:** `process_ncei_data` and the sentinel handling are claimed as hydro-fetch's scope and are pending extraction; `_c` **stays** — NCEI station QAQC is a hydro-fetch capability even though this particular instance persists nothing. This is an ADDITION to the absorbed set, not a swap.

**Separately: there is no NCEI acquisition code in either repo.** `f_hourlyprecip_airport` names a hand-dated manual download (`2024-5-16_NCEI_airport_hourly.csv`); nothing fetches it. If hydro-fetch's scope is "acquire the hydrologic inputs," this is a hole in the acquisition layer rather than merely an unclaimed file.

## 6. What this directory is, and what it is not

**It is not a library.** It is legacy reference material staged for refactor, exactly like the rest of `_old_code_to_refactor/`. The two shim modules exist so the four scripts can be *read and traced in isolation*; they are not a path-management design and should not be extended into one.

**Overlap with existing hydro-fetch legacy code — check before refactoring.** This repo already carries `_old_code_to_refactor/hpc/d_download_AORC.sh`, a SLURM/shell AORC downloader. `_a2_dwnld_aorc_pre_mrms.py` is a *second* AORC acquisition path, Python and S3-zarr-based. **These two have not been reconciled.** Whether they are redundant, complementary, or targeting different AORC products is an open question for the refactor's AORC download work, and nobody should assume the answer.

Related refactor work: AORC download, point extraction, path management, and GIS input/output.

---

## 7. For the `multidriver-swg` session — the short version

- **Gone from your purview:** AORC S3 download + clip; NOAA CO-OPS water-level/tide/surge **acquisition and characterization**; NCEI station-data loading and QAQC; MRMS→subcatchment watershed rainfall averaging; **and SWMM rainfall formatting** (ruled hydro-fetch's, reversibly).
- **Still yours:** everything in `_a_dwnld_and_process_water-level-data.py` from `#%% transferred to script b2` onward — surge event selection, thresholds, event summaries and time series. The physical lines exist in our copy for readability; the *scope* did not transfer. Check whether `_b2_event_selection.py` already supersedes them.
- **Still yours, untouched:** `_b2`–`_b7`, `_d_build_water_level_generator.py`, `__ref_ams_functions.py`, `_inputs.py`, `_utils.py`.
- **We did not modify your repo.** Verify that yourself rather than taking this line for it.
- **Two of the four absorbed scripts are broken as committed in your tree** (§ 5.1, § 5.2), and a fifth script you retained — `_d_build_water_level_generator.py` — carries the same `def_inputs_for_*` fossil live (§ 5.6). If your refactoring work assumes they run, that work rests on a false premise — and that is true on your side whether or not the code moves.

---

## 8. Unit-by-unit hand-off record, as received from `multidriver-swg`

This section is hydro-fetch's record of every unit of the four files in § 2 that `multidriver-swg` handed to it. `multidriver-swg`'s disposition ledger (`tests/correspondence/ledger/ceded_files.toml` in that repository) records each of the four files as a scope-out to hydro-fetch and points at this section.

| Field | Value |
|---|---|
| Ruling | The developer's ruling that these four files move to hydro-fetch, three whole and one in part as § 2 states (§ 1, "Absorbed on") |
| Ruling date | 2026-08-17 |
| Source repository | `multidriver-swg`, https://github.com/lassiterdc/multidriver-swg |
| Revision the line ranges refer to | `4f3b50404acc09957946e6cb4d560bce0df76ee6`. The four files are byte-identical there and at the source commit in § 1 (`1fba582`). |
| Unit rule | `multidriver-swg`'s extent rule, `tests/correspondence/extent.py` at that revision: every line of a file belongs to exactly one unit, and a unit's key is `{file}:{first}-{last}`, with further `,{first}-{last}` ranges where a unit's lines are not contiguous |
| Surface of this record | this file, `_old_code_to_refactor/from_multidriver_swg/README.md` in the hydro-fetch repository, § 8 |
| Count | 50 units across the four files, the count `multidriver-swg`'s ledger prints, plus one preamble extent in `_a_dwnld_and_process_water-level-data.py` (its module docstring, lines 1-9), which that count leaves out. All 51 are listed, so every line of the four files is accounted for. |

The line ranges are `multidriver-swg`'s. The copies in this directory begin with a provenance header (§ 4.1), so their own line numbers are larger. The `Lines:` totals below count a last line that has no newline, so for `_a2_dwnld_aorc_pre_mrms.py` and `_c_gen_ncei_hrly_and_daily_data.py` they are one more than the `wc -l` figures in § 2.

### 8.1 `_a2_dwnld_aorc_pre_mrms.py`

Units: 11. Lines: 95.

| Unit key | Line ranges | Name |
|---|---|---|
| `_a2_dwnld_aorc_pre_mrms.py:1-22` | 1-22 | none |
| `_a2_dwnld_aorc_pre_mrms.py:23-29` | 23-29 | none |
| `_a2_dwnld_aorc_pre_mrms.py:30-40` | 30-40 | none |
| `_a2_dwnld_aorc_pre_mrms.py:41-61` | 41-61 | `load_aorc_rain_data` |
| `_a2_dwnld_aorc_pre_mrms.py:62-64` | 62-64 | none |
| `_a2_dwnld_aorc_pre_mrms.py:65-69` | 65-69 | none |
| `_a2_dwnld_aorc_pre_mrms.py:70-72` | 70-72 | none |
| `_a2_dwnld_aorc_pre_mrms.py:73-77` | 73-77 | none |
| `_a2_dwnld_aorc_pre_mrms.py:78-82` | 78-82 | none |
| `_a2_dwnld_aorc_pre_mrms.py:83-92` | 83-92 | none |
| `_a2_dwnld_aorc_pre_mrms.py:93-95` | 93-95 | none |

### 8.2 `_a_dwnld_and_process_water-level-data.py`

Units: 15, plus 1 preamble extent. Lines: 487.

| Unit key | Line ranges | Name |
|---|---|---|
| `_a_dwnld_and_process_water-level-data.py:1-9` | 1-9 | none (preamble above the first cell marker) |
| `_a_dwnld_and_process_water-level-data.py:10-52` | 10-52 | none |
| `_a_dwnld_and_process_water-level-data.py:53-100` | 53-100 | `dwnld_data` |
| `_a_dwnld_and_process_water-level-data.py:101-184` | 101-184 | none |
| `_a_dwnld_and_process_water-level-data.py:185-250,260-282` | 185-250,260-282 | none |
| `_a_dwnld_and_process_water-level-data.py:251-259` | 251-259 | `sum_square_diffs` |
| `_a_dwnld_and_process_water-level-data.py:283-285` | 283-285 | none |
| `_a_dwnld_and_process_water-level-data.py:286-293` | 286-293 | `perform_statistical_test` |
| `_a_dwnld_and_process_water-level-data.py:294-323` | 294-323 | `compare_stats` |
| `_a_dwnld_and_process_water-level-data.py:324-333` | 324-333 | `succeeded_stat_test` |
| `_a_dwnld_and_process_water-level-data.py:334-363` | 334-363 | none |
| `_a_dwnld_and_process_water-level-data.py:364-367` | 364-367 | none |
| `_a_dwnld_and_process_water-level-data.py:368-432` | 368-432 | `surge_event_selection` |
| `_a_dwnld_and_process_water-level-data.py:433-448` | 433-448 | none |
| `_a_dwnld_and_process_water-level-data.py:449-466` | 449-466 | none |
| `_a_dwnld_and_process_water-level-data.py:467-487` | 467-487 | none |

### 8.3 `_b_gen_wshed-precip-tseries-from-mrms.py`

Units: 18. Lines: 333.

| Unit key | Line ranges | Name |
|---|---|---|
| `_b_gen_wshed-precip-tseries-from-mrms.py:1-13` | 1-13 | none |
| `_b_gen_wshed-precip-tseries-from-mrms.py:14-32` | 14-32 | `comp_dist_to_1to1_line` |
| `_b_gen_wshed-precip-tseries-from-mrms.py:33-36` | 33-36 | `compute_frac_within_tolerance_of_1to1_line` |
| `_b_gen_wshed-precip-tseries-from-mrms.py:37-104` | 37-104 | `plt_hexbin` |
| `_b_gen_wshed-precip-tseries-from-mrms.py:105-124,131-136` | 105-124,131-136 | none |
| `_b_gen_wshed-precip-tseries-from-mrms.py:125-130` | 125-130 | `transform_to_4326` |
| `_b_gen_wshed-precip-tseries-from-mrms.py:137-162` | 137-162 | none |
| `_b_gen_wshed-precip-tseries-from-mrms.py:163-166` | 163-166 | none |
| `_b_gen_wshed-precip-tseries-from-mrms.py:167-194` | 167-194 | `return_gridcells_nearest_subcatchments` |
| `_b_gen_wshed-precip-tseries-from-mrms.py:195-232` | 195-232 | none |
| `_b_gen_wshed-precip-tseries-from-mrms.py:233-238` | 233-238 | none |
| `_b_gen_wshed-precip-tseries-from-mrms.py:239-245` | 239-245 | none |
| `_b_gen_wshed-precip-tseries-from-mrms.py:246-247` | 246-247 | none |
| `_b_gen_wshed-precip-tseries-from-mrms.py:248-281` | 248-281 | `create_time_series` |
| `_b_gen_wshed-precip-tseries-from-mrms.py:282-286` | 282-286 | none |
| `_b_gen_wshed-precip-tseries-from-mrms.py:287-294` | 287-294 | none |
| `_b_gen_wshed-precip-tseries-from-mrms.py:295-322` | 295-322 | none |
| `_b_gen_wshed-precip-tseries-from-mrms.py:323-333` | 323-333 | none |

### 8.4 `_c_gen_ncei_hrly_and_daily_data.py`

Units: 6. Lines: 84.

| Unit key | Line ranges | Name |
|---|---|---|
| `_c_gen_ncei_hrly_and_daily_data.py:1-8` | 1-8 | none |
| `_c_gen_ncei_hrly_and_daily_data.py:9-12` | 9-12 | none |
| `_c_gen_ncei_hrly_and_daily_data.py:13-21` | 13-21 | `find_stations_with_min_record_length` |
| `_c_gen_ncei_hrly_and_daily_data.py:22-26` | 22-26 | `filter_stations_with_min_record` |
| `_c_gen_ncei_hrly_and_daily_data.py:27-77` | 27-77 | `gen_qaqc_plots` |
| `_c_gen_ncei_hrly_and_daily_data.py:78-84` | 78-84 | none |

### 8.5 The last five extents of `_a_dwnld_and_process_water-level-data.py`

Lines 364-487, the five extents from `364-367` to `467-487` in § 8.2, are the event-selection tail that § 3.2 records as not absorbed as scope. They are listed because every line of the file was handed over as code, and this directory carries them. Their capability was not handed over: `multidriver-swg` keeps surge event selection in its own retained code, as `surge_event_selection` in `_old_code_to_refactor/_utils.py`, lines 1423-1539 at the revision above, which its `_b2_event_selection.py` calls at lines 432, 441 and 558. The source file calls `wlevel_event_selection` at lines 442, 452 and 453 (§ 5.2); in the copy in this directory the calls are at lines 464, 474 and 475. The name is defined nowhere. This is the confirmation against `_b2` that § 3.2 asks for.
