# GOES Real-Time Flare Trigger Algorithm

To run: `python3 run_realtime_algorithm.py`

As of now, it is in "historical" mode, which can be changed to realtime mode in the function "running_realtime" (historical=False).

### Necessary Packages: 
Will add in instructions on creating a virtual environment!
 - `python version 3.11.3`
 - `pandas version 2.0.1`
 - `pyqtgraph version 0.13.3`
 - `numpy version 1.24.3`
 - `PyQt6`
### Included Files: 

**Date Files**:
  - `xrays-6-hour.json`: realtime data file that will be replaced everytime data is reloaded. This file is always this name, and is update once every ~minute by NOAA.
  - `historical-test-GOES.json`: 3-day .json file in the same format as the realtime GOES data. This file is utilized when the real-time code is being run in "historical" mode.
  
**Python Files**:
 - `run_realtime_algorithm.py`: File to be run in the terminal. This runs `realtime_flare_trigger.py` and does analysis on all launces with `post_analysis.py` once the realtime algorithm has been ended. 
 - `realtime_flare_trigger.py`: This determines the state of the launch (searching, triggered, launched), plots real-time data and saves a summary of the flare trigger/launch times as well as the aggregated data downloaded during the entire run. 
 - `post_analysis.py`: Utilizes the saved .csv files to make plots of all launches. Also saves a TextSummary file that summarizes the percentages of launches vs. cancelled triggers vs. held launches, and a summary of each launch.
 - `GOES_data_upload.py`: uploads data for both realtime and historical runs of the real-time code. For realtime data, the xrays-6-hour.json file is redownloaded once every minute. For historical data, one minute of data is added each time the data is reloaded. 
  - `flare_conditions.py`: determines the flare trigger and flare end conditions utilized in the real-time code. These are separate so that they are easily changeable. If/once we choose to add in another cancellation condition, it would also go in this file.

**Files Saved after Run:**
All saved data files are in the ObservationSummary folder. Files are written over for each run if they are named the same. Names may be changed in the "main" function in `realtime_flare_trigger.py`.
  - `GOES_XRSA.csv` and `GOES_XRSB.csv`: Aggregated data saved from the entire run, in the same format as realtime data downloaded form NOAA.
  - `historical_summary.csv`: File containing timestamps for each trigger/event. These timestamps may be used to know how many triggers ended in launch, save plots of "launches", analyze GOES class of launched flares, etc. 

### Flowchart of Realtime System: 

![](algorithm_flowchart.pdf)