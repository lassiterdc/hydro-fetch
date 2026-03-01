#%%
import numpy as np
import pandas as pd
import xarray as xr
from glob import glob
import matplotlib.pyplot as plt
# import flox
from pathlib import Path

# define filepaths
f_plot_ptrn = "plots/bias_crctd_mrms_qaqc/"
fldr_mrms_constant_tstep = "D:/Dropbox/_GradSchool/_norfolk/highres-radar-rainfall-processing/data/mrms_zarr_preciprate_fullres_dailyfiles_constant_tstep/"
lst_fs_qaqc = glob(fldr_mrms_constant_tstep + "*qaqc*.zarr")

#%%

def plot_multipanel_plot(ds, parent_fldr, lst_vars, lst_cbar_lab = None, lst_vmin = None, lst_vmax = None, lst_cmap = None, figpath_suffix="",
                         fig_title_suffix = ""):
    Path(parent_fldr).mkdir(parents=True, exist_ok=True)
    figsize = (13,4)
    # return agg var
    for coord in ds.coords:
        if coord not in ["longitude", "latitude", "spatial_ref"]:
            agg = coord
    agg_vars = pd.unique(ds[agg].values)
    for agg_var in agg_vars:
        ds_sub = ds.sel({agg:agg_var})
        if agg == "date":
            agg_var = str(agg_var)[0:10]
        fig_fpath = "{}{}_{}_{}.png".format(parent_fldr,agg,agg_var,figpath_suffix)

        ncols = int(np.ceil(np.sqrt(len(lst_vars))))
        nrows = int(np.ceil(len(lst_vars)/ncols))
        fig, axes = plt.subplots(ncols=ncols, nrows=nrows, figsize = (ncols*4.75, nrows*4), dpi = 250)
        count = -1
        for row_id, row in enumerate(axes):
            for ax in row:
                count += 1
                if count == len(lst_vars):
                    break
                var_to_plot = lst_vars[count]
                dict_cbar_args = {}
                pcolormesh_args = {}
                if lst_cbar_lab is not None:
                    dict_cbar_args["label"] = lst_cbar_lab[count]
                if lst_vmin is not None:
                    pcolormesh_args["vmin"] = lst_vmin[count]
                if lst_vmax is not None:
                    pcolormesh_args["vmax"] = lst_vmax[count]
                if lst_cmap is not None:
                    pcolormesh_args["cmap"] = lst_cmap[count]
                # print("pcolormesh_args: {}".format(pcolormesh_args))
                # print("dict_cbar_args: {}".format(dict_cbar_args))
                ds_sub[var_to_plot].plot.pcolormesh(ax = ax, **pcolormesh_args, cbar_kwargs=dict_cbar_args)
                ax.set_title(var_to_plot)
        fig.suptitle("{} {} | {}".format(agg, agg_var, fig_title_suffix))
        fig.tight_layout()
        plt.savefig(fig_fpath)
        plt.close()

# define functions
def determine_vmax_for_multiple_vars(ds, lst_vars, quantile_cutoff = 0.98):
    vmax = -9999
    for var in lst_vars:
        da = ds[var]
        vmax_var = da.to_dataframe().quantile(quantile_cutoff).max()
        if vmax_var > vmax:
            vmax = vmax_var
    print("vmax = {}".format(vmax))
    return vmax

# define functions for computing whether points are within 10% of 1 to 1 line
def comp_dist_to_1to1_line(df, xvar, yvar):
    # https://en.wikipedia.org/wiki/Distance_from_a_point_to_a_line
    b = 1
    a = -1*b
    c = 0
    x0 = df[xvar]
    y0 = df[yvar]

    dist = np.abs(a * x0 + b * y0 + c) / np.sqrt(a**2 + b**2)
    nearest_x = (b * (b*x0 - a * y0) - a * c) / (a**2 + b**2)
    nearest_y = (a*(-b*x0 + a*y0) - b*c)/(a**2 + b**2)

    dist.name = "distance_to_1to1_line"
    nearest_x.name = "x_coord_of_nearest_pt_on_1to1_line"
    nearest_y.name = "y_coord_of_nearest_pt_on_1to1_line"

    return dist, nearest_x, nearest_y

