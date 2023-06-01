import pandas as pd
from PyQt6 import QtWidgets, QtCore
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
import sys
import numpy as np
import GOES_data_upload as GOES_data
import flare_conditions as fc

class RealTimeTrigger(QtWidgets.QMainWindow):
    
    print_updates=False #prints more updated in terminal. Only suggested for real-time data.
    ms_timing = 200 #amount of ms between each new data download.
    
    TRIGGER_WINDOW = 4 
    TRIGGER_TO_LAUNCH = TRIGGER_WINDOW + 3
    TRIGGER_TO_FOXSI_OBS_START = TRIGGER_TO_LAUNCH + 2
    TRIGGER_TO_FOXSI_OBS_END = TRIGGER_TO_FOXSI_OBS_START + 6
    TRIGGER_TO_HIC_OBS_START = TRIGGER_TO_FOXSI_OBS_START + 2
    TRIGGER_TO_HIC_OBS_END = TRIGGER_TO_HIC_OBS_START + 6
    DEADTIME = 30
    
    def __init__(self, data, summary_filename, xrsa_filename, xrsb_filename):
        
        #defining data:
        self.XRS_data = data
        self.summary_filename = summary_filename
        self.xrsa_filename = xrsa_filename
        self.xrsb_filename = xrsb_filename
        
        #defining XRS variables: 
        self.xrsa_current = None #newly reloaded data
        self.xrsa = None #total data (aggregated during entire run time)
        self.xrsb_current = None
        self.xrsb = None
        self.current_time = None #most recent time of data
        self.current_realtime = None #current realtime- accounts for 3 minute latency
        
        #defining flare state 
        self.flare_prediction_state = "searching"
        self.flare_happening = False
        self.launch = False
        self.post_launch = False
        
        self.flare_summary = pd.DataFrame(columns=['Trigger','Realtime Trigger', 'Flare End', 'Launch', 'FOXSI Obs Start', 'FOXSI Obs End', 'HiC Obs Start', 'HiC Obs End'])
        self.flare_summary_index = -1
        
        #initial loading of the data: 
        self.load_data(reload=False)
        
        #initial plotting of data: 
        #initializing plot: 
        super().__init__()
        self.graphWidget = pg.PlotWidget(axisItems={'bottom': pg.DateAxisItem()})
        self.setCentralWidget(self.graphWidget)
        
        self.graphWidget.setBackground('w')
        styles = {'color':'k', 'font-size':'20pt'} 
        self.graphWidget.setLabel('left', 'W m<sup>-2</sup>', **styles)
        self.graphWidget.setLabel('bottom', 'Time', **styles)
        self.graphWidget.setTitle(f'GOES XRS Real-Time: {self.flare_prediction_state}', color='k', size='24pt')
        self.graphWidget.addLegend()
        self.graphWidget.showGrid(x=True, y=True)
        #self.graphWidget.setYRange(1e-9, 1e-2, padding=0)
        self.graphWidget.setLogMode(y=True)
        
        time_tags = [pd.Timestamp(date).timestamp() for date in self.xrsb['time_tag']]
        self.xrsb_data = self.plot(time_tags, np.array(self.xrsb['flux']), color='r', plotname='GOES XRSB')
        self.xrsa_data = self.plot(time_tags, np.array(self.xrsa['flux']), color='b', plotname='GOES XRSA')
        
        #initializing trigger and observation plotting:
        self.flare_trigger_plot = self.plot([time_tags[0]]*2, [1e-9, 1e-3], color='gray', plotname='Data Trigger')
        self.flare_trigger_plot.setAlpha(0, False)
        self.flare_realtrigger_plot = self.plot([time_tags[0]]*2, [1e-9, 1e-3], color='k', plotname='Actual time of Trigger')
        self.flare_realtrigger_plot.setAlpha(0, False)
        self.FOXSI_launch_plot = self.plot([time_tags[0]]*2, [1e-9, 1e-3], color='green', plotname='FOXSI Launch')
        self.FOXSI_launch_plot.setAlpha(0, False)
        self.HIC_launch_plot = self.plot([time_tags[0]]*2, [1e-9, 1e-3], color='orange', plotname='HIC Launch')
        self.HIC_launch_plot.setAlpha(0, False)
        
        #updating data
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.ms_timing)
        self.timer.timeout.connect(self.update)
        self.timer.start()
      
    ########################### STATE FUNCTIONS ######################################  
    def change_to_searching_state(self):
        self.flare_prediction_state = "searching"
        self.flare_happening = False
        
    def change_to_triggered_state(self):
        self.flare_prediction_state = "triggered"
        self.flare_happening = True
        self.flare_summary_index += 1
        
    def change_to_pre_launch_state(self):
        self.flare_prediction_state = "pre-launch"
        
    def change_to_launched_state(self):
        self.flare_prediction_state = "launched"
        
    def change_to_post_launch_state(self):
        self.flare_prediction_state = "post-launch"
   ####################################################################################
     
    def plot(self, x, y, color, plotname):
       pen = pg.mkPen(color=color, width=5)
       return self.graphWidget.plot(x, y, name=plotname, pen=pen)
       
    def load_data(self, reload=True):
        if self.print_updates: print('Loading Data')
        self.xrsa_current, self.xrsb_current = self.XRS_data()
        self.current_time = list(self.xrsa_current['time_tag'])[-1]
        self.current_realtime = self.current_time + pd.Timedelta(3, unit='minutes') #to account for latency
        if not reload:
            self.xrsa = self.xrsa_current
            self.xrsb = self.xrsb_current
            
    def check_for_new_data(self):
        previous_time = list(self.xrsa['time_tag'])[-1]
        new_minutes = pd.Timedelta(self.current_time - previous_time).seconds/60.0
        self.new_data = False
        if new_minutes > 0: 
            self.xrsa = self.xrsa._append(self.xrsa_current.iloc[-int(new_minutes)], ignore_index=True)
            self.xrsb = self.xrsb._append(self.xrsb_current.iloc[-int(new_minutes)], ignore_index=True)
            self.new_data = True
            if self.print_updates: print(f'{new_minutes} new minute(s) of data: most recent data from {self.current_time}')
            if self.print_updates and new_minutes > 1: print('More than one minute added! Check internet connection.')
            
    def check_for_trigger(self):
        if fc.flare_trigger_condition(xrsa_data=self.xrsa, xrsb_data=self.xrsb):
            self.change_to_triggered_state()
            self.flare_summary.loc[self.flare_summary_index, 'Trigger'] = self.current_time
            self.flare_summary.loc[self.flare_summary_index, 'Realtime Trigger'] = self.current_realtime
            print(f'FLARE TRIGGERED on {self.current_time} flux, at {self.current_realtime} UTC.')
        else:
            if self.print_updates: print(f'Still searching for flare')
        
    def check_for_flare_end(self):
        if fc.flare_end_condition(xrsa_data=self.xrsa, xrsb_data=self.xrsb):
            self.flare_summary.loc[self.flare_summary_index, 'Flare End'] = self.current_time
            if self.flare_prediction_state == "triggered":
                self.change_to_searching_state()
                print(f'Flare ended at {self.current_time}. DO NOT LAUNCH! Searching for another flare.')
            elif self.flare_prediction_state == "pre-launch":
                self.flare_happening = False
                self.change_to_post_launch_state()
                print(f'Flare ended during pre-launch window at {self.current_time}. HOLD LAUNCH!! Entering post-launch deadtime.')
            elif self.flare_prediction_state == "launched":
                self.flare_happening = False
                print(f'Flare ended during observation at {self.current_time}.')
            
             
    def check_for_pre_launch(self):
        self.trigger_to_current_time = int(pd.Timedelta(pd.Timestamp(self.current_realtime) - self.flare_summary['Realtime Trigger'].iloc[-1]).seconds/60.0)
        if self.trigger_to_current_time == self.TRIGGER_WINDOW: 
            print(f'Beginning 3-minute pre-launch window at {self.current_realtime}')
            self.change_to_pre_launch_state()
             
    def check_for_launch(self):
        self.trigger_to_current_time = int(pd.Timedelta(pd.Timestamp(self.current_realtime) - self.flare_summary['Realtime Trigger'].iloc[-1]).seconds/60.0)
        if self.trigger_to_current_time == self.TRIGGER_TO_LAUNCH and self.flare_prediction_state == "pre-launch":
            self.change_to_launched_state()
            self.save_observation_times()
            print(f'Launching FOXSI at {self.current_realtime}')
                  
    def save_observation_times(self):
        foxsi_obs_start = self.flare_summary['Realtime Trigger'].iloc[-1] + pd.Timedelta(self.TRIGGER_TO_FOXSI_OBS_START, unit='minutes')
        foxsi_obs_end = self.flare_summary['Realtime Trigger'].iloc[-1] + pd.Timedelta(self.TRIGGER_TO_FOXSI_OBS_END, unit='minutes')
        hic_obs_start = self.flare_summary['Realtime Trigger'].iloc[-1] + pd.Timedelta(self.TRIGGER_TO_HIC_OBS_START, unit='minutes')
        hic_obs_end = self.flare_summary['Realtime Trigger'].iloc[-1] + pd.Timedelta(self.TRIGGER_TO_HIC_OBS_END, unit='minutes')
        self.flare_summary.loc[self.flare_summary_index, 'Launch'] = self.current_realtime
        self.flare_summary.loc[self.flare_summary_index, 'FOXSI Obs Start'] = foxsi_obs_start
        self.flare_summary.loc[self.flare_summary_index, 'FOXSI Obs End'] = foxsi_obs_end
        self.flare_summary.loc[self.flare_summary_index, 'HiC Obs Start'] = hic_obs_start
        self.flare_summary.loc[self.flare_summary_index, 'HiC Obs End'] = hic_obs_end
        
    def provide_launch_updates(self):
        if self.current_realtime == self.flare_summary['FOXSI Obs Start'].iloc[-1]:
            print(f'Beginning FOXSI Observation at {self.current_realtime}')
        if self.current_realtime == self.flare_summary['FOXSI Obs End'].iloc[-1]:
            print(f'FOXSI Observation complete at {self.current_realtime}')
        if self.current_realtime == self.flare_summary['HiC Obs Start'].iloc[-1]:
            print(f'Beginning HiC Observation at {self.current_realtime}')
        if self.current_realtime == self.flare_summary['HiC Obs End'].iloc[-1]:
            print(f'HiC Observation complete at {self.current_realtime}')
            
    def check_for_post_launch(self):
        if self.current_realtime == self.flare_summary['HiC Obs End'].iloc[-1]:
            self.change_to_post_launch_state()
            print('Entering post-observation deadtime.')
            
    def check_for_search_again(self):
        if self.current_realtime == self.flare_summary['HiC Obs End'].iloc[-1] + pd.Timedelta(self.DEADTIME, unit='minutes'): 
            if self.flare_happening:
                self.flare_summary.loc[self.flare_summary_index, 'Flare End'] = self.current_time
                print(f'Flare end condition not met within post-launch window. Setting flare end time to most recent data: {self.current_time}.')
            self.change_to_searching_state()
            print(f'Ready to look for another flare at {self.current_realtime}!')
        elif pd.isnull(self.flare_summary['HiC Obs End'].iloc[-1]) and self.current_realtime == self.flare_summary['Flare End'].iloc[-1] + pd.Timedelta(self.DEADTIME, unit='minutes'):
            self.change_to_searching_state()
            print(f'Ready to look for another flare at {self.current_realtime}! {self.flare_happening}')
            
            
    def update(self):
        self.load_data()
        self.check_for_new_data()
        if self.new_data:
            print(self.flare_happening)
            self.xrs_plot_update()
            if self.flare_happening: 
                self.check_for_flare_end()
            if self.flare_prediction_state == "searching":
                self.check_for_trigger()
            elif self.flare_prediction_state == "triggered":
                self.check_for_pre_launch()
            elif self.flare_prediction_state == "pre-launch":
                self.check_for_launch()
            elif self.flare_prediction_state == "launched":
                self.provide_launch_updates()
                self.check_for_post_launch()
            elif self.flare_prediction_state == "post-launch":
                self.check_for_search_again()
            self.update_trigger_plot()
            self.update_launch_plots()
            self.save_data()
            
    def xrs_plot_update(self):
        if self.xrsa.shape[0]>30:
            self.new_time_tags = [pd.Timestamp(date).timestamp() for date in self.xrsb.iloc[-30:]['time_tag']]
            self.new_xrsa = np.array(self.xrsa.iloc[-30:]['flux'])
            self.new_xrsb = np.array(self.xrsb.iloc[-30:]['flux'])
            self.xrsa_data.setData(self.new_time_tags, self.new_xrsa)
            self.xrsb_data.setData(self.new_time_tags, self.new_xrsb)
        else: 
            self.new_time_tags = [pd.Timestamp(date).timestamp() for date in self.xrsb['time_tag']]
            self.new_xrsa = np.array(self.xrsa['flux'])
            self.new_xrsb = np.array(self.xrsb['flux'])
            self.xrsa_data.setData(self.new_time_tags, self.new_xrsa)
            self.xrsb_data.setData(self.new_time_tags, self.new_xrsb)   
        self.graphWidget.setTitle(f'GOES XRS Testing \n State: {self.flare_prediction_state}') 
        
    def update_trigger_plot(self): 
        if not self.flare_summary.shape[0]==0:
            if self.current_time == self.flare_summary['Trigger'].iloc[-1]:
                self.flare_trigger_plot.setData([pd.Timestamp(self.flare_summary['Trigger'].iloc[-1]).timestamp()]*2, [1e-9, 1e-3])
                self.flare_trigger_plot.setAlpha(1, False)
            if self.current_time == self.flare_summary['Realtime Trigger'].iloc[-1]:
                self.flare_realtrigger_plot.setData([pd.Timestamp(self.flare_summary['Realtime Trigger'].iloc[-1]).timestamp()]*2, [1e-9, 1e-3])
                self.flare_realtrigger_plot.setAlpha(1, False)
            if self.flare_summary['Trigger'].iloc[-1] not in list(self.xrsb['time_tag'].iloc[-30:]):
                self.flare_trigger_plot.setData([self.new_time_tags[0]]*2, [1e-9, 1e-3])
                self.flare_trigger_plot.setAlpha(0, False)
            if self.flare_summary['Realtime Trigger'].iloc[-1] not in list(self.xrsb['time_tag'].iloc[-30:]):
                self.flare_realtrigger_plot.setData([self.new_time_tags[0]]*2, [1e-9, 1e-3])
                self.flare_realtrigger_plot.setAlpha(0, False)
            
    def update_launch_plots(self):
        if not self.flare_summary.shape[0] == 0:
            #setting launch lines to the right time
            if self.current_time == self.flare_summary['Launch'].iloc[-1]:
                self.FOXSI_launch_plot.setData([pd.Timestamp(self.flare_summary['Launch'].iloc[-1]).timestamp()]*2, [1e-9, 1e-3])
                self.FOXSI_launch_plot.setAlpha(1, False)
            if self.current_time == self.flare_summary['FOXSI Obs Start'].iloc[-1]:
                self.HIC_launch_plot.setData([pd.Timestamp(self.flare_summary['FOXSI Obs Start'].iloc[-1]).timestamp()]*2, [1e-9, 1e-3])
                self.HIC_launch_plot.setAlpha(1, False)
            #removing launch lines when they are out of range
            if self.flare_summary['Launch'].iloc[-1] not in list(self.xrsb['time_tag'].iloc[-30:]):
                self.FOXSI_launch_plot.setData([self.new_time_tags[0]]*2, [1e-9, 1e-3])
                self.FOXSI_launch_plot.setAlpha(0, False)
            if self.flare_summary['FOXSI Obs Start'].iloc[-1] not in list(self.xrsb['time_tag'].iloc[-30:]):
                self.HIC_launch_plot.setData([self.new_time_tags[0]]*2, [1e-9, 1e-3])
                self.HIC_launch_plot.setAlpha(0, False)    
        
    def save_data(self):
        self.flare_summary.to_csv(f'ObservationSummary/{self.summary_filename}')
        self.xrsa.to_csv('ObservationSummary/{self.xrsa_filename}')
        self.xrsb.to_csv('ObservationSummary/{self.xrsb_filename}')
        
            
def main(historical=False):
    ''' Runs the RealTimeTrigger algorithm. To utilize the historical GOES 3-day dataset, state historical=True.
    Otherwise, real-time data will be downloaded from NOAA.'''
    app = QtWidgets.QApplication(sys.argv)
    if historical: 
        historical_data = GOES_data.FakeDataUpdator(GOES_data.historical_GOES_XRS)
        main = RealTimeTrigger(historical_data.append_new_data, 'historical_summary.csv', 'GOES_XRSA.csv', 'GOES_XRSB.csv')
    else:     
        main = RealTimeTrigger(load_realtime_XRS, 'realtime_summary.csv', 'GOES_XRSA.csv', 'GOES_XRSB.csv')
    main.show()
    sys.exit(app.exec()) 
if __name__ == '__main__':
    main(historical=True)
        
	