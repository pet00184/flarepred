import pandas as pd
import os
import wget
import json

############################# HISTORICAL GOES TESTING DATA #################################################
class FakeDataUpdator:
    ''' To be utilized when using historical_GOES_XRS. Each time data is loaded in the RealTimeTrigger class,
    another datapoint is appended to xrsa_current and xrsb_current, imitating a new minute of data being
    downloaded from NOAA.
    '''
    def __init__(self, fake_data):
        self.xrsa_data_total, self.xrsb_data_total = fake_data()
        self.xrsa_current = self.xrsa_data_total.iloc[0:1]
        self.xrsb_current = self.xrsb_data_total.iloc[0:1]
        
    def append_new_data(self):
        #for this, just append the first data point! 
        next_datapoint = self.xrsa_current.shape[0]
        #print(f'Currently have {next_datapoint} minutes of historical data')
        self.xrsa_current = self.xrsa_current._append(self.xrsa_data_total.iloc[next_datapoint], ignore_index=True)
        self.xrsb_current = self.xrsb_current._append(self.xrsb_data_total.iloc[next_datapoint], ignore_index=True)
        return self.xrsa_current, self.xrsb_current
		
def historical_GOES_XRS():
    ''' Saved 3-day GOES data, to be used for testing/debugging the algorithm. Data is in the same format 
    as the real-time data. Notably, an X-class flare occurs shortly after the start of the data.
    '''
    with open(os.path.dirname(os.path.realpath(__file__))+'/historical-test-GOES.json') as f: 
        df = pd.DataFrame(json.load(f))
    xrsa_current = df[df.energy == '0.05-0.4nm'].iloc[1285:]
    xrsa_current.reset_index(drop=True, inplace=True)
    xrsb_current = df[df.energy == '0.1-0.8nm'] .iloc[1285:]
    xrsb_current.reset_index(drop=True, inplace=True)
    #changing time_tag to datetime format: 
    xrsa_current.loc[:,'time_tag'] = pd.to_datetime(xrsa_current.loc[:,'time_tag'], format='ISO8601')
    xrsb_current.loc[:,'time_tag'] = pd.to_datetime(xrsb_current.loc[:,'time_tag'], format='ISO8601')
    
    return xrsa_current, xrsb_current 
    
########################### REAL-TIME DATA #################################################################
def load_realtime_XRS():   
    ''' Downloads real-time XRS data from NOAA, and is to be used for real-time testing and launch.
    Note: the url and filename remains the same- do not edit.

    Recursive function: if an error occurs during the data download, 
    this function calls itself until successful.
    ''' 
    json_url='https://services.swpc.noaa.gov/json/goes/primary/xrays-6-hour.json'
    json_file='xrays-6-hour.json'
    
    if os.path.exists(json_file):
        os.remove(json_file)

    try:
        wget.download(json_url, bar=None)
    
        with open('xrays-6-hour.json') as f: 
            df = pd.DataFrame(json.load(f))
        xrsa_current = df[df.energy == '0.05-0.4nm'].iloc[-30:]
        xrsa_current.reset_index(drop=True, inplace=True)
        xrsb_current = df[df.energy == '0.1-0.8nm'] .iloc[-30:]
        xrsb_current.reset_index(drop=True, inplace=True)
        #changing time_tag to datetime format: 
        xrsa_current.loc[:,'time_tag'] = pd.to_datetime(xrsa_current.loc[:,'time_tag'], format='ISO8601')
        #reorganizing to single dataframe
        xrsa_current.rename(columns={'flux': 'xrsa'}, inplace=True)
        xrsa_current.drop(['observed_flux', 'electron_correction', 'electron_contaminaton', 'energy'], axis=1, inplace=True)
        goes_current = xrsa_current
        goes_current.insert(3, 'xrsb', xrsb_current['flux'])
        
        return goes_current
    
    except Exception as e:
        print(f"Likely download error from `wget`:\n{e}")
        return load_realtime_XRS()
        