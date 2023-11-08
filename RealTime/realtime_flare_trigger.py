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
from datetime import datetime, timedelta, timezone

PACKAGE_DIR = os.path.dirname(os.path.realpath(__file__))

class RealTimeTrigger(QtWidgets.QWidget):
    
    print_updates=False #prints more updated in terminal. Only suggested for real-time data.
    ms_timing = 2000 #amount of ms between each new data download.
    
    # old constant TRIGGER_WINDOW = 4 
    PRE_LAUNCH_WINDOW = 3
    LAUNCH_INIT_TO_FOXSI_OBS_START = PRE_LAUNCH_WINDOW + 2
    LAUNCH_INIT_TO_FOXSI_OBS_END = LAUNCH_INIT_TO_FOXSI_OBS_START + 6
    LAUNCH_INIT_TO_HIC_OBS_START = LAUNCH_INIT_TO_FOXSI_OBS_START + 2
    LAUNCH_INIT_TO_HIC_OBS_END = LAUNCH_INIT_TO_HIC_OBS_START + 6
    DEADTIME = 30
    
    # need to be class variable to connect
    value_changed_signal_status = QtCore.pyqtSignal()
    value_changed_new_xrsb = QtCore.pyqtSignal()
    value_changed_alerts = QtCore.pyqtSignal()

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
        styles = {'color':'k', 'font-size':'20pt', "units":None} 
        self.graphWidget.setLabel('left', 'W m<sup>-2</sup>', **styles)
        self.graphWidget.setLabel('bottom', 'Time', **styles)
        self.graphWidget.setTitle(f'GOES XRS Real-Time: {self._flare_prediction_state}', color='k', size='24pt')
        self.graphWidget.addLegend()
        self.graphWidget.showGrid(x=True, y=True)
        self.graphWidget.getAxis('left').enableAutoSIPrefix(enable=False)

        # convert left and right y-axes to display GOES notation stuff
        self._min_arr, self._max_arr = "xrsa", "xrsb" # give values to know what ylims are used
        self._logy = True
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

        # alerts *** DO NOT forget to end both tuples with `,`
        # add new alerts to `update_flare_alerts()` as well
        self.flare_alert_names = tuple(fc.FLARE_ALERT_MAP.keys())
        self.flare_alerts = pd.DataFrame(data={n:[False] for n in self.flare_alert_names}, index=["states"])
        
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
        
        intermediate_classes = [1,2,3,4,5,6,7,8,9]
        num_of_int = [value[None,:] for _ in range(len(intermediate_classes))]
        value_ints = (np.vstack(num_of_int).T*np.array(intermediate_classes)).flatten() # now go letter class, half up, next letter class; e.g., A, A5, B, B5, etc.
        log_value_ints = self._log_data(value_ints)
        
        goes_labels_ints = self._goes_strings("A0.0", arng=intermediate_classes)+\
                           self._goes_strings("A0.", arng=intermediate_classes)+\
                           self._goes_strings("A", arng=intermediate_classes)+\
                           self._goes_strings("B", arng=intermediate_classes)+\
                           self._goes_strings("C", arng=intermediate_classes)+\
                           self._goes_strings("M", arng=intermediate_classes)+\
                           self._goes_strings("X", arng=intermediate_classes)+\
                           self._goes_strings("X", arng=intermediate_classes, append="0")+\
                           self._goes_strings("X", arng=intermediate_classes, append="00")

        # set the y-limits for the plot
        self.ylims()

        # do axis stuff, show top line and annotate right axis
        self.graphWidget.showAxis('top')
        self.graphWidget.getAxis('top').setStyle(showValues=False)
        self.graphWidget.getAxis('top').setGrid(False)
        self.graphWidget.showAxis('right')
        self.graphWidget.getAxis('right').setLabel('GOES Class')
        self.graphWidget.getAxis('right').setGrid(False)
        self.graphWidget.getAxis('right').enableAutoSIPrefix(enable=False)

        keep_intermediate_classes = self.ticks_display()

        goes_labels_ints_keep = self._keep_goes_intermediate(intermediate_classes=intermediate_classes, classes_to_keep=keep_intermediate_classes)
        goes_value_ints_keep = log_value_ints[goes_labels_ints_keep]

        if self._logy:
            self.graphWidget.getAxis('right').setTicks([[(v, str(s)) if (v in goes_value_ints_keep) else (v,"") for v,s in zip(log_value_ints,goes_labels_ints)]])
            self.graphWidget.getAxis('left').setTicks([[(v, f"{s:0.0e}") if (v in goes_value_ints_keep) else (v,"") for v,s in zip(log_value_ints,value_ints)]])
        else: 
            self.graphWidget.getAxis('right').setTicks([[(v, str(s)) if (v in goes_value_ints_keep) else (v,"") for v,s in zip(value_ints,goes_labels_ints)]])
            self.graphWidget.getAxis('left').setTicks([[(v, f"{s:0.0e}") if (v in goes_value_ints_keep) else (v,"") for v,s in zip(value_ints,value_ints)]])

    def ticks_display(self):
        """ Chooses which ticks to display for certain y-ranges. """
        _max_arr = getattr(self,"new_"+self._max_arr) if hasattr(self, "new_"+self._max_arr) else getattr(self,self._max_arr)["flux"]
        _a = 1.1 if self._logy else np.nanmax(_max_arr[np.isfinite(_max_arr)])*0.9
        _b = 2.1 if self._logy else np.nanmax(_max_arr[np.isfinite(_max_arr)])*1.5

        if (self.upper-self.lower)<=_a:
            keep_intermediate_classes = [1,2,3,4,5,6,7,8,9]
        elif _a<(self.upper-self.lower)<=_b:
            keep_intermediate_classes = [1,2,4,6,8]
        else:
            keep_intermediate_classes = [1]
        return keep_intermediate_classes

    def _keep_goes_intermediate(self, intermediate_classes, classes_to_keep):
        """ Work out which intermediate GOES class to plot the tick labels for. """
        return [(np.array(classes_to_keep)-1)+i*len(intermediate_classes) for i in range(9)]

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
        _ymargin = 0.25 if self._logy else np.nanmin(_min_arr[np.isfinite(_min_arr)])

        # depend plotting on lowest ~A1 (slightly less to make sure tick plots)
        _lyr = self._lowest_yrange if self._logy else 10**self._lowest_yrange
        self.lower = np.nanmax([_lyr, self._log_data(np.nanmin(_min_arr[np.isfinite(_min_arr)]))-_ymargin]) # *1.02 to make sure lower tick for -8 actually appears if needed
        # on 200x largest xsrb value to look sensible and scale with new data
        _hyr = self._highest_yrange if self._logy else 10**self._highest_yrange
        self.upper = np.nanmin([self._log_data(np.nanmax(_max_arr[np.isfinite(_max_arr)]))+_ymargin, _hyr]) # *0.96 to make sure upper tick for -3 actually appears if needed
        self.graphWidget.plotItem.vb.setLimits(yMin=self.lower, yMax=self.upper)
        self.graphWidget.plot() # update the plot with the new ylims

    def _log_data(self, array):
        """ Check if the data is to be logged with `self._logy`."""
        if self._logy:
            log = np.log10(array)
            return log
        return array

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
        return self.graphWidget.plot(x, self._log_data(y), name=plotname, pen=pen)
       
    def load_data(self, reload=True):
        if self.print_updates: print('Loading Data')
        self.xrsa_current, self.xrsb_current = self.XRS_data()
        self.current_time = list(self.xrsa_current['time_tag'])[-1]
        self.current_realtime = self.current_time + pd.Timedelta(3, unit='minutes') #to account for latency
        if not reload:
            self.xrsa = self.xrsa_current
            self.xrsb = self.xrsb_current
            
    def check_for_new_data(self):
        """ Check for new data and add to what is plotted. """
        self.new_data = False
        # get indices for any data that has a newer time than the newest plotted
        new_times = self.xrsa_current.iloc[:]['time_tag']>list(self.xrsa['time_tag'])[-1]
        # if there are >0 new data-points then append them to the plotting data
        if len(self.xrsa_current[new_times]['time_tag']) > 0: 
            self.xrsa = self.xrsa._append(self.xrsa_current[new_times], ignore_index=True)
            self.xrsb = self.xrsb._append(self.xrsb_current[new_times], ignore_index=True)
            self.new_data = True

            # make sure the y-limits change with the plot if needed and alert that new data is added
            self.display_goes()
            self.value_changed_new_xrsb.emit()

    def update_flare_alerts(self):  
        """ Function to update the alerts and emit a signal. """
        for a in self.flare_alert_names:
            self.flare_alerts.at['states', a] = fc.FLARE_ALERT_MAP[a](xrsa_data=self.xrsa, xrsb_data=self.xrsb)  
        self.value_changed_alerts.emit()
    
    def check_for_trigger(self):
        self.update_flare_alerts()
        if np.all(self.flare_alerts.loc['states']):
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
        if not hasattr(self,"coming_launch_time"):
            self.coming_launch_time = self._get_current_time()+timedelta(minutes=self.PRE_LAUNCH_WINDOW)
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
        self._launched = None
            
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
            
    def _get_current_time(self):
        """ Need to be able to redefine for historical data. """
        now_time = datetime.now(timezone.utc)
        if (now_time-self.current_realtime).seconds>(5*60):
            return self.current_realtime
        return now_time
            
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
            self.update()
            
    def xrs_plot_update(self):
        
        if self.xrsa.shape[0]>30:
            self.new_time_tags = [pd.Timestamp(date).timestamp() for date in self.xrsb.iloc[-30:]['time_tag']]
            self.new_xrsa = np.array(self.xrsa.iloc[-30:]['flux'])
            self.new_xrsb = np.array(self.xrsb.iloc[-30:]['flux'])
        else: 
            self.new_time_tags = [pd.Timestamp(date).timestamp() for date in self.xrsb['time_tag']]
            self.new_xrsa = np.array(self.xrsa['flux'])
            self.new_xrsb = np.array(self.xrsb['flux'])

        self.display_goes()
        self.xrsa_data.setData(self.new_time_tags, self._log_data(self.new_xrsa))
        self.xrsb_data.setData(self.new_time_tags, self._log_data(self.new_xrsb))
        
    def update_trigger_plot(self): 
        if self.flare_summary.shape[0]!=0:
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
            
    def _plot_foxsi_launch_line(self):
        if (list(self.xrsa['time_tag'])[-1]<=self.coming_launch_time) and \
            (self._flare_prediction_state != "post-launch") and \
                not hasattr(self,"_launched"):
            self.FOXSI_launch_plot.setData([pd.Timestamp(self.coming_launch_time).timestamp()]*2, 
                                            [self._lowest_yrange, self._highest_yrange], 
                                            pen=pg.mkPen('g', width=5))
        else:
            pen_details = {"color":'g',"width":4} if hasattr(self,"_launched") else {"color":(100,100,100),"width":4,"style":QtCore.Qt.PenStyle.DotLine}
            self.FOXSI_launch_plot.setData([pd.Timestamp(self.coming_launch_time).timestamp()]*2, 
                                           [self._lowest_yrange, self._highest_yrange], 
                                            pen=pg.mkPen(**pen_details))
        self.FOXSI_launch_plot.setAlpha(1, False)
    
    def update_launch_plots(self):
        if self.flare_summary.shape[0] != 0:
            #setting launch lines to the right time
            if hasattr(self,"coming_launch_time") and (list(self.xrsa['time_tag'])[-30]<=self.coming_launch_time):
                self._plot_foxsi_launch_line()

            if self.flare_summary['FOXSI Obs Start'].iloc[-1] in list(self.xrsb['time_tag'].iloc[-30:]):
                self.HIC_launch_plot.setData([pd.Timestamp(self.flare_summary['FOXSI Obs Start'].iloc[-1]).timestamp()]*2, [self._lowest_yrange, self._highest_yrange])
                self.HIC_launch_plot.setAlpha(1, False)
            #removing launch lines when they are out of range
            if hasattr(self,"coming_launch_time") and (list(self.xrsa['time_tag'])[-30]>self.coming_launch_time):
                self.FOXSI_launch_plot.setData([np.nan]*2, [self._lowest_yrange, self._highest_yrange])
                self.FOXSI_launch_plot.setAlpha(0, False)
                del self.coming_launch_time
                if hasattr(self,"_launched"):
                    del self._launched
            if self.flare_summary['FOXSI Obs Start'].iloc[-1] not in list(self.xrsb['time_tag'].iloc[-30:]):
                self.HIC_launch_plot.setData([np.nan]*2, [self._lowest_yrange, self._highest_yrange])
                self.HIC_launch_plot.setAlpha(0, False)  
        else:
              self.FOXSI_launch_plot.setData([np.nan]*2, [self._lowest_yrange, self._highest_yrange])
              self.FOXSI_launch_plot.setAlpha(0, False)
              self.HIC_launch_plot.setData([np.nan]*2, [self._lowest_yrange, self._highest_yrange])
              self.HIC_launch_plot.setAlpha(0, False)
        
    def save_data(self):
        self.flare_summary.to_csv(f'{PACKAGE_DIR}/SessionSummaries/{self.foldername}/timetag_summary.csv')
        self.xrsa.to_csv(f'{PACKAGE_DIR}/SessionSummaries/{self.foldername}/GOES_XRSA.csv')
        self.xrsb.to_csv(f'{PACKAGE_DIR}/SessionSummaries/{self.foldername}/GOES_XRSB.csv')
        
            
        
	