import sys
from PyQt6 import QtWidgets, QtCore
import PyQt6
import realtime_flare_trigger as rft
import GOES_data_upload as GOES_data
import post_analysis as pa
import datetime
import os


# run_name = 'EXAMPLE_HISTORICAL_RUN2' #utilize this to specify your saved runs
#
# def running_realtime(foldername, historical=False):
#     ''' Runs the RealTimeTrigger algorithm. To utilize the historical GOES 3-day dataset, state historical=True.
#     Otherwise, real-time data will be downloaded from NOAA.'''
#
#     app = QtWidgets.QApplication(sys.argv)
#     if historical:
#         historical_data = GOES_data.FakeDataUpdator(GOES_data.historical_GOES_XRS)
#         main = rft.RealTimeTrigger(historical_data.append_new_data, foldername)
#     else:
#         main = rft.RealTimeTrigger(GOES_data.load_realtime_XRS, foldername)
#     main.show()
#
#     ret = app.exec()
#     #doing post-analysis
#     post_analysis(foldername)
#     sys.exit(ret)
    
def post_analysis(foldername):
    pra = pa.PostRunAnalysis(foldername)
    pra.sort_summary()
    pra.do_launch_analysis()
    pra.do_hold_analysis()
    pra.do_triggers_only_analysis()
    pra.write_text_summary()
    
def utc_time_folder():
    datetime_str_format = "%Y%m%d_%H-%M-%S"
    utc_str = datetime.datetime.now(datetime.timezone.utc).strftime(datetime_str_format)
    return utc_str

# if __name__=="__main__":
#     # put here so if I import then this doesn't run
#     #running_realtime(historical=True, foldername=run_name)
#     utc_folder = utc_time_folder()
#     print(utc_folder)
