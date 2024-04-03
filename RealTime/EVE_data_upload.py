import os
import wget
import json
import datetime as dt
import numpy as np
import math
import pandas as pd

def load_realtime_EVE():
    ''' Retrieves the latest EVE 10 second data.
    '''
    json_url="https://lasp.colorado.edu/eve/data_access/eve_data/quicklook/L0CS/LATEST_EVE_L0CS_DIODES_10s_counts.json" 
    json_file='LATEST_EVE_L0CS_DIODES_10s_counts.json'
    
    if os.path.exists(json_file):
        os.remove(json_file)

    try:
        wget.download(json_url, bar=None)
        with open(json_file) as f: 
            eve_current = pd.DataFrame(json.load(f))
        eve_current = eve_current.iloc[-200:]
        eve_current.reset_index(drop=True, inplace=True)
        # eve0diff = np.array(eve_current['ESP_0_7_COUNTS'])
        # eve0diff = eve0diff[1:] - eve0diff[:-1]
        # eve0diff_final = np.concatenate([np.full(1, math.nan), eve0diff]) #appending correct # of 0's to front
        # eve_current['ESP_0_7_DIFFS'] = eve0diff_final
        return eve_current
    
    except Exception as e:
        print(f"Likely EVE download error from `wget`:\n{e}")
        #return load_realtime_EVE()
        
if __name__=='__main__':
    t = load_realtime_EVE()
    print(t)