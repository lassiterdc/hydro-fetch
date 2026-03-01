#%% import libraries
import shutil
import pandas as pd
import sys
from glob import glob
import xarray as xr
import time
from __utils import *
import os
from tqdm import tqdm
import geopandas as gpd
import rioxarray as rxr
import dask

start_time = time.time()

final_output_type = "zarr"

if final_output_type == "zarr":
    engine = "zarr"
else:
    engine = "h5netcdf"

#%% work
year = 2003 # "all" # 2002
fldr_mrms = "/project/quinnlab/dcl3nd/norfolk/highres-radar-rainfall-processing/data/mrms_zarr_preciprate_fullres_dailyfiles_constant_tstep/"
fldr_bias_crxn_ref = "/project/quinnlab/dcl3nd/norfolk/highres-radar-rainfall-processing/data/raw_data/raw_data/aorc/"
shp_gages = "/project/quinnlab/dcl3nd/norfolk/highres-radar-rainfall-processing/data/geospatial/rain_gages.shp"
fldr_out_zarr = "/project/quinnlab/dcl3nd/norfolk/highres-radar-rainfall-processing/data/mrms_zarr_preciprate_fullres_yearlyfiles_atgages/"
#%% end work
fldr_mrms = str(sys.argv[1]) # ${assar_dirs[out_fullres_dailyfiles_consolidated]} # "/scratch/dcl3nd/highres-radar-rainfall-processing/out_fullres_dailyfiles_consolidated/"
fldr_bias_crxn_ref = str(sys.argv[2])
shp_gages = str(sys.argv[3])
fldr_out_zarr = str(sys.argv[4]) # assar_dirs[out_fullres_yearly_atgages]
try:
    year = int(sys.argv[5])
except:
    year = "all"
#%% load mrms data
bm_time0 = time.time()
if year != "all":
    lst_f_mrms = glob(f"{fldr_mrms}{year}*.zarr")
else:
    lst_f_mrms = []
    for f in glob(f"{fldr_mrms}*.zarr"):
        if "qaqc" not in f.split("/")[-1]:
            lst_f_mrms.append(f)

# ds = xr.open_dataset(lst_f_mrms[0], engine=engine, consolidated = True)
gdf_clip = gpd.read_file(shp_gages).buffer(2500).to_crs("EPSG:4326")
minx, miny, maxx, maxy = gdf_clip.total_bounds

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
lst_f_mrms.sort()
s_dup_check_results = pd.Series(index = lst_f_mrms, dtype="object")
ds_ref_structure = None
for f in lst_f_mrms:
    ds_day = xr.open_dataset(f, engine = engine, consolidated = True)
    if (ds_day["bias_corrected"].values[0] == True) and (ds_ref_structure is None):
        ds_ref_structure = ds_day.copy()
    result = check_duplicates(ds_day, dims=['latitude', "longitude"])
    if result == "duplicates":
        print("WARNING: A dataset has duplicate latitude or longitude values:")
        print(f)
        print(ds_day)
    s_dup_check_results.loc[f] = result
# use the first non-dupilcated dataset as the reference
f_ref = s_dup_check_results[s_dup_check_results == "no_duplicates"].index[0]
reference_ds = xr.open_dataset(f_ref, engine = engine, consolidated = True)
latitudes = reference_ds['latitude']
longitudes = reference_ds['longitude']
lst_da_rainrates = []
lst_ds_qaqcvars = []
# lst_ds_date = []
for f in lst_f_mrms:
    ds_day = xr.open_dataset(f, engine = engine, consolidated = True).chunk("auto")
    ds_day = ds_day.sortby("time")
    if s_dup_check_results.loc[f] != "no_duplicates":
        ds_day = ds_day.assign_coords({
            'latitude': latitudes,
            'longitude': longitudes
        })
    ds_day = ds_day.rio.write_crs("EPSG:4326")
    ds_day = ds_day.rio.clip_box(minx+360, miny, maxx+360, maxy)
    # make sure structure is consistent
    if (ds_day["bias_corrected"].values[0] == False):
        # fill missing data arrays with na
        for var in ds_ref_structure.data_vars:
            if var not in ds_day.data_vars:
                # Add the missing variable with NaN values, matching dimensions from ds_ref_structure
                ds_day[var] = xr.full_like(ds_ref_structure[var], fill_value=float('nan'))
    # add time as a coordinate to data arrays that don't have it
    date = ds_day.time.to_series().sort_values().iloc[0]
    lst_das_qaqc = []
    for var in ds_day.data_vars:
        if "time" not in ds_day[var].coords:
            with dask.config.set(**{'array.slicing.split_large_chunks': False}):
                ds_day[var] = ds_day[var].expand_dims({"date":[date]})
                lst_das_qaqc.append(ds_day[var])
        else:
            lst_da_rainrates.append(ds_day[var])
    lst_ds_qaqcvars.append(xr.merge(lst_das_qaqc))
    # lst_ds_date.append(ds_day)

chunks = {
    "time": 720,         # Adjust to match uniform time chunks
    "bias_corrected": 2,
    "latitude": 15,
    "longitude": 27
}
# ds_mrms = xr.combine_by_coords(lst_ds_date)
ds_rain = xr.concat(lst_da_rainrates, dim = "time").chunk(chunks).to_dataset()
# ds_mrms = ds_mrms.load()
print(f"Time to load all mrms data for year {year} (min): {((time.time() - bm_time0)/60):.2f} | total script runtime (min): {((time.time() - start_time)/60):.2f}")

bm_time = time.time()
encoding = define_zarr_compression(ds_rain)
f_out_zarr = f"{fldr_out_zarr}{year}_mrms_at_gages.zarr"
ds_rain.to_zarr(f_out_zarr, mode = "w", encoding = encoding)
print(f"Time to export ds_mrms for year {year} to zarr (min): {((time.time() - bm_time)/60):.2f} | total script runtime (min): {((time.time() - start_time)/60):.2f}")
print(f_out_zarr)

ds_qaqc = xr.concat(lst_ds_qaqcvars, dim = "date").chunk({"date":30, "bias_corrected": 2,"latitude": 15,"longitude": 27}).load()
bm_time = time.time()
encoding = define_zarr_compression(ds_qaqc)
f_out_zarr = f"{fldr_out_zarr}{year}_mrms_at_gages_qaqc.zarr"
ds_qaqc.to_zarr(f_out_zarr, mode = "w", encoding = encoding)
print(f"Time to export ds_mrms for year {year} to zarr (min): {((time.time() - bm_time)/60):.2f} | total script runtime (min): {((time.time() - start_time)/60):.2f}")
print(f_out_zarr)
# %%
