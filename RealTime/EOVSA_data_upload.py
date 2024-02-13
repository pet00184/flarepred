import pandas as pd
import os
import wget
import json
from bs4 import BeautifulSoup
from urllib.request import urlopen
from datetime import datetime

class EOVSADataUpload:
    
    main_url = 'http://www.ovsa.njit.edu/fits/FTST/'
    
    def make_full_url(self):
        year = str(datetime.now().year)
        month = datetime.now().strftime("%m")
        self.url = os.path.join(self.main_url, year, month)
    
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
        wget.download(os.path.join(url_maker.url, most_recent_eovsa), bar=None) 
        
        df = pd.read_csv(most_recent_eovsa, sep=" ", header=8, usecols=[1,2, 3, 6, 13, 20, 27, 34, 41, 48]).reset_index(drop=True)
        df.columns = ["date", "time", "Flare Flag", "1-7 GHz", "7-13 GHz", "13-18 GHz", "Mean", "Sigma", "Threshold", "Count"] 
        
        eovsa_current = df
        
        eovsa_current['time'] = pd.to_datetime(eovsa_current['time'], format='%H%M%S').dt.time
        eovsa_current['date'] = pd.to_datetime(eovsa_current['date'], format='%Y%m%d')

        return eovsa_current
    
    except Exception as e:
        print(f"Likely download error from `wget`:\n{e}")
        #return load_realtime_EOVSA()

#
# if __name__ == '__main__':
#     load_realtime_EOVSA()
    