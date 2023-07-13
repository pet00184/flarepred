import pandas as pd
from PyQt6 import QtWidgets, QtCore
import PyQt6
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
import sys
import os
import numpy as np
import GOES_data_upload as GOES_data
import flare_conditions as fc

PACKAGE_DIR = os.path.dirname(os.path.realpath(__file__))

class RealTimeTrigger(QtWidgets.QWidget):
    
    print_updates=False #prints more updated in terminal. Only suggested for real-time data.
    ms_timing = 5000#200 #amount of ms between each new data download.
    
    #TRIGGER_WINDOW = 4 
    PRE_LAUNCH_WINDOW = 3
    LAUNCH_INIT_TO_FOXSI_OBS_START = PRE_LAUNCH_WINDOW + 2
    LAUNCH_INIT_TO_FOXSI_OBS_END = LAUNCH_INIT_TO_FOXSI_OBS_START + 6
    LAUNCH_INIT_TO_HIC_OBS_START = LAUNCH_INIT_TO_FOXSI_OBS_START + 2
    LAUNCH_INIT_TO_HIC_OBS_END = LAUNCH_INIT_TO_HIC_OBS_START + 6
    DEADTIME = 30
    
    # need to be class variable to connect
    value_changed_signal_status = QtCore.pyqtSignal()
    value_changed_new_xrsb = QtCore.pyqtSignal()

    def __init__(self, data, foldername, parent=None):
        QtWidgets.QWidget.__init__(self,parent)
        
        #making folder to store summary data:
        # if not os.path.exists(f"{PACKAGE_DIR/SessionSummaries}"):
#             os.mkdir(f"{PACKAGE_DIR/SessionSummaries}")
            
        if not os.path.exists(f"{PACKAGE_DIR}/SessionSummaries/{foldername}"):
            os.makedirs(f"{PACKAGE_DIR}/SessionSummaries/{foldername}")
            
        #defining data:
        self.XRS_data = data
        # self.summary_filename = summary_filename
#         self.xrsa_filename = xrsa_filename
#         self.xrsb_filename = xrsb_filename
        self.foldername = foldername
        
        #defining XRS variables: 
        self.xrsa_current = None #newly reloaded data
        self.xrsa = None #total data (aggregated during entire run time)
        self.xrsb_current = None
        self.xrsb = None
        self.current_time = None #most recent time of data
        self.current_realtime = None #current realtime- accounts for 3 minute latency
        
        #defining flare state 
        self.flare_prediction_state("searching")
        self.flare_happening = False
        self.launch = False
        self.post_launch = False
        
        self.flare_summary = pd.DataFrame(columns=['Trigger','Realtime Trigger', 'Flare End', 'Launch Initiated', 'Launch', 'FOXSI Obs Start', 'FOXSI Obs End', 'HiC Obs Start', 'HiC Obs End'])
        self.flare_summary_index = -1
        
        #initial loading of the data: 
        self.load_data(reload=False)
        
        #initial plotting of data: 
        #initializing plot: 
        self.layout = QtWidgets.QVBoxLayout()
        
        self.graphWidget = pg.PlotWidget(axisItems={'bottom': pg.DateAxisItem()})
        # self.setCentralWidget(self.graphWidget)
        self.layout.addWidget(self.graphWidget)
        self.setLayout(self.layout)

        # Disable interactivity
        self.graphWidget.setMouseEnabled(x=False, y=False)  # Disable mouse panning & zooming
        
        self.graphWidget.setBackground('w')
        styles = {'color':'k', 'font-size':'20pt'} 
        self.graphWidget.setLabel('left', 'W m<sup>-2</sup>', **styles)
        self.graphWidget.setLabel('bottom', 'Time', **styles)
        self.graphWidget.setTitle(f'GOES XRS Real-Time: {self._flare_prediction_state}', color='k', size='24pt')
        self.graphWidget.addLegend()
        self.graphWidget.showGrid(x=True, y=True)

        # convert left and right y-axes to display GOES notation stuff
        self._min_arr, self._max_arr = "xrsa", "xrsb" # give values to know what ylims are used
        self._lowest_yrange, self._highest_yrange = -8*1.02, -3*0.96
        self.display_goes()
        
        self.time_tags = [pd.Timestamp(date).timestamp() for date in self.xrsb['time_tag']]
        self.xrsb_data = self.plot(self.time_tags, np.array(self.xrsb['flux']), color='r', plotname='GOES XRSB')
        self.xrsa_data = self.plot(self.time_tags, np.array(self.xrsa['flux']), color='b', plotname='GOES XRSA')
        
        #initializing trigger and observation plotting:
        self.flare_trigger_plot = self.plot([self.time_tags[0]]*2, [1e-9, 1e-3], color='gray', plotname='Data Trigger')
        self.flare_trigger_plot.setAlpha(0, False)
        self.flare_realtrigger_plot = self.plot([self.time_tags[0]]*2, [1e-9, 1e-3], color='k', plotname='Actual time of Trigger')
        self.flare_realtrigger_plot.setAlpha(0, False)
        self.FOXSI_launch_plot = self.plot([self.time_tags[0]]*2, [1e-9, 1e-3], color='green', plotname='FOXSI Launch')
        self.FOXSI_launch_plot.setAlpha(0, False)
        self.HIC_launch_plot = self.plot([self.time_tags[0]]*2, [1e-9, 1e-3], color='orange', plotname='HIC Launch')
        self.HIC_launch_plot.setAlpha(0, False)
        
        #updating data
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.ms_timing)
        self.timer.timeout.connect(self._update)
        self.timer.start()

    def _goes_strings(self, cls, arng, append=""):
        """ GenerateGOES class strings."""
        return [cls+str(v)+append for v in arng]

    def display_goes(self):
        """ Method to add in the GOES class stuff"""
        
        log_value = np.arange(-10,-1) # get the letter class log-values
        value = 10**(log_value.astype(float)) # get the letter class values
        goes_labels = ["A0.01", "A0.1", "A1", "B1", "C1", "M1", "X1", "X10", "X100"]
        
        intermediate_classes = [1,2,4,6,8]
        num_of_int = [value[None,:] for _ in range(len(intermediate_classes))]
        value_ints = (np.vstack(num_of_int).T*np.array(intermediate_classes)).flatten() # now go letter class, half up, next letter class; e.g., A, A5, B, B5, etc.
        log_value_ints = np.log10(value_ints)
        
        goes_labels_ints = self._goes_strings("A0.0", arng=intermediate_classes)+\
                           self._goes_strings("A0.", arng=intermediate_classes)+\
                           self._goes_strings("A", arng=intermediate_classes)+\
                           self._goes_strings("B", arng=intermediate_classes)+\
                           self._goes_strings("C", arng=intermediate_classes)+\
                           self._goes_strings("M", arng=intermediate_classes)+\
                           self._goes_strings("X", arng=intermediate_classes)+\
                           self._goes_strings("X", arng=intermediate_classes, append="0")+\
                           self._goes_strings("A0.0", arng=intermediate_classes, append="00")

        # set the y-limits for the plot
        self.ylims()

        # do axis stuff, show top line and annotate right axis
        self.graphWidget.showAxis('top')
        self.graphWidget.getAxis('top').setStyle(showValues=False)
        self.graphWidget.getAxis('top').setGrid(False)
        self.graphWidget.showAxis('right')
        self.graphWidget.getAxis('right').setLabel('GOES Class')
        self.graphWidget.getAxis('right').setGrid(False)
        
        
        if self.upper-self.lower<=1.5:
            self.graphWidget.getAxis('right').setTicks([[(v, str(s)) for v,s in zip(log_value_ints,goes_labels_ints)]])
            self.graphWidget.getAxis('left').setTicks([[(v, f"{s:0.0e}") for v,s in zip(log_value_ints,value_ints)]])
        else:
            self.graphWidget.getAxis('right').setTicks([[(v, str(s)) for v,s in zip(log_value,goes_labels)]])
            self.graphWidget.getAxis('left').setTicks([[(v, f"{s:0.0e}") for v,s in zip(log_value,value)]])

    def ylims(self):
        """ 
        The ylims are:
            ymin = A-class or half an order of magnitude below the min. of `self._min_arr`.
            ymax = X10-class or half an order of magnitude above the max. of `self._max_arr`.

        The ylims are, by DEFAULT:
            ymin = A-class or half an order of magnitude below the min. of XRSA.
            ymax = X10-class or half an order of magnitude above the max. of XRSB.
        """
        _supported_arrays = ["xrsa", "xrsb"]
        if (self._min_arr not in _supported_arrays) or (self._max_arr not in _supported_arrays):
            print(f"self._min_arr={self._min_arr} or self._max_arr={self._max_arr} not in _supported_arrays={_supported_arrays}.")
            return
        
        # make sure arrays are the most recent
        _min_arr = getattr(self,"new_"+self._min_arr) if hasattr(self, "new_"+self._min_arr) else getattr(self,self._min_arr)["flux"]
        _max_arr = getattr(self,"new_"+self._max_arr) if hasattr(self, "new_"+self._max_arr) else getattr(self,self._max_arr)["flux"]

        # define, in log space, the top and bottom y-margin for the plotting
        _ymargin = 0.25

        # depend plotting on lowest ~A1 (slightly less to make sure tick plots)
        self.lower = np.max([self._lowest_yrange, np.log10(np.min(_min_arr))-_ymargin]) # *1.02 to make sure lower tick for -8 actually appears if needed
        # on 200x largest xsrb value to look sensible and scale with new data
        self.upper = np.min([np.log10(np.max(_max_arr))+_ymargin, self._highest_yrange]) # *0.96 to make sure upper tick for -3 actually appears if needed
        self.graphWidget.plotItem.vb.setLimits(yMin=self.lower, yMax=self.upper)
        self.graphWidget.plot() # update the plot with the new ylims

    def flare_prediction_state(self, state):
        self._flare_prediction_state = state
        self.value_changed_signal_status.emit()
      
    ########################### STATE FUNCTIONS ######################################  
    def change_to_searching_state(self):
        self.flare_prediction_state("searching")
        self.flare_happening = False
        
    def change_to_triggered_state(self):
        self.flare_prediction_state("triggered")
        self.flare_happening = True
        self.flare_summary_index += 1
        
    def change_to_pre_launch_state(self):
        self.flare_prediction_state("pre-launch")
        
    def change_to_launched_state(self):
        self.flare_prediction_state("launched")
        
    def change_to_post_launch_state(self):
        self.flare_prediction_state("post-launch")
   ####################################################################################
     
    def plot(self, x, y, color, plotname):
       pen = pg.mkPen(color=color, width=5)
       return self.graphWidget.plot(x, np.log10(y), name=plotname, pen=pen)
       
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

            # make sure the y-limits change with the plot if needed and alert that new data is added
            self.ylims()
            self.value_changed_new_xrsb.emit()
            
    def check_for_trigger(self):
        if fc.flare_trigger_condition(xrsa_data=self.xrsa, xrsb_data=self.xrsb):
            self.change_to_triggered_state()
            self.flare_summary.loc[self.flare_summary_index, 'Trigger'] = self.current_time
            self.flare_summary.loc[self.flare_summary_index, 'Realtime Trigger'] = self.current_realtime
            print(f'FLARE TRIGGERED on {self.current_time} flux, at {self.current_realtime} UTC.')
        else:
            if self.print_updates: print('Still searching for flare')
        
    def check_for_flare_end(self):
        if fc.flare_end_condition(xrsa_data=self.xrsa, xrsb_data=self.xrsb):
            self.flare_summary.loc[self.flare_summary_index, 'Flare End'] = self.current_time
            if self._flare_prediction_state == "triggered":
                self.change_to_searching_state()
                print(f'Flare ended at {self.current_time}. DO NOT LAUNCH! Searching for another flare.')
            # elif self._flare_prediction_state == "pre-launch":
            #     self.flare_happening = False
            #     self.change_to_post_launch_state()
            #     print(f'Flare ended during pre-launch window at {self.current_time}. HOLD LAUNCH!! Entering post-launch deadtime.')
            elif self._flare_prediction_state == "launched":
                self.flare_happening = False
                print(f'Flare ended during observation at {self.current_time}.')
            
             
    def check_for_pre_launch(self):
        self.trigger_to_current_time = int(pd.Timedelta(pd.Timestamp(self.current_realtime) - self.flare_summary['Realtime Trigger'].iloc[-1]).seconds/60.0)
        if self.trigger_to_current_time == self.TRIGGER_WINDOW: 
            print(f'Beginning 3-minute pre-launch window at {self.current_realtime}')
            # self.change_to_pre_launch_state()

    def _button_press_pre_launch(self):
        self.change_to_pre_launch_state()
        self.flare_summary.loc[self.flare_summary_index, "Launch Initiated"] = self.current_realtime
             
    def check_for_launch(self):
        self.trigger_to_current_time = int(pd.Timedelta(pd.Timestamp(self.current_realtime) - self.flare_summary['Launch Initiated'].iloc[-1]).seconds/60.0)
        if self.trigger_to_current_time == self.PRE_LAUNCH_WINDOW and self._flare_prediction_state == "pre-launch":
            self.change_to_launched_state()
            self.save_observation_times()
            print(f'Launching FOXSI at {self.current_realtime}')
                  
    def save_observation_times(self):
        foxsi_obs_start = self.flare_summary['Launch Initiated'].iloc[-1] + pd.Timedelta(self.LAUNCH_INIT_TO_FOXSI_OBS_START, unit='minutes')
        foxsi_obs_end = self.flare_summary['Launch Initiated'].iloc[-1] + pd.Timedelta(self.LAUNCH_INIT_TO_FOXSI_OBS_END, unit='minutes')
        hic_obs_start = self.flare_summary['Launch Initiated'].iloc[-1] + pd.Timedelta(self.LAUNCH_INIT_TO_HIC_OBS_START, unit='minutes')
        hic_obs_end = self.flare_summary['Launch Initiated'].iloc[-1] + pd.Timedelta(self.LAUNCH_INIT_TO_HIC_OBS_END, unit='minutes')
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
        elif pd.isnull(self.flare_summary['HiC Obs End'].iloc[-1]) and self.current_realtime == self.flare_summary['Realtime Trigger'].iloc[-1] + pd.Timedelta(self.DEADTIME, unit='minutes'):
            self.change_to_searching_state()
            print(f'Ready to look for another flare at {self.current_realtime}! {self.flare_happening}')
            
            
    def _update(self):
        self.load_data()
        self.check_for_new_data()
        self.graphWidget.setTitle(f'GOES XRS Testing Status: {self._flare_prediction_state}') 
        if self.new_data:
            self.xrs_plot_update()
            if self.flare_happening: 
                self.check_for_flare_end()
            if self._flare_prediction_state == "searching":
                self.check_for_trigger()
            elif self._flare_prediction_state == "triggered":
                # self.check_for_pre_launch()
                pass
            elif self._flare_prediction_state == "pre-launch":
                self.check_for_launch()
            elif self._flare_prediction_state == "launched":
                self.provide_launch_updates()
                self.check_for_post_launch()
            elif self._flare_prediction_state == "post-launch":
                self.check_for_search_again()
            self.update_trigger_plot()
            self.update_launch_plots()
            self.save_data()
            
    def xrs_plot_update(self):
        
        if self.xrsa.shape[0]>30:
            self.new_time_tags = [pd.Timestamp(date).timestamp() for date in self.xrsb.iloc[-30:]['time_tag']]
            self.new_xrsa = np.array(self.xrsa.iloc[-30:]['flux'])
            self.new_xrsb = np.array(self.xrsb.iloc[-30:]['flux'])
            self.ylims()
            self.xrsa_data.setData(self.new_time_tags, np.log10(self.new_xrsa))
            self.xrsb_data.setData(self.new_time_tags, np.log10(self.new_xrsb))
        else: 
            self.new_time_tags = [pd.Timestamp(date).timestamp() for date in self.xrsb['time_tag']]
            self.new_xrsa = np.array(self.xrsa['flux'])
            self.new_xrsb = np.array(self.xrsb['flux'])
            self.ylims()
            self.xrsa_data.setData(self.new_time_tags, np.log10(self.new_xrsa))
            self.xrsb_data.setData(self.new_time_tags, np.log10(self.new_xrsb))   
        #self.graphWidget.setTitle(f'GOES XRS Testing \n State: {self._flare_prediction_state}') 
        
        
    def update_trigger_plot(self): 
        if not self.flare_summary.shape[0]==0:
            if self.flare_summary['Trigger'].iloc[-1] in list(self.xrsb['time_tag'].iloc[-30:]):
                self.flare_trigger_plot.setData([pd.Timestamp(self.flare_summary['Trigger'].iloc[-1]).timestamp()]*2, [self._lowest_yrange, self._highest_yrange])
                self.flare_trigger_plot.setAlpha(1, False)
            if self.flare_summary['Realtime Trigger'].iloc[-1] in list(self.xrsb['time_tag'].iloc[-30:]):
                self.flare_realtrigger_plot.setData([pd.Timestamp(self.flare_summary['Realtime Trigger'].iloc[-1]).timestamp()]*2, [self._lowest_yrange, self._highest_yrange])
                self.flare_realtrigger_plot.setAlpha(1, False)
            if self.flare_summary['Trigger'].iloc[-1] not in list(self.xrsb['time_tag'].iloc[-30:]):
                self.flare_trigger_plot.setData([self.new_time_tags[0]]*2, [self._lowest_yrange, self._highest_yrange])
                self.flare_trigger_plot.setAlpha(0, False)
            if self.flare_summary['Realtime Trigger'].iloc[-1] not in list(self.xrsb['time_tag'].iloc[-30:]):
                self.flare_realtrigger_plot.setData([self.new_time_tags[0]]*2, [self._lowest_yrange, self._highest_yrange])
                self.flare_realtrigger_plot.setAlpha(0, False)
        else:
            self.flare_trigger_plot.setData([self.new_time_tags[0]]*2, [self._lowest_yrange, self._highest_yrange])
            self.flare_trigger_plot.setAlpha(0, False)
            self.flare_realtrigger_plot.setData([self.new_time_tags[0]]*2, [self._lowest_yrange, self._highest_yrange])
            self.flare_realtrigger_plot.setAlpha(0, False)
            
    def update_launch_plots(self):
        if not self.flare_summary.shape[0] == 0:
            #setting launch lines to the right time
            if self.flare_summary['Launch'].iloc[-1] in list(self.xrsb['time_tag'].iloc[-30:]):
                self.FOXSI_launch_plot.setData([pd.Timestamp(self.flare_summary['Launch'].iloc[-1]).timestamp()]*2, [self._lowest_yrange, self._highest_yrange])
                self.FOXSI_launch_plot.setAlpha(1, False)
            if self.flare_summary['FOXSI Obs Start'].iloc[-1] in list(self.xrsb['time_tag'].iloc[-30:]):
                self.HIC_launch_plot.setData([pd.Timestamp(self.flare_summary['FOXSI Obs Start'].iloc[-1]).timestamp()]*2, [self._lowest_yrange, self._highest_yrange])
                self.HIC_launch_plot.setAlpha(1, False)
            #removing launch lines when they are out of range
            if self.flare_summary['Launch'].iloc[-1] not in list(self.xrsb['time_tag'].iloc[-30:]):
                self.FOXSI_launch_plot.setData([self.new_time_tags[0]]*2, [self._lowest_yrange, self._highest_yrange])
                self.FOXSI_launch_plot.setAlpha(0, False)
            if self.flare_summary['FOXSI Obs Start'].iloc[-1] not in list(self.xrsb['time_tag'].iloc[-30:]):
                self.HIC_launch_plot.setData([self.new_time_tags[0]]*2, [self._lowest_yrange, self._highest_yrange])
                self.HIC_launch_plot.setAlpha(0, False)  
        else:
              self.FOXSI_launch_plot.setData([self.new_time_tags[0]]*2, [self._lowest_yrange, self._highest_yrange])
              self.FOXSI_launch_plot.setAlpha(0, False)
              self.HIC_launch_plot.setData([self.new_time_tags[0]]*2, [self._lowest_yrange, self._highest_yrange])
              self.HIC_launch_plot.setAlpha(0, False)
        
    def save_data(self):
        self.flare_summary.to_csv(f'{PACKAGE_DIR}/SessionSummaries/{self.foldername}/timetag_summary.csv')
        self.xrsa.to_csv(f'{PACKAGE_DIR}/SessionSummaries/{self.foldername}/GOES_XRSA.csv')
        self.xrsb.to_csv(f'{PACKAGE_DIR}/SessionSummaries/{self.foldername}/GOES_XRSB.csv')
        
            
        
	