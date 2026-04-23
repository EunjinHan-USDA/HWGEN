"""Compute and plot cumulative GDD for climatology vs HWGEN output.

This script is written for portability and repository sharing:
- Paths are repository-relative.
- GDD and cumulative GDD are computed with vectorized operations.
- Repeated logic is wrapped in helper functions.
"""

from os import path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


SITE_DICT = {
    "AL02": "AL_EVSmith",
    "WA02": "WA_Ritzville",
}


PROJECT_ROOT = path.dirname(path.dirname(path.abspath(__file__)))


def add_calendar_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["date"] = pd.to_datetime(df["YEAR"].astype(str) + df["DOY"].astype(str), format="%Y%j")
    df["MONTH"] = df["date"].dt.month
    return df


def filter_season(df: pd.DataFrame, start_doy: int, end_doy: int, year_col: str) -> pd.DataFrame:
    """Filter a seasonal window and build season_year, including cross-year seasons."""
    if end_doy >= start_doy:
        out = df[(df["DOY"] >= start_doy) & (df["DOY"] <= end_doy)].copy()
        out.loc[:, "season_year"] = out[year_col]
        return out

    out = df[(df["DOY"] >= start_doy) | (df["DOY"] <= end_doy)].copy()
    out.loc[:, "season_year"] = out[year_col]
    out.loc[out["DOY"] <= end_doy, "season_year"] = out["season_year"] - 1

    start_year = out.loc[out["DOY"] >= start_doy, "season_year"].min()
    end_year = out.loc[out["DOY"] <= end_doy, "season_year"].max()
    out = out[(out["season_year"] >= start_year) & (out["season_year"] <= end_year)].copy()
    return out


def overwrite_observed_window(
    df: pd.DataFrame,
    source_df: pd.DataFrame,
    source_year: int,
    window_start_doy: int,
    window_end_doy: int,
) -> pd.DataFrame:
    """Replace TMAX/TMIN in the window using source_df values from source_year by DOY."""
    out = df.copy()
    source = source_df[
        (source_df["season_year"] == source_year)
        & (source_df["DOY"] >= window_start_doy)
        & (source_df["DOY"] <= window_end_doy)
    ][["DOY", "TMAX", "TMIN"]].drop_duplicates(subset=["DOY"])

    tmax_map = source.set_index("DOY")["TMAX"]
    tmin_map = source.set_index("DOY")["TMIN"]

    mask = (out["DOY"] >= window_start_doy) & (out["DOY"] <= window_end_doy)
    out.loc[mask, "TMAX"] = out.loc[mask, "DOY"].map(tmax_map).to_numpy()
    out.loc[mask, "TMIN"] = out.loc[mask, "DOY"].map(tmin_map).to_numpy()
    return out


def compute_gdd(df: pd.DataFrame, tbase: float, topt: float) -> pd.DataFrame:
    """Vectorized GDD and cumulative GDD per season_year."""
    out = df.copy()
    out.loc[:, "Tavg"] = (out["TMAX"] + out["TMIN"]) / 2.0
    clipped = out["Tavg"].clip(lower=tbase, upper=topt)
    out.loc[:, "GDD"] = clipped - tbase
    out.loc[:, "day_count"] = out.groupby("season_year").cumcount() + 1
    out.loc[:, "cumGDD"] = out.groupby("season_year")["GDD"].cumsum()
    return out


def gdd_quantiles(df: pd.DataFrame) -> pd.DataFrame:
    grp = df.groupby("day_count")["cumGDD"]
    return pd.DataFrame(
        {
            "day_count": grp.mean().index,
            "cumGDD_5th": grp.quantile(0.05).to_numpy(),
            "cumGDD_50th": grp.quantile(0.50).to_numpy(),
            "cumGDD_95th": grp.quantile(0.95).to_numpy(),
            "cumGDD_mean": grp.mean().to_numpy(),
        }
    )


