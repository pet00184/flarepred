# GOES Real-Time Flare Trigger Algorithm

To run: `python3 realtime_flare_trigger.py`

As of now, it is in "historical" mode, which can be changed to realtime mode in the function "main" (historical=False). Names of saved files can also be changed in "main". 

### Included Files: 

**Date Files**:
  - `xrays-6-hour.json`: realtime data file that will be replaced everytime data is reloaded. This file is always this name, and is update once every ~minute by NOAA.
  - `historical-test-GOES.json`: 3-day .json file in the same format as the realtime GOES data. This file is utilized when the real-time code is being run in "historical" mode.
  
**Python Files**:
 - `realtime_flare_trigger.py`: File to be run in the terminal. This determines the state of the launch (searching, triggered, launched), plots real-time data and saves a summary of the flares as well as the aggregated data downloaded during the entire run. 
 - `GOES_data_upload.py`: uploads data for both realtime and historical runs of the real-time code. For realtime data, the xrays-6-hour.json file is redownloaded once every minute. For historical data, one minute of data is added each time the data is reloaded. 
  - `flare_conditions.py`: determines the flare trigger and flare end conditions utilized in the real-time code. These are separate so that they are easily changeable. If/once we choose to add in another cancellation condition, it would also go in this file.