def compute_frac_within_tolerance_of_1to1_line(dist, nearest_x, frac_tol):
    s_within_tol = (dist <= nearest_x*(frac_tol/2))
    return s_within_tol.sum()/len(s_within_tol)

# define hexbin plot function
def plt_hexbin(df, frac_tol = 0.1, col1="mrms_biascorrected_daily_totals_mm", col2="mrms_nonbiascorrected_daily_totals_mm",
                refcol ="ref_daily_totals_mm",logcount = True, gridcnt = 40, fig_fpath = None,
                fig_title = None):
    fig, (ax0, ax1) = plt.subplots(ncols=2, figsize=(10, 4), dpi = 300)

    ylim = xlim = (0, df.loc[:,refcol ].max())
    nx = gridcnt
    ny = int(round(nx / np.sqrt(3),0))
    extent = xlim[0], xlim[1], ylim[0], ylim[1]
    # xlim = (0, max(df.loc[:, col1].max(), df.loc[:, col2].max()))
    ax0.set(xlim=xlim, ylim=ylim)
    ax1.set(xlim=xlim, ylim=ylim)

    if logcount:
        hb1 = ax0.hexbin(df.loc[:, col1], df.loc[:,refcol ], bins='log', cmap='inferno',mincnt=5,gridsize=(nx, ny), extent = extent)
        hb2 = ax1.hexbin(df.loc[:, col2], df.loc[:,refcol ], bins='log', cmap='inferno',mincnt=5,gridsize=(nx, ny), extent = extent)
    else:
        hb1 = ax0.hexbin(df.loc[:, col1], df.loc[:,refcol ], cmap='inferno', mincnt=5,gridsize=(nx, ny), extent = extent)
        hb2 = ax1.hexbin(df.loc[:, col2], df.loc[:,refcol ], cmap='inferno', mincnt=5,gridsize=(nx, ny), extent = extent)

    # compute frac of points within tolerance
    dist1, nearest_x1, nearest_y1 = comp_dist_to_1to1_line(df, col1, refcol)
    frac_pts_in_tol1 = compute_frac_within_tolerance_of_1to1_line(dist1, nearest_x1, frac_tol)
    dist2, nearest_x2, nearest_y2 = comp_dist_to_1to1_line(df, col2, refcol)
    frac_pts_in_tol2 = compute_frac_within_tolerance_of_1to1_line(dist2, nearest_x2, frac_tol)

    ax0.set_xlabel(df.loc[:, col1].name)
    ax0.set_ylabel(df.loc[:,refcol ].name)
    ax1.set_xlabel(df.loc[:, col2].name)
    ax1.set_ylabel(df.loc[:,refcol ].name)

    ax0.set_title("Percent of observations within {}% of the 1:1 line: {}%".format(int(frac_tol*100), round(frac_pts_in_tol1*100, 2)),
                  fontsize = 9)
    ax1.set_title("Percent of observations within {}% of the 1:1 line: {}%".format(int(frac_tol*100), round(frac_pts_in_tol2*100, 2)),
                  fontsize = 9)
    # add lines showing tolerance threshold
    x0 = y0 = np.linspace(0, xlim, 500)
    dist = x0 * frac_tol/2
    # based on a^2 + b^2 = c^2, assuming 1:1 line so a=b
    x_upper = x0 - np.sqrt(dist**2/2)
    y_upper = y0 + np.sqrt(dist**2/2)
    x_lower = x0 + np.sqrt(dist**2/2)
    y_lower = y0 - np.sqrt(dist**2/2)

    ax0.plot(x_upper, y_upper, label = "upper bound", c = "cyan", ls = "--", linewidth = 0.7, alpha = 0.8)
    ax0.plot(x_lower, y_lower, label = "lower bound", c = "cyan", ls = "--", linewidth = 0.7, alpha = 0.8)

    ax1.plot(x_upper, y_upper, label = "upper bound", c = "cyan", ls = "--", linewidth = 0.7, alpha = 0.8)
    ax1.plot(x_lower, y_lower, label = "lower bound", c = "cyan", ls = "--", linewidth = 0.7, alpha = 0.8)

    # ax1.set_title("With a log color scale")
    cb1 = fig.colorbar(hb1, ax=ax0, label='')
    cb2 = fig.colorbar(hb2, ax=ax1, label='')
    ax0.axline((0, 0), slope=1, c = "cyan", ls = "--", linewidth = 1.2)
    ax1.axline((0, 0), slope=1, c = "cyan", ls = "--", linewidth = 1.2)
    # define lines based on upper and lower bounds of defined tolerance
    pts = nearest_y1[nearest_y1>0].quantile([0.1, 0.9])
    # create folder if it doesn't already exist
    Path(fig_fpath).parent.mkdir(parents=True, exist_ok=True)
    if fig_title is not None:
        fig.suptitle(fig_title)
    # fig.tight_layout()
    if fig_fpath is not None:
        plt.savefig(fig_fpath)
    plt.close()
    return

