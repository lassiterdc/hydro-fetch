#%% Import libraries and set filepaths
import sys
import pandas as pd
import pytz
from glob import glob
import dask
import xarray as xr
import datetime
from __filepaths import *
dask.config.set(**{'array.slicing.split_large_chunks': False})

inches_per_mm = 1/25.4
# f_mrms_csvs_fullres, f_ref_csvs_fullres, fl_events, f_csv_mrms_and_gage_events, f_csv_ref_and_gage_events = return_a2_filepaths()
#%% load mrms data
lst_fs_mrms_at_gages = glob(fldr_mrms_at_gages + "*.zarr")
lst_f_qaqc = []
lst_f_rainfall = []
for f in lst_fs_mrms_at_gages:
    if "all_" in f:
        continue
    if "_qaqc.zarr" in f:
        lst_f_qaqc.append(f)
    else:
        lst_f_rainfall.append(f)
#%%
ds_mrms = xr.open_mfdataset(lst_f_rainfall, chunks = "auto", concat_dim="time", combine="nested")
ds_qaqc = xr.open_mfdataset(lst_f_qaqc, chunks = "auto", concat_dim="date", combine="nested")
#%% load mrms data from csvs
all_files_mrms = glob(f_mrms_csvs_fullres)
all_files_ref = glob(f_ref_csvs_fullres)
# load data of mrms gridcells overlapping HRSD gages
df_mrms_long = pd.concat((pd.read_csv(f, index_col=0, parse_dates=["time"]) for f in all_files_mrms), ignore_index=True)
df_ref_long = pd.concat((pd.read_csv(f, index_col=0, parse_dates=["time"]) for f in all_files_ref), ignore_index=True)

#%% assign timezone to time
def assign_tz(df):
    dt = df.time
    dti = pd.DatetimeIndex(dt, tz="utc")
    df.time = dti
    return df

df_mrms_long = assign_tz(df_mrms_long)
df_ref_long = assign_tz(df_ref_long)
#%% load HRSD data
gage_ids = df_mrms_long.overlapping_gage_id.unique()

df_events_wide = pd.read_csv(fl_events, parse_dates=["Time"])
dti = pd.DatetimeIndex(df_events_wide.Time)
if dti.tz != pytz.utc:
    sys.exit("The timezone of the gage data is either non-UTC or unassigned. Exiting script...")

df_events_long = pd.melt(df_events_wide, id_vars = ["Time", "event_id"], value_vars = gage_ids,
                        var_name = "gage_id", value_name = "gage_rainfall")
#%% convert mrms data to a proceeding 15-minute timestamp (note that it is already a proceeding time interval)
def convert_to_15min(df):
    df = df.sort_values(["overlapping_gage_id", "time"])
    # df["duplicated"] = df.duplicated(keep = False)
    df = df.drop_duplicates()
    # df_no_dups[(df_no_dups.time.dt.date == datetime.date(2013, 1, 3)).values]
    # df[list(df.time.dt.date == datetime.date(2013, 1, 3))]
    ## convert to 1 minute
    df_1min = df.set_index("time")
    df_1min = df_1min.groupby("overlapping_gage_id")
    df_1min = df_1min.resample("1min").bfill()
    df_1min = df_1min.droplevel("overlapping_gage_id")

    # convert to 15 minute
    for col in df.columns:
        if "_lat" in col:
            lat_name = col
        if "_lon" in col:
            lon_name = col

    df_15min = df_1min.groupby(["overlapping_gage_id", lat_name, lon_name])
    df_15min = df_15min.resample("15min").mean()
    df_15min = df_15min.drop(labels=[lat_name, lon_name], axis="columns")

    # convert from mm/hr to inches
    df_15min["precip_in"] = df_15min.loc[:, "precip_mm_per_hour"] * 15/60 * inches_per_mm # mm/hr * 15/60 hrs * in/mm
    return df_15min

#%% merge the dataframe 
#%% merge dataframe with gage stuff
def merge_df(df_15min):
    df_out = pd.merge(df_15min, df_events_long, how = 'left', left_on = ['time', 'overlapping_gage_id'], right_on = ['Time', 'gage_id'])

    # drop timesteps where HRSD events and MRMS timesteps do not overlap
    df_out.dropna(subset="event_id", inplace=True)

    df_out =  df_out.reset_index(drop=True)

    df_out = df_out.rename(columns={"Time":"time", "gage_rainfall":"gage_precip_in"})

    df_out = df_out.loc[:, ['time', 'gage_id', 'event_id', 'precip_in', 'gage_precip_in']]

    df_out = df_out.astype({"event_id":int})

    return df_out


#%%
df_ref_long_15min = convert_to_15min(df_ref_long)
df_out_ref = merge_df(df_ref_long_15min)
df_out_ref.to_csv(f_csv_ref_and_gage_events)
#%%
del df_ref_long_15min
del df_out_ref

#%%
df_mrms_long_15min = convert_to_15min(df_mrms_long)
df_out_mrms = merge_df(df_mrms_long_15min)
df_out_mrms.to_csv(f_csv_mrms_and_gage_events)

print("finished exporting csv")