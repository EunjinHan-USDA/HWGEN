# HWGEN
HWGEN (Hybrid Weather Generator) is a hybrid stochastic weather generator for temporal downscaling of seasonal tercile climate forecasts into synthetic daily weather series.

It generates daily:
- precipitation (RAIN)
- solar radiation (SRAD)
- maximum temperature (TMAX)
- minimum temperature (TMIN)

# What HWGEN_main_GUI.exe does (CONTACT EUNJIN.HAN@USDA.GOV FOR SOURCE CODE):
- seasonal forecast conditioning (IRI tercile probabilities)
- stochastic weather generation
- monthly low-frequency correction
- seasonal bias correction using theoretical CDF matching
- Final output (synthetic daily weater) file is HWGEN_season_corr_out_####.csv under the output folder (e.g.,"...dist\HWGEN_out\AL02_2021\AL02_DJF")

The workflow combines:
- seasonal forecast probabilities (IRI SCF),
- historical daily weather observations (Daymet),
- weather generation and post-processing,
- downstream agronomic indicators such as cumulative growing degree days (GDD).

## Repository Contents

```
HWGEN/
	README.md
	data/
		Daymet/
			daymet_AL_EVSmith.csv
		IRI_SCF/
			IRI_SCF_L1_pcp_2017_present/
			IRI_SCF_L1_tmp_2017_present/
			IRI_SCF_L4_pcp_2017_present/
			IRI_SCF_L4_tmp_2017_present/
	dist/
		HWGEN_main_GUI.exe
		HWGEN_out/
		compute_GDD_daymet_AL_DJF_2021.py
```

## Data Inputs

### Daymet daily weather
- Location: `data/Daymet/daymet_AL_EVSmith.csv`
- Example columns: `YEAR`, `DOY`, `RAIN`, `SRAD`, `TMAX`, `TMIN`
- Used as observed climatology and for partial observed-window overwrite in early-season days.

### IRI seasonal forecast tercile probabilities
- Location: `data/IRI_SCF/...`
- Includes 1-month and 4-month lead time products for precipitation and temperature.
- Example columns: `Tercile Classes`, `Month Forecast Issued`, `Tercile Probability`

## Current Analysis Script

The script `dist/compute_GDD_daymet_AL_DJF_2021.py` computes and plots cumulative GDD for:
- observed climatology,
- HWGEN-generated seasonal ensembles,
- observed target season.

### What compute_GDD_daymet_AL_DJF_2021.py does
* Note: compute_GDD_daymet_AL_DJF_2021.py is to process HWGEN-generated output to compute GDD
       Therefore,HWGEN_main_GUI.exe should run first and then it will look for `dist/HWGEN_out/...` to read the HWGEN-generated weather data
1. Loads Daymet observed daily Tmax/Tmin.
2. Builds seasonal windows with support for cross-year seasons (for example DJF).
3. Computes daily GDD and cumulative GDD with base and optimum temperature thresholds.
4. Loads HWGEN generated daily weather output.
5. Compares median/mean cumulative GDD at a sampling date.
6. Produces a figure with climatology envelope, HWGEN envelope, and observed cumulative GDD.

### Site mapping in script
- `AL02` -> `AL_EVSmith`
- `WA02` -> `WA_Ritzville`

## Requirements

Python packages used by the analysis script:
- `numpy`
- `pandas`
- `matplotlib`

Install with:

```bash
pip install numpy pandas matplotlib
```

## Running the GDD Example

From the repository root:

```bash
python dist/compute_GDD_daymet_AL_DJF_2021.py
```

The script is currently parameterized internally (site, season, year, thresholds), so edit values in `main()` for alternate experiments.

## Expected Outputs

For the included Alabama DJF 2021 setup, outputs are written under:

`dist/HWGEN_out/AL02_2021/AL02_DJF/`

Example output files include:
- `HWGEN_season_corr_out_2021.csv`
- `GDD_forecasts_AL02_2021_DJF.png`

## Notes

- Paths in the current analysis script are repository-relative for portability.
- The script expects prior HWGEN output files to already exist in `dist/HWGEN_out/...`.
- If you package this as a reusable module, move hard-coded parameters to a config file or command-line arguments.