#%%
# ds_qaqc = xr.open_dataset(lst_fs_qaqc[0], engine = "zarr", consolidated = True).chunk(dict(date = 1))
ds_qaqc = xr.open_mfdataset(lst_fs_qaqc, engine = "zarr", concat_dim="date", combine="nested")
ds_subset = ds_qaqc[["mrms_biascorrected_daily_totals_mm", "mrms_nonbiascorrected_daily_totals_mm","ref_daily_totals_mm"]]
ds_subset.coords["year"] = ds_subset['date'].dt.strftime('%Y')
ds_subset.coords["year_month"] = ds_subset['date'].dt.strftime('%Y-%m')
#%% hex plots
years = pd.unique(ds_subset.date.dt.year.values)
#%% work
# years = years[0:1]
#%% end work

ds_subset_yearly_totals = ds_subset.groupby("year").sum()
ds_subset_yearly_totals = ds_subset_yearly_totals.load()
# subset only where the mrms and reference data have non zero totals
condition = (ds_subset_yearly_totals["mrms_nonbiascorrected_daily_totals_mm"] > 0) & \
            (ds_subset_yearly_totals["ref_daily_totals_mm"] > 0)
if condition.sum() > 0:
    ds_subset_yearly_totals = ds_subset_yearly_totals.where(condition, drop=True)
else:
    print("No valid data points matching the condition.")

df_yearly_totals = ds_subset_yearly_totals.to_dataframe().dropna()
plt_hexbin(df_yearly_totals, fig_fpath = f"{f_plot_ptrn}annual_totals_hexbin.png", fig_title = "yearly total comparison")

for yr in years:
    ds_sub_yr = ds_subset_yearly_totals.sel(year = str(yr))
    df_yearly_totals = ds_sub_yr.to_dataframe().dropna()
    plt_hexbin(df_yearly_totals, fig_fpath = "{}hexbins_annualtotals_by_year/year_{}_hexbin_yearly_tots.png".format(f_plot_ptrn,yr), fig_title = "year {} yearly total comparison".format(yr))


#%%
ds_subset_yearmonthly_totals = ds_subset.groupby("year_month").sum()
ds_subset_yearmonthly_totals = ds_subset_yearmonthly_totals.load()
# subset only where the mrms and reference data have non zero totals
condition = (ds_subset_yearmonthly_totals["mrms_nonbiascorrected_daily_totals_mm"] > 0) & \
            (ds_subset_yearmonthly_totals["ref_daily_totals_mm"] > 0)
if condition.sum() > 0:
    ds_subset_yearmonthly_totals = ds_subset_yearmonthly_totals.where(condition, drop=True)
else:
    print("No valid data points matching the condition.")

# df_yearmonthly_totals = ds_subset_yearmonthly_totals.to_dataframe().dropna()
# plt_hexbin(df_yearmonthly_totals, fig_fpath = f"{f_plot_ptrn}annual_totals_hexbin.png", fig_title = "yearmonthly total comparison")

for yr_mnth in ds_subset["year_month"].to_series().unique():
    print(yr_mnth)
    ds_sub_yr = ds_subset_yearmonthly_totals.sel(year_month = str(yr_mnth))
    df_yearmonthly_totals = ds_sub_yr.to_dataframe().dropna()
    plt_hexbin(df_yearmonthly_totals, fig_fpath = "{}hexbins_yearmonthtotals_by_yearmonth/{}_hexbin_yearmonthly_tots.png".format(f_plot_ptrn,yr_mnth), fig_title = "yearmonth {} yearmonthly total comparison".format(yr_mnth))
