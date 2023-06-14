import sys
from PyQt6 import QtWidgets, QtCore
import PyQt6
import realtime_flare_trigger as rft
import GOES_data_upload as GOES_data
import post_analysis as pa


run_name = 'EXAMPLE_HISTORICAL_RUN2' #utilize this to specify your saved runs

def running_realtime(foldername, historical=False):
    ''' Runs the RealTimeTrigger algorithm. To utilize the historical GOES 3-day dataset, state historical=True. 
    Otherwise, real-time data will be downloaded from NOAA.'''
    
    app = QtWidgets.QApplication(sys.argv)
    if historical: 
        historical_data = GOES_data.FakeDataUpdator(GOES_data.historical_GOES_XRS)
        main = rft.RealTimeTrigger(historical_data.append_new_data, foldername)
    else:     
        main = rft.RealTimeTrigger(GOES_data.load_realtime_XRS, foldername)
    main.show()
    
    ret = app.exec()
    #doing post-analysis
    post_analysis(foldername)
    sys.exit(ret) 
    
def post_analysis(foldername):
    pra = pa.PostRunAnalysis(foldername)
    pra.sort_summary()
    pra.do_launch_analysis()
    pra.write_text_summary()
    
running_realtime(historical=True, foldername=run_name)