def main() -> None:
    wsta = "AL02"
    target_scf_year = 2021
    plot_year = 2021
    trimester1 = "DJF"

    plot_start_date = "2021-11-01"
    plot_end_date = "2022-03-31"
    sampling_date = "2022-03-30"   #rye termination date

    planting_doy = 305
    termination_doy = 90
    obs_start_doy = 305   #Nov 1 - the first date when observed weather is availalbe
    obs_end_doy = 334     #Nov 30 - the last date when observed weather is availalbe

    tbase = 4.4
    topt = 24.4

    main_dir = path.join(PROJECT_ROOT, "HWGEN_out")

    daymet_path = path.join(PROJECT_ROOT, "data", "Daymet")
    obs_fname = path.join(daymet_path, f"daymet_{SITE_DICT[wsta]}.csv")
    df_obs = pd.read_csv(obs_fname)[["YEAR", "DOY", "TMAX", "TMIN"]]
    df_obs = add_calendar_columns(df_obs)
    df_obs = filter_season(df_obs, planting_doy, termination_doy, "YEAR")
    df_obs = overwrite_observed_window(df_obs, df_obs, plot_year, obs_start_doy, obs_end_doy)
    df_obs_gdd = compute_gdd(df_obs, tbase, topt)

    march_daily = df_obs_gdd[df_obs_gdd["MONTH"] == 3].groupby("day_count")["GDD"].mean()
    print("March AVG GDD in climatology")
    print("minmum = ", np.min(march_daily.values))
    print("maximum = ", np.max(march_daily.values))

    obs_year_df = df_obs_gdd[df_obs_gdd["season_year"] == plot_year].reset_index(drop=True)
    clim_quantile = gdd_quantiles(df_obs_gdd)

    gen_fname = path.join(
        main_dir,
        f"{wsta}_{target_scf_year}",
        f"{wsta}_{trimester1}",
        f"HWGEN_season_corr_out_{target_scf_year}.csv",
    )
    print(gen_fname)

    df_gen = pd.read_csv(gen_fname)[["iyear", "YEAR", "DOY", "TMAX", "TMIN"]]
    df_gen = df_gen.astype({"iyear": int, "YEAR": int, "DOY": int})
    df_gen = add_calendar_columns(df_gen)
    df_gen.loc[:, "YEAR2"] = df_gen["iyear"] + df_gen["YEAR"]
    df_gen = filter_season(df_gen, planting_doy, termination_doy, "YEAR2")
    df_gen = overwrite_observed_window(df_gen, df_obs, plot_year, obs_start_doy, obs_end_doy)
    df_gen_gdd = compute_gdd(df_gen, tbase, topt)

    gen_quantile = gdd_quantiles(df_gen_gdd)

    obs_val = obs_year_df.loc[obs_year_df["date"] == sampling_date, "cumGDD"].values[0]
    idx = obs_year_df["date"] == sampling_date
    clim_mean = clim_quantile.loc[idx, "cumGDD_mean"].values[0]
    gen_mean = gen_quantile.loc[idx, "cumGDD_mean"].values[0]
    clim_med = clim_quantile.loc[idx, "cumGDD_50th"].values[0]
    gen_med = gen_quantile.loc[idx, "cumGDD_50th"].values[0]

    print("observed cumGDD on", sampling_date, ":", int(obs_val))
    print("climatology mean cumGDD on", sampling_date, ":", int(clim_mean))
    print("HWGEN mean cumGDD on", sampling_date, ":", int(gen_mean))
    print("obs GDD - climGDD = ", round(obs_val - clim_mean, 2))
    print("obs GDD - HWGEN GDD = ", round(obs_val - gen_mean, 2))
    print("climatology median cumGDD on", sampling_date, ":", int(clim_med))
    print("HWGEN median cumGDD on", sampling_date, ":", int(gen_med))
    print("obs GDD - climGDD = ", round(obs_val - clim_med, 2))
    print("obs GDD - HWGEN GDD = ", round(obs_val - gen_med, 2))

    xdate = pd.date_range(start=plot_start_date, end=plot_end_date)
    gen_quantile.loc[:, "date"] = xdate
    target_dates = [
        "2021-11-01",
        "2021-12-01",
        "2022-01-01",
        "2022-02-01",
        "2022-03-01",
        "2022-04-01",
    ]
    indices = gen_quantile[gen_quantile["date"].isin(target_dates)].index
    x_major_ticks = gen_quantile.loc[indices, "day_count"].values
    xdata = gen_quantile["day_count"].values

    fig = plt.figure()
    fig.suptitle("cumGDD forecast issued in Nov 2021", fontsize=12)
    ax0 = fig.add_subplot(111)

    ax0.plot(xdata, clim_quantile["cumGDD_50th"].values, color="orange", linestyle=":", label="Climatology")
    ax0.fill_between(xdata, clim_quantile["cumGDD_5th"].values, clim_quantile["cumGDD_95th"].values, color="orange", alpha=0.2)

    ax0.plot(xdata, gen_quantile["cumGDD_50th"].values, color="blue", linestyle=":", label="HWGEN")
    ax0.fill_between(xdata, gen_quantile["cumGDD_5th"].values, gen_quantile["cumGDD_95th"].values, color="blue", alpha=0.2)

    ax0.plot(xdata, obs_year_df["cumGDD"].values, color="black", linestyle="-.", label="Observed")
    ax0.set_ylabel(r"Cumulative GDD [$^\circ$C]", fontsize=10)
    ax0.set_xlabel("Date [mm-dd]", fontsize=10)
    ax0.set_xlim(xdata[0], xdata[-1])
    ax0.set_ylim(0, 1400)
    ax0.grid(which="major", alpha=0.2)
    ax0.legend(loc="upper center")
    ax0.text(5, 1220, "(b)")
    ax0.set_xticks(x_major_ticks)
    ax0.set_xticklabels(["11-01", "12-01", "01-01", "02-01", "03-01"])

    fig.set_size_inches(5, 4)
    plt.tight_layout()

    fig_name = path.join(
        main_dir,
        f"{wsta}_{target_scf_year}",
        f"{wsta}_{trimester1}",
        f"GDD_forecasts_{wsta}_{target_scf_year}_{trimester1}.png",
    )
    plt.savefig(fig_name)
    plt.show()


if __name__ == "__main__":
    main()

