"""
Self-contained replacement for multidriver-swg's `_old_code_to_refactor/_inputs.py`.

WHY THIS FILE EXISTS
--------------------
The four scripts in this directory were absorbed from `multidriver-swg` (see README.md).
Each one began with `from _inputs import *`, pulling in a 203-line flat module of
constants and hard-coded paths that belongs to multidriver-swg, not to hydro-fetch.
Vendoring that module wholesale would have (a) imported ~180 symbols that have nothing
to do with data acquisition -- vine copulas, event thresholds, SST realization counts --
and (b) imported a hard-coded personal Dropbox path into a repo intended to be public.

This module therefore carries ONLY the symbols the four absorbed scripts actually
reference, traced by reading each script. Every constant below is byte-identical to
its value in the source module EXCEPT where a `SCRUBBED` or `DEFECT` comment says
otherwise. Nothing has been added, renamed, or "improved".

THIS IS NOT A DESIGN. It is a transitional shim whose only job is to make the absorbed
scripts readable and traceable in isolation. The real path-management layer is a
refactor deliverable (`01C path management`), and the project-config layer that will
supersede these constants entirely is the sister projects repo.

Source: multidriver-swg @ 1fba5826d024cf10ffb5d31ebd268b2900c48651
        _old_code_to_refactor/_inputs.py
"""

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# ROOT RESOLUTION
# ---------------------------------------------------------------------------
# DEFECT PRESERVED, NOT FIXED. The source module resolved its root as:
#
#     fldr_nrflk = str(Path(os.getcwd()).parents[1]) + "/"
#
# i.e. two directories above the CURRENT WORKING DIRECTORY. Every path below
# therefore depended on where the interpreter happened to be launched from, and
# the same script produced different paths under different invocations. This is
# recorded rather than repaired: repairing it here would hide a defect the
# refactor needs to see, and the replacement (a project config declaring its own
# roots) is an architectural decision, not a shim decision.
#
# The env var is an escape hatch so the module is importable for reading without
# reproducing the cwd dependence. Absent the env var, the original behavior stands.
_ENV_ROOT = os.environ.get("MULTIDRIVER_SWG_LEGACY_ROOT")
if _ENV_ROOT:
    fldr_nrflk = str(Path(_ENV_ROOT)) + "/"
else:
    fldr_nrflk = str(Path(os.getcwd()).parents[1]) + "/"

fldr_stormy = fldr_nrflk + "stormy/"
fldr_ssr = fldr_stormy + "stochastic_storm_rescaling/"
dir_ssr_outputs = fldr_ssr + "outputs/"
fldr_mrms_processing = fldr_nrflk + "/highres-radar-rainfall-processing/data/"
fldr_mrms_at_gages = fldr_mrms_processing + "mrms_zarr_preciprate_fullres_yearlyfiles_atgages/"

# ---------------------------------------------------------------------------
# UNIT CONSTANTS  (used by _b_gen_wshed-precip-tseries-from-mrms.py)
# ---------------------------------------------------------------------------
mm_per_inch = 25.4

# ---------------------------------------------------------------------------
# HRSD RAIN GAGES  (used by _a2_dwnld_aorc_pre_mrms.py to define the clip AOI)
# ---------------------------------------------------------------------------
# SCRUBBED. The source value was a hard-coded absolute path into a personal
# Dropbox folder on a Windows drive letter. It is replaced with an env-var
# placeholder because hydro-fetch is intended to be a public package and a
# machine-specific path may not enter a tracked file (roadmap R14).
#
# This single constant is the most instructive artifact in the whole absorption:
# it is a PROJECT DEFINITION (which gages define the area of interest) trapped
# inside toolkit code. It is precisely what the sister projects repo exists to
# hold, and `_a2` uses it to derive its AOI as a buffered bounding box around
# these gages -- the exact AOI-derivation rule the roadmap treats as an
# architectural parameter.
dir_hrsd = os.environ.get("HRSD_GAGE_DIR", "{SET_HRSD_GAGE_DIR}/")
shp_hrsd_gages = dir_hrsd + "rain_gages.shp"

# ---------------------------------------------------------------------------
# SWMM MODEL FEATURES  (used by _b_gen_wshed-precip-tseries-from-mrms.py)
# ---------------------------------------------------------------------------
fldr_swmm = fldr_stormy + "swmm/"
fldr_swmm_features = fldr_swmm + "hague/swmm_model/exported_layers/"
fldr_swmm_tseries = fldr_stormy + "swmm/hague/swmm_timeseries/"
f_shp_swmm_subs = fldr_swmm_features + "subcatchments.shp"

