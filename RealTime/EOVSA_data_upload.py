import pandas as pd
import os
import wget
import json
from bs4 import BeautifulSoup
from urllib.request import urlopen
from datetime import datetime
import numpy as np

class EOVSADataUpload:
    
    main_url = 'http://www.ovsa.njit.edu/fits/FTST/'
    
    def make_full_url(self):
        year = str(datetime.now().year)
        month = datetime.now().strftime("%m")
        self.url = f"{self.main_url}{year}/{month}"
    
    def get_last_txt(self):

        # Get the website html
        page = urlopen(self.url)
        html = page.read().decode('utf-8')
        soup = BeautifulSoup(html, 'html.parser')

        # Parse the reversed list of items with hyperlinks.
        # Return the first instance of a .nc file (the most recent).
        for e in reversed(soup.find_all('a', href=True)):
            for c in e.contents:
                if '.txt' in c:
                    return c
        

def load_realtime_EOVSA():
    
    url_maker = EOVSADataUpload()
    url_maker.make_full_url()
    most_recent_eovsa = url_maker.get_last_txt()
    
    if os.path.exists(most_recent_eovsa):
        os.remove(most_recent_eovsa)
        
    try:
        wget.download(f"{url_maker.url}/{most_recent_eovsa}", bar=None) 
        
        #doing the time separately, since pandas df is trying to be smart and make in a float when we want a string
        time_df = pd.read_csv(most_recent_eovsa, sep=' ', header=8, dtype=str, usecols=[2])
        time_df.columns = ['time']
        time_df['time'] = pd.to_datetime(time_df['time'], format='%H%M%S.%f').dt.time
        
        df = pd.read_csv(most_recent_eovsa, sep=" ", header=8, usecols=[1,2, 6, 13, 20, 27, 34, 41, 48]).reset_index(drop=True)
        df.columns = ["date", "Flare Flag", "1-7 GHz", "7-13 GHz", "13-18 GHz", "Mean", "Sigma", "Threshold", "Count"]

        eovsa_current = df
        eovsa_current.insert(1, 'time', time_df['time'])
        eovsa_current['date'] = pd.to_datetime(eovsa_current['date'], format='%Y%m%d')

        return eovsa_current
    
    except Exception as e:
        print(f"Likely EOVSA download error from `wget`:\n{e}")
        return load_realtime_EOVSA()

    