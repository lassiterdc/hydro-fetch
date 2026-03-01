#%% Import libraries
import shutil
import pandas as pd
import sys
from glob import glob
import xarray as xr
import time
from __utils import *
import os

start_time = time.time()

use_previous_scratcj_outputs_if_available = False

final_output_type = "zarr" # must be "nc" or "zarr" and match what is in script da2

if final_output_type == "zarr":
    engine = "zarr"
else:
    engine = "h5netcdf"

#%% work
# start_year = 2001
# year = 2016
# fldr_out = "/project/quinnlab/dcl3nd/norfolk/highres-radar-rainfall-processing/data/mrms_zarr_preciprate_fullres_dailyfiles_constant_tstep/"
# fldr_csvs = "/scratch/dcl3nd/highres-radar-rainfall-processing/_scratch/csv/"
# fldr_bias_crxn_ref = "/project/quinnlab/dcl3nd/norfolk/highres-radar-rainfall-processing/data/raw_data/raw_data/aorc/"
# use_previous_qaqc_netcdf = True
#%% end work
start_year = int(sys.argv[1])
year = int(sys.argv[2])
fldr_out = str(sys.argv[3]) # ${assar_dirs[out_fullres_dailyfiles_consolidated]} # "/scratch/dcl3nd/highres-radar-rainfall-processing/out_fullres_dailyfiles_consolidated/"
fldr_csvs = str(sys.argv[4])
fldr_bias_crxn_ref = str(sys.argv[5])

# create qaqc csv's just once
if year == start_year:
    fl_da2_csv = fldr_csvs +"da2_resampling_{}.csv".format("*") # must match pattern in script da2
    # qaqc of resampling
    lst_f_csvs = glob(fl_da2_csv)
    lst_dfs = []
    for f in lst_f_csvs:
        lst_dfs.append(pd.read_csv(f, index_col = 0))
    df = pd.concat(lst_dfs, ignore_index = True)
    df.to_csv(fldr_out+"_da3_resampling_performance.csv")
    # qaqc of dataset as a whole
    fl_csv_qaqc = fldr_csvs +"qaqc_of_daily_fullres_data_{}.csv".format("*") # must match pattern in script da2
    lst_f_csvs = glob(fl_csv_qaqc)
    lst_dfs = []
    for f in lst_f_csvs:
        lst_dfs.append(pd.read_csv(f, index_col = 0))
    df = pd.concat(lst_dfs, ignore_index = False)
    df.to_csv(fldr_out+"_da3_qaqc_fullres_dataset.csv")

df = pd.read_csv(fldr_out+"_da3_resampling_performance.csv")
try:
    df_successes = df[df.problem_exporting_netcdf == False]
except:
    pass
try:
    df_successes = df[df.problem_exporting_zarr == False]
except:
    pass

# Function to check for duplicate values along a dimension
def check_duplicates(ds, dims=['latitude', "longitude"]):
    import warnings
    try:
        result = "no_duplicates"
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            for dim in dims:
                if ds[dim].to_pandas().duplicated().any():
                    # print(f"Duplicate values found in dimension '{dim}' for file: {file_path}")
                    result = "duplicates"
                ds.close()  # Close the dataset to release resources
    except Exception as e:
        # print(f"Error while processing file {file_path}: {e}")
        result = f"failed due to error {e}"
    return result

def return_monthly_files_for_year(year):
    lst_files = glob(fldr_scratch_zarr + "da3_qaqc_{}*.zarr".format(year))
    lst_monthly_outputs = []
    for f in lst_files:
        if "-" in f.split(str(year))[-1]:
            continue
        lst_monthly_outputs.append(f)
    return lst_monthly_outputs

def return_daily_files_for_yearmonth(year, month):
    lst_files = glob(fldr_scratch_zarr + "da3_qaqc_{}-{}*.zarr".format(year, month))
    lst_daily_outputs = []
    for f in lst_files:
        if "-" in f.split(str(year))[-1]:
            lst_daily_outputs.append(f)
    return lst_daily_outputs


def return_year_and_month_from_monthly_file(f):
    yearmonth = f.split("/")[-1].split("_")[-1].split(".")[0]
    year = yearmonth[0:4]
    month = yearmonth[4:]
    return year, month

# consolidating qaqc statistics into monthly netcdf files
df_dates = pd.to_datetime(df_successes.date,format="%Y%m%d").sort_values().astype(str).str.split("-", expand = True)
df_dates.columns = ["year", "month", "day"]
df_yearmonths = df_dates.loc[:, ["year", "month"]].drop_duplicates()
# subset target years
df_yearmonths = df_yearmonths[df_yearmonths.year.astype(int) == int(year)].reset_index(drop = True)
print("Creating monthly outputs of qaqc data.....")
n_days_per_month_to_test = None
bm_time0 = time.time()

lst_monthly_outputs = []
if use_previous_scratcj_outputs_if_available:
    lst_monthly_outputs = return_monthly_files_for_year(year)
    lst_monthly_outputs.sort()
# n_days_per_month_to_test = 3
for id, row in df_yearmonths.iterrows():
    bm_time = time.time()
    year = row.year
    month = row.month
    fl_scratch_out_qaqc = fldr_scratch_zarr + "da3_qaqc_{}{}.zarr".format(year, month)
    if fl_scratch_out_qaqc in lst_monthly_outputs:
        continue
    lst_f_outputs = glob(fldr_out + "{}{}*.{}".format(year, month, final_output_type))
    lst_f_outputs.sort()
    # lst_ds_qaqc = []
    lst_fs_date = []
    if use_previous_scratcj_outputs_if_available:
        lst_fs_date = return_daily_files_for_yearmonth(year, month)
    for f_out in lst_f_outputs:
        ds_day = xr.open_dataset(f_out, engine = engine).chunk(dict(time = 1))
        lst_das = []
        date = ds_day.time.values[0]
        str_date = str(pd.to_datetime(date).date())
        fl_scratch_out_qaqc_day = fldr_scratch_zarr + "da3_qaqc_{}.zarr".format(str_date)
        if fl_scratch_out_qaqc_day in lst_fs_date:
            continue
        # break
        if ds_day["bias_corrected"].values[0] == False: # only doing this for bias corrected dates
            # print(f"{str_date} not bias corrected so no bias correction qaqc outputs to export")
            continue
        for dvar in ds_day.data_vars:
            include = True
            for coord in ds_day[dvar].coords: # if time is one of the coordinates, do not include it
                if "time" in coord:
                    include = False
            if include:
                da_to_include = ds_day[dvar].reset_coords()[dvar] # isolate just the dataarray and the used coordinates
                # add as a coordinate the date
                da_to_include = da_to_include.assign_coords({"date":date})
                lst_das.append(da_to_include)
        ds_day_qaqc = xr.Dataset({da.name: da for da in lst_das})
        # export day to temporary zarr
        bm_time_day = time.time()
        encoding = define_zarr_compression(ds_day_qaqc)
        dc_chnk = dict(latitude = 100, longitude = 100, quantile=3, bias_corrected = 1)
        ds_day_qaqc_loaded = ds_day_qaqc.load()
        ds_day_qaqc_loaded.to_zarr(fl_scratch_out_qaqc_day, mode = "w", encoding = encoding, consolidated=True)
        # lst_daily_outputs.append(fl_scratch_out_qaqc_day)
        lst_fs_date.append(fl_scratch_out_qaqc_day)
        print(f"Time to export {str_date} qaqc stats to zarr (min): {((time.time() - bm_time_day)/60):.2f} | total script runtime (min): {((time.time() - start_time)/60):.2f}")
        del ds_day_qaqc_loaded
    if len(lst_fs_date) == 0:
        print(f"{year}-{month} no files were created for this month")
        continue
    #%% work
    # lst_fs_date = glob(fldr_scratch_zarr + "da3_qaqc_{}.zarr".format("2003-12*"))
    s_dup_check_results = pd.Series(index = lst_fs_date, dtype="object")
    for f in lst_fs_date:
        ds_day = xr.open_dataset(f, engine = engine, consolidated = True)
        result = check_duplicates(ds_day, dims=['latitude', "longitude"])
        s_dup_check_results.loc[f] = result
    # use the first non-dupilcated dataset as the reference
    f_ref = s_dup_check_results[s_dup_check_results == "no_duplicates"].index[0]
    reference_ds = xr.open_dataset(f_ref, engine = engine, consolidated = True)
    latitudes = reference_ds['latitude']
    longitudes = reference_ds['longitude']
    lst_ds_date = []
    for f in lst_fs_date:
        ds_day = xr.open_dataset(f, engine = engine, consolidated = True).chunk(dict(bias_corrected=-1))
        if s_dup_check_results.loc[f] != "no_duplicates":
            ds_day = ds_day.assign_coords({
                'latitude': latitudes,
                'longitude': longitudes
            })
        lst_ds_date.append(ds_day)
    ds_qaqc = xr.concat(lst_ds_date, dim="date")
    #%% end work
    # ds_qaqc = xr.open_mfdataset(lst_fs_date, engine = "zarr", concat_dim="date", combine="nested")
    bm_time = time.time()
    encoding = define_zarr_compression(ds_qaqc)
    # dc_chnk = dict(date=-1, latitude = 100, longitude = 100, quantile=3, bias_corrected = 1)
    ds_qaqc.to_zarr(fl_scratch_out_qaqc, mode = "w", encoding = encoding, consolidated=True)
    lst_monthly_outputs.append(fl_scratch_out_qaqc)
    print(f"Time to export {year}-{month} qaqc stats to zarr (min): {((time.time() - bm_time)/60):.2f} | total script runtime (min): {((time.time() - start_time)/60):.2f}")
    # delete the daily files
    for f in lst_fs_date:
        shutil.rmtree(f)
print(f"Time to export monthly qaqc stats to zarr for year {year} (min): {((time.time() - bm_time0)/60):.2f} | total script runtime (min): {((time.time() - start_time)/60):.2f}")


# consolidate to yearly datasets
if len(lst_monthly_outputs) == 0:
    print(f"There was no data for year {year}")
    sys.exit(0)

# #%% work

# lst_monthly_outputs = return_monthly_files_for_year(year)

# import numpy as np
# for trial_year in np.arange(2001, 2024):
#     return_monthly_files_for_year(trial_year)
#     if len(lst_monthly_outputs) > 1:
#         print(f"year = {trial_year}")
#         break

# lst_monthly_outputs.sort()
# lst_monthly_outputs = lst_monthly_outputs[:-2]
#%% end work
fl_out_qaqc_out = fldr_out + "_qaqc_of_resampled_data_{}.zarr".format(year)
dc_chnk = dict(date=30, latitude = 500, longitude = 1000)
ds_qaqc_year = xr.open_mfdataset(lst_monthly_outputs, engine = "zarr", concat_dim="date", combine="nested")
ds_qaqc_year = ds_qaqc_year.chunk(dc_chnk)
bm_time = time.time()
encoding = define_zarr_compression(ds_qaqc_year)


ds_qaqc_year.to_zarr(fl_out_qaqc_out, mode = "w", encoding = encoding, consolidated=True)
print(f"Time to export {year} qaqc stats to zarr (min): {((time.time() - bm_time)/60):.2f} | total script runtime (min): {((time.time() - start_time)/60):.2f}")

# ds_qaqc_year_test = xr.open_dataset(date_test, engine = engine, consolidated=True).chunk(dc_chnk)

# scratch files once netcdf has been created
for f in lst_monthly_outputs:
    try:
        shutil.rmtree(f)
    except:
        pass
    try:
        os.remove(f)   
    except:
        pass



#%% work - exporting version at reference resolution
# bias_correction_reference = "aorc"
# if bias_correction_reference == "stageiv":
#     f_nc_stageiv = glob(fldr_bias_crxn_ref + "*/*")
#     f_nc_stageiv = f_nc_stageiv[-1]
#     ds_ref = xr.open_dataset(f_nc_stageiv)
#     ds_ref = process_dans_stageiv(ds_ref)
#     ds_ref['time'] = ds_ref.time - pd.Timedelta(1, "hours")
# elif bias_correction_reference == "aorc":
#     lst_f_aorc_yr = glob(f"{fldr_bias_crxn_ref}/data/2022*") # using 2022
#     f_aorc_yr = lst_f_aorc_yr[0]
#     da_aorc_rainfall = xr.open_dataset(f_aorc_yr, engine = "zarr", chunks = 'auto')["APCP_surface"]
#     da_aorc_rainfall = da_aorc_rainfall.sel(time="20220501") # arbitrarily selecting may 1st
#     da_aorc_rainfall.name = "rainrate" # rename like mrms
#     if da_aorc_rainfall.attrs["units"] != "kg/m^2": # verify units (these are equivalent to mm/hr)
#         sys.exit(f'WARNING: AORC RAINFALL UNITS NOT RECOGNIZED da_aorc_rainfall.attrs["units"]={da_aorc_rainfall.attrs["units"]}')
#     ds_ref = da_aorc_rainfall.to_dataset()
#     if ds_ref.longitude.values.min() < 0:
#         ds_ref["longitude"] = ds_ref.longitude + 360

# lst_outs_year_ref_res = []
# print("Creating yearly outputs of qaqc data.....")
# for year in df_yearmonths.year.unique():
#     f_out_resampled = fldr_out + "_qaqc_of_resampled_data_{}_ref_res.zarr".format(year)
#     lst_outs_year_ref_res.append(f_out_resampled)
#     bm_time = time.time()
#     lst_f_scratch_out = glob(fldr_scratch_zarr + "da3_qaqc_{}*.zarr".format(year))
#     ds_qaqc_year = xr.open_mfdataset(lst_f_scratch_out, engine = "zarr", chunks = "auto")
#     bm_time2 = time.time()
#     ds_ref_subset = clip_ds_to_another_ds(ds_ref, ds_qaqc_year)
#     ds_qaqc_year_to_ref = spatial_resampling(ds_qaqc_year, ds_ref_subset, "latitude", "longitude", missingfillval = 0)
#     bm_time = time.time()
#     encoding = define_zarr_compression(ds_qaqc_year_to_ref)
#     dc_chnk = dict(date=-1, latitude = 3500, longitude = 3500, quantile=3, bias_corrected = 1)
#     ds_qaqc_year_to_ref.chunk(dc_chnk).to_zarr(f_out_resampled, mode = "w", encoding = encoding, consolidated=True)
#     print(f"Time to export {year} qaqc stats at ref res to zarr (min): {((time.time() - bm_time)/60):.2f} | total script runtime (min): {((time.time() - start_time)/60):.2f}")
# print("Done creating yearly outputs of qaqc data.....")

#%% end work