# ---------------------------------------------------------------------------
# NOAA WATER LEVELS  (used by _a_dwnld_and_process_water-level-data.py)
# ---------------------------------------------------------------------------
dir_noaa_water_levels = dir_ssr_outputs + "a_NOAA_water_levels/"
f_out_a_meta = dir_noaa_water_levels + 'sewells_pt_water_level_metadatap.json'
f_water_level_storm_surge = dir_noaa_water_levels + "a_water-lev_tide_surge.csv"
f_water_level_storm_surge_hrly = dir_noaa_water_levels + "a_water-lev_tide_surge_hrly.csv"
f_out_a_shp = dir_noaa_water_levels + "sewells_pt.shp"
f_out_swmm_waterlevel = fldr_swmm_tseries + "a_water_levels_ft.dat"

# Surge EVENT outputs. NOTE: these are written by the tail of `_a`, which the
# source file itself annotates "transferred to script b2" -- i.e. event selection
# is multidriver-swg's concern, not hydro-fetch's. See README.md § Partial
# absorptions. They are carried here only so the absorbed file remains readable.
f_water_level_storm_surge_event_summaries = dir_noaa_water_levels + "a1a_surge_event_summary.csv"
f_water_level_storm_surge_event_tseries = dir_noaa_water_levels + "a1b_surge_event_tseries.csv"
f_water_level_hourly_storm_surge_event_summaries = dir_noaa_water_levels + "a2a_hourly_surge_event_summary.csv"
f_water_level_hourly_storm_surge_event_tseries = dir_noaa_water_levels + "a2b_hourly_surge_event_tseries.csv"

# ---------------------------------------------------------------------------
# AORC  (used by _a2 and read by _b)
# ---------------------------------------------------------------------------
dir_aorc_rainfall = dir_ssr_outputs + "a2_aorc_data/"
f_aorc_data_pre_mrms = dir_aorc_rainfall + "aorc_pre_mrms.zarr"
f_aorc_data = dir_aorc_rainfall + "aorc.zarr"
f_aorc_data_missing_mrms_fill = dir_aorc_rainfall + "aorc_2012-2014.zarr"

# ---------------------------------------------------------------------------
# WATERSHED PRECIP TIME SERIES  (used by _b_gen_wshed-precip-tseries-from-mrms.py)
# ---------------------------------------------------------------------------
fld_out_b = dir_ssr_outputs + "b_precip_time_series_at_gages/"
f_mrms_rainfall = fld_out_b + "mrms_rainfall.csv"
f_aorc_rainfall = fld_out_b + "aorc_rainfall.csv"
f_out_b_csv_subs_w_mrms_grid = fld_out_b + "b_sub_ids_and_mrms_rain_col.csv"
f_out_swmm_rainfall = fldr_swmm_tseries + "b_mrms_rainfall_in_per_hr_{}.dat"

# ---------------------------------------------------------------------------
# NCEI STATION DATA  (used by _c_gen_ncei_hrly_and_daily_data.py)
# ---------------------------------------------------------------------------
min_record_length = 30
fldr_NCEI = fldr_stormy + "data/climate/NCEI/"
f_daily_summaries = fldr_NCEI + "2023-1-4_NCEI_daily summaries_download.csv"
f_daily_summaries_airport = fldr_NCEI + "2024-5-16_NCEI_airport_daily.csv"
f_hourlyprecip_airport = fldr_NCEI + "2024-5-16_NCEI_airport_hourly.csv"

# DEFECT RECORDED. `_c` expects a symbol named `f_hourlyprecip`. The source module
# defines `f_hourlyprecip_airport` and no bare `f_hourlyprecip`. `_c` was already
# unrunnable for a second, independent reason (see README.md § 5.1), so there is
# no observed behavior to preserve here.
#
# CORRECTED 2026-08-17 -- THIS ALIAS IS PROBABLY WRONG. It was first recorded as an
# unconfirmed inference; review narrowed it further and the direction is negative:
#   - `_c` reads `f_daily_summaries`, the MULTI-STATION daily file.
#   - `_c`'s whole purpose is `find_stations_with_min_record_length` ACROSS stations,
#     which is meaningless against a one-station airport export.
#   - `_c:105` expects a `STATION_NAME` column a single-airport export would not need.
#   - The `_airport` suffix marks the SINGLE-station members of a pair, and the
#     source module carries a distinct `f_daily_summaries_airport` for that case.
# So `f_hourlyprecip` was almost certainly a MULTI-STATION HOURLY file that
# `_inputs.py` never defined, and this alias pairs a multi-station daily with a
# single-station hourly -- a mismatched pair, not a probable match.
#
# TREAT THIS AS A PLACEHOLDER FOR A MISSING CONSTANT. Do not carry the pairing
# forward into the refactor; resolve it against the actual NCEI data holdings.
f_hourlyprecip = f_hourlyprecip_airport

fld_out_c_plts = fldr_NCEI + "qaqc_plots/"
fld_out_c_processed_data = fldr_NCEI + "processed_data/"
