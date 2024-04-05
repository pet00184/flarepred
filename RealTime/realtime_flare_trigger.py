import pandas as pd
from PyQt6 import QtWidgets, QtCore, QtGui
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtCore import QUrl
import PyQt6
from pyqtgraph import PlotWidget, plot
import pyqtgraph as pg
import sys
import os
import numpy as np
import GOES_data_upload as GOES_data
import flare_conditions as fc
import emission_measure
from datetime import datetime, timedelta, timezone
import math

PACKAGE_DIR = os.path.dirname(os.path.realpath(__file__))

class RealTimeTrigger(QtWidgets.QWidget):
    
    print_updates=False #prints more updated in terminal. Only suggested for real-time data.
    ms_timing = 4000 #amount of ms between each new data download.
    
    LAUNCH_TO_FOXSI_OBS_START = 2
    LAUNCH_TO_FOXSI_OBS_END = LAUNCH_TO_FOXSI_OBS_START + 6
    LAUNCH_TO_HIC_OBS_START = LAUNCH_TO_FOXSI_OBS_START + 1
    LAUNCH_TO_HIC_OBS_END = LAUNCH_TO_HIC_OBS_START + 6
    DEADTIME = 30
    
    mm_a = 7.288781677851528e-09; cc_a = -4.698588594426906e-06 #used for goes proxy
    
    # need to be class variable to connect
    value_changed_signal_status = QtCore.pyqtSignal()
    value_changed_new_xrsb = QtCore.pyqtSignal()
    value_changed_alerts = QtCore.pyqtSignal()

    def __init__(self, goes_data, eovsa_data, eve_data, foldername, sound_filename, no_eovsa, no_eve, parent=None):
        QtWidgets.QWidget.__init__(self,parent)
        
        #making folder to store summary data:
        # if not os.path.exists(f"{PACKAGE_DIR/SessionSummaries}"):
#             os.mkdir(f"{PACKAGE_DIR/SessionSummaries}")
            
        if not os.path.exists(os.path.join(PACKAGE_DIR, "SessionSummaries", foldername)):
            os.makedirs(os.path.join(PACKAGE_DIR, "SessionSummaries", foldername))
        
        #defining if we are including EOVSA data or not: 
        self.no_eovsa = no_eovsa    
        self.no_eve = no_eve
        #defining data:
        self.XRS_data = goes_data
        self.EOVSA_data = eovsa_data
        self.EVE_data = eve_data
        self.foldername = foldername
        self.sound_filename=sound_filename
        
        #defining XRS variables: 
        self.goes_current = None #newly reloaded data
        self.goes = None #total data (aggregated during entire run time)
        self.current_time = None #most recent time of data
        self.current_realtime = self._get_datetime_now() #current realtime- accounts for 3 minute latency
        
        #defining flare state 
        self.flare_prediction_state("searching")
        self.flare_happening = False
        self.launch = False
        self.post_launch = False
        
        #setting up trigger alarm sound
        self.trigger_sound_effect = QSoundEffect()
        self.trigger_sound_effect.setSource(QUrl.fromLocalFile(self.sound_filename))
        self.trigger_sound_effect.setLoopCount(1)
        
        
        self.flare_summary = pd.DataFrame(columns=['Trigger','Realtime Trigger', 'Countdown Initiated', 'Hold', 'Launch', 'HiC Launch', 'Flare End', 'FOXSI Obs Start', 'FOXSI Obs End', 'HiC Obs Start', 'HiC Obs End'])
        self.flare_summary_index = -1
        self.fai_summary = pd.DataFrame(columns=['Flare_Index', 'FAI_Time'])
        self.fai_summary_index = -1
        self.FAI_loc = 0
        
        #initial loading of the data: 
        self.load_data(reload=False)
        if self.no_eovsa==False:
            self.load_eovsa_data(reload=False)
        if self.no_eve==False:
            self.load_eve_data(reload=False)
            
        self.find_goes_proxy()
        
        #initial plotting of data: 
        #initializing plot: 
        self.layout = QtWidgets.QGridLayout()
        
        self.graphWidget = pg.PlotWidget(axisItems={'bottom': pg.DateAxisItem()}) # to have the plot at UTC then `pg.DateAxisItem(utcOffset=0)`
        self.tempgraph = pg.PlotWidget(axisItems={'bottom': pg.DateAxisItem()})
        self.emgraph = pg.PlotWidget(axisItems={'bottom': pg.DateAxisItem()})
        self.evegraph0 = pg.PlotWidget(axisItems={'bottom': pg.DateAxisItem()})
        self.evegraph30 = pg.PlotWidget(axisItems={'bottom': pg.DateAxisItem()})
        if not no_eovsa:
            self.eovsagraph = pg.PlotWidget(axisItems={'bottom': pg.DateAxisItem()})
        # self.setCentralWidget(self.graphWidget)
        
        #################### CHANGING THE LAYOUT HERE ONLY ##################################
        self.layout.addWidget(self.graphWidget, 0, 0, 1, 3)
        self.layout.addWidget(self.tempgraph, 0, 3, 1, 2)
        self.layout.addWidget(self.emgraph, 1, 3, 1, 2)
        self.layout.addWidget(self.evegraph0, 1, 0, 1, 3)
        #self.layout.addWidget(self.evegraph30, 1, 1, 1, 1)
        # if not no_eovsa:
        #     self.layout.addWidget(self.eovsagraph, 1, 2, 1, 1)
            
        self.setLayout(self.layout)

        # Disable interactivity
        self.graphWidget.setMouseEnabled(x=False, y=False)  # Disable mouse panning & zooming
        
        self.graphWidget.setBackground('w')
        styles = {'color':'k', 'font-size':'20pt', "units":None} 
        self.graphWidget.setLabel('left', 'W m<sup>-2</sup>', **styles)
        self.graphWidget.setLabel('bottom', 'Time', **styles)
        self.graphWidget.setTitle(f'GOES XRS', color='k', size='24pt')
        self.graphWidget.addLegend()
        self.graphWidget.showGrid(x=True, y=True)
        self.graphWidget.getAxis('left').enableAutoSIPrefix(enable=False)
        
        # SAME FOR TEMP WIDGET
        self.tempgraph.setMouseEnabled(x=False, y=False)  # Disable mouse panning & zooming
        
        self.tempgraph.setBackground('w')
        styles = {'color':'k', 'font-size':'20pt', "units":None} 
        #self.graphWidget.setLabel('left', 'W m<sup>-2</sup>', **styles)
        self.tempgraph.setLabel('bottom', 'Time', **styles)
        self.tempgraph.setLabel('left', 'MK', **styles)
        self.tempgraph.setTitle(f'Temperature', color='k', size='24pt')
        #self.tempgraph.addLegend()
        self.tempgraph.showGrid(x=True, y=True)
        self.tempgraph.getAxis('left').enableAutoSIPrefix(enable=False)
        
        # SAME FOR EM WIDGET
        self.emgraph.setMouseEnabled(x=False, y=False)  # Disable mouse panning & zooming
        
        self.emgraph.setBackground('w')
        styles = {'color':'k', 'font-size':'20pt', "units":None} 
        self.emgraph.setLabel('left', 'cm<sup>-3</sup>', **styles)
        self.emgraph.setLabel('bottom', 'Time', **styles)
        self.emgraph.setTitle(f'Emission Measure', color='k', size='24pt')
        #self.emgraph.addLegend()
        self.emgraph.showGrid(x=True, y=True)
        self.emgraph.getAxis('left').enableAutoSIPrefix(enable=False)
        
        if not no_eovsa:
            # SAME FOR EOVSA WIDGET
            self.eovsagraph.setMouseEnabled(x=False, y=False)  # Disable mouse panning & zooming
        
            self.eovsagraph.setBackground('w')
            styles = {'color':'k', 'font-size':'20pt', "units":None} 
            self.eovsagraph.setLabel('left', 'amplitude sums', **styles)
            self.eovsagraph.setLabel('bottom', 'Time', **styles)
            self.eovsagraph.setTitle(f'EOVSA', color='k', size='24pt')
            self.eovsagraph.addLegend()
            self.eovsagraph.showGrid(x=True, y=True)
            self.eovsagraph.getAxis('left').enableAutoSIPrefix(enable=False)
        
        # SAME FOR EVE WIDGETS
        self.evegraph0.setMouseEnabled(x=False, y=False)  # Disable mouse panning & zooming
        
        self.evegraph0.setBackground('w')
        styles = {'color':'k', 'font-size':'20pt', "units":None} 
        self.evegraph0.setLabel('left', 'Raw Counts', **styles)
        self.evegraph0.setLabel('bottom', 'Time', **styles)
        self.evegraph0.setTitle(f'EVE ESP 0-7nm', color='k', size='24pt')
        self.evegraph0.addLegend()
        self.evegraph0.showGrid(x=True, y=True)
        self.evegraph0.getAxis('left').enableAutoSIPrefix(enable=False)
        
        self.evegraph30.setMouseEnabled(x=False, y=False)  # Disable mouse panning & zooming
        
        self.evegraph30.setBackground('w')
        styles = {'color':'k', 'font-size':'20pt', "units":None} 
        self.evegraph30.setLabel('left', 'Raw Counts', **styles)
        self.evegraph30.setLabel('bottom', 'Time', **styles)
        self.evegraph30.setTitle(f'EVE ESP 30nm', color='k', size='24pt')
        self.evegraph30.addLegend()
        self.evegraph30.showGrid(x=True, y=True)
        self.evegraph30.getAxis('left').enableAutoSIPrefix(enable=False)

        # convert left and right y-axes to display GOES notation stuff
        self._min_arr, self._max_arr = "xrsa", "xrsb" # give values to know what ylims are used
        self._logy = True
        self._lowest_yrange, self._highest_yrange = -8*1.02, -3*0.96
        self.display_goes()
        self.display_temp()
        self.display_em()
        self.display_eve0()
        self.display_eve30()
        self.xlims()
        
        #PLOTTING EVE: 
        if self.no_eve==False:
            self.evetime_tags = [pd.Timestamp(str(date)).timestamp() for date in self.eve['UTC_TIME']]
            self.eve0_data = self.eveplot0(self.evetime_tags, self.eve['ESP_0_7_COUNTS'], color='salmon', plotname='ESP 0-7 nm')
            self.eve30_data = self.eveplot30(self.evetime_tags, self.eve['ESP_30_COUNTS'], color='cyan', plotname='ESP 30 nm')
            
            #initializing trigger and observation plotting FOR eovsa:
            self.flare_trigger_eveplot0 = self.eveplot0([self.evetime_tags[0]]*2, [self.line_min_eve0, self.line_max_eve0], color='gray', plotname=None)
            self.flare_trigger_eveplot0.setAlpha(0, False)
            self.flare_realtrigger_eveplot0 = self.eveplot0([self.evetime_tags[0]]*2, [self.line_min_eve0, self.line_max_eve0], color='k', plotname=None)
            self.flare_realtrigger_eveplot0.setAlpha(0, False)
            self.FOXSI_launch_eveplot0 = self.eveplot0([self.evetime_tags[0]]*2, [self.line_min_eve0, self.line_max_eve0], color='green', plotname=None)
            self.FOXSI_launch_eveplot0.setAlpha(0, False)
            self.HIC_launch_eveplot0 = self.eveplot0([self.evetime_tags[0]]*2, [self.line_min_eve0, self.line_max_eve0], color='orange', plotname=None)
            self.HIC_launch_eveplot0.setAlpha(0, False)
            fai_time = pd.Timestamp(self.goes['time_tag'].iloc[self.FAI_loc]).timestamp()
            self.FAI_eveplot0 = self.eveplot0([fai_time]*2, [self.line_min_eve0, self.line_max_eve0], color='pink', plotname=None)
            if self.FAI_loc > 0:
                self.FAI_eveplot0.setAlpha(1, False)
            else:
                self.FAI_eveplot0.setAlpha(0, False)
            
            self.flare_trigger_eveplot30 = self.eveplot30([self.evetime_tags[0]]*2, [self.line_min_eve30, self.line_max_eve30], color='gray', plotname=None)
            self.flare_trigger_eveplot30.setAlpha(0, False)
            self.flare_realtrigger_eveplot30 = self.eveplot30([self.evetime_tags[0]]*2, [self.line_min_eve30, self.line_max_eve30], color='k', plotname=None)
            self.flare_realtrigger_eveplot30.setAlpha(0, False)
            self.FOXSI_launch_eveplot30 = self.eveplot30([self.evetime_tags[0]]*2, [self.line_min_eve30, self.line_max_eve30], color='green', plotname=None)
            self.FOXSI_launch_eveplot30.setAlpha(0, False)
            self.HIC_launch_eveplot30 = self.eveplot30([self.evetime_tags[0]]*2, [self.line_min_eve30, self.line_max_eve30], color='orange', plotname=None)
            self.HIC_launch_eveplot30.setAlpha(0, False)
            self.FAI_eveplot30 = self.eveplot30([fai_time]*2, [self.line_min_eve30, self.line_max_eve30], color='pink', plotname=None)
            if self.FAI_loc > 0:
                self.FAI_eveplot30.setAlpha(1, False)
            else:
                self.FAI_eveplot30.setAlpha(0, False)

        else:
            font = QtGui.QFont()
            font.setPixelSize(40)
            self.evegraph0.setYRange(0, 1)
            self.evegraph30.setYRange(0, 1)
            self.evetext = pg.TextItem("No EVE Data", color=(255,0,0), anchor=(0.5,0.5))
            self.evegraph0.addItem(self.evetext)
            self.evegraph30.addItem(self.evetext)
            xloc = pd.Timestamp(self._get_datetime_now()-timedelta(minutes=15)).timestamp()
            self.evetext.setPos(xloc, .5)
            self.evetext.setFont(font)
            
        #PLOTTING GOES
        #goes proxy from eve:
        self.goes_proxy = self.proxyplot(self.evetime_tags, np.array(self.eve['ESP_0_7_COUNTS'])*self.proxy_ratio, color='salmon', plotname='GOES PROXY')
        
        self.time_tags = [pd.Timestamp(date).timestamp() for date in self.goes['time_tag']]
        self.xrsb_data = self.plot(self.time_tags, np.array(self.goes['xrsb']), color='r', plotname='GOES XRSB')
        self.xrsa_data = self.plot(self.time_tags, np.array(self.goes['xrsa']), color='b', plotname='GOES XRSA')
        
        #initializing trigger and observation plotting:
        self.flare_trigger_plot = self.plot([self.time_tags[0]]*2, [1e-9, 1e-3], color='gray', plotname='Data Trigger')
        self.flare_trigger_plot.setAlpha(0, False)
        self.flare_realtrigger_plot = self.plot([self.time_tags[0]]*2, [1e-9, 1e-3], color='k', plotname='Actual time of Trigger')
        self.flare_realtrigger_plot.setAlpha(0, False)
        self.FOXSI_launch_plot = self.plot([self.time_tags[0]]*2, [1e-9, 1e-3], color='green', plotname='FOXSI Launch')
        self.FOXSI_launch_plot.setAlpha(0, False)
        self.HIC_launch_plot = self.plot([self.time_tags[0]]*2, [1e-9, 1e-3], color='orange', plotname='HIC Launch')
        self.HIC_launch_plot.setAlpha(0, False)
        self.FAI_plot = self.plot([pd.Timestamp(self.goes['time_tag'].iloc[self.FAI_loc]).timestamp()]*2, [1e-9, 1e-3], color='pink', plotname='FAI')
        if self.FAI_loc > 0:
            self.FAI_plot.setAlpha(1, False)
        else:
            self.FAI_plot.setAlpha(0, False)
        
        #PLOTTING TEMP:
        self.temp_data = self.tempplot(self.time_tags, np.array(self.goes['Temp']), color='g', plotname='Temperature')
        
        #initializing trigger and observation plotting FOR TEMP:
        self.flare_trigger_tempplot = self.tempplot([self.time_tags[0]]*2, [self.line_min_temp, self.line_max_temp], color='gray', plotname='Data Trigger')
        self.flare_trigger_tempplot.setAlpha(0, False)
        self.flare_realtrigger_tempplot = self.tempplot([self.time_tags[0]]*2, [self.line_min_temp, self.line_max_temp], color='k', plotname='Actual time of Trigger')
        self.flare_realtrigger_tempplot.setAlpha(0, False)
        self.FOXSI_launch_tempplot = self.tempplot([self.time_tags[0]]*2, [self.line_min_temp, self.line_max_temp], color='green', plotname='FOXSI Launch')
        self.FOXSI_launch_tempplot.setAlpha(0, False)
        self.HIC_launch_tempplot = self.tempplot([self.time_tags[0]]*2, [self.line_min_temp, self.line_max_temp], color='orange', plotname='HIC Launch')
        self.HIC_launch_tempplot.setAlpha(0, False)
        self.FAI_tempplot = self.tempplot([pd.Timestamp(self.goes['time_tag'].iloc[self.FAI_loc]).timestamp()]*2, [self.line_min_temp, self.line_max_temp], color='pink', plotname='FAI')
        if self.FAI_loc > 0:
            self.FAI_tempplot.setAlpha(1, False)
        else:
            self.FAI_tempplot.setAlpha(0, False)
        
        #PLOTTING EM:
        self.em_data = self.emplot(self.time_tags, np.array(self.goes['emission measure']), color='orange', plotname='Emission Measure')
        
        #initializing trigger and observation plotting FOR EM:
        self.flare_trigger_emplot = self.emplot([self.time_tags[0]]*2, [self.line_min_em, self.line_max_em], color='gray', plotname='Data Trigger')
        self.flare_trigger_emplot.setAlpha(0, False)
        self.flare_realtrigger_emplot = self.emplot([self.time_tags[0]]*2, [self.line_min_em, self.line_max_em], color='k', plotname='Actual time of Trigger')
        self.flare_realtrigger_emplot.setAlpha(0, False)
        self.FOXSI_launch_emplot = self.emplot([self.time_tags[0]]*2, [self.line_min_em, self.line_max_em], color='green', plotname='FOXSI Launch')
        self.FOXSI_launch_emplot.setAlpha(0, False)
        self.HIC_launch_emplot = self.emplot([self.time_tags[0]]*2, [self.line_min_em, self.line_max_em], color='orange', plotname='HIC Launch')
        self.HIC_launch_emplot.setAlpha(0, False)
        self.FAI_emplot = self.emplot([pd.Timestamp(self.goes['time_tag'].iloc[self.FAI_loc]).timestamp()]*2, [self.line_min_em, self.line_max_em], color='pink', plotname='FAI')
        if self.FAI_loc > 0:
            self.FAI_emplot.setAlpha(1, False)
        else:
            self.FAI_emplot.setAlpha(0, False)
        
        #PLOTTING EOVSA: 
        if self.no_eovsa==False:
            self.eovsatime_tags = [pd.Timestamp(str(date)).timestamp() for date in self.eovsa['time']]
            self.eovsa1_data = self.eovsaplot(self.eovsatime_tags, self.eovsa['1-7 GHz'], color='purple', plotname='1-7 GHz')
            self.eovsa2_data = self.eovsaplot(self.eovsatime_tags, self.eovsa['7-13 GHz'], color='blue', plotname='7-13 GHz')
            self.eovsa3_data = self.eovsaplot(self.eovsatime_tags, self.eovsa['13-18 GHz'], color='green', plotname='13-18 GHz')
        
            self.eovsa_alert = self.eovsaplot([self.eovsatime_tags[0]]*2, [0, np.max(np.array(self.eovsa['1-7 GHz']))], color='k', plotname='EOVSA Flare Trigger')
            self.eovsa_alert.setAlpha(0, False)
            
            #initializing trigger and observation plotting FOR eovsa:
            self.flare_trigger_eovsaplot = self.eovsaplot([self.eovsatime_tags[0]]*2, [0, np.max(np.array(self.eovsa['1-7 GHz']))], color='gray', plotname=None)
            self.flare_trigger_eovsaplot.setAlpha(1, False)
            self.flare_realtrigger_eovsaplot = self.eovsaplot([self.eovsatime_tags[0]]*2, [0, np.max(np.array(self.eovsa['1-7 GHz']))], color='k', plotname=None)
            self.flare_realtrigger_eovsaplot.setAlpha(1, False)
            self.FOXSI_launch_eovsaplot = self.eovsaplot([self.eovsatime_tags[0]]*2, [0, np.max(np.array(self.eovsa['1-7 GHz']))], color='green', plotname=None)
            self.FOXSI_launch_eovsaplot.setAlpha(1, False)
            self.HIC_launch_eovsaplot = self.eovsaplot([self.eovsatime_tags[0]]*2, [0, np.max(np.array(self.eovsa['1-7 GHz']))], color='orange', plotname=None)
            self.HIC_launch_eovsaplot.setAlpha(1, False)

        # else:
        #     font = QtGui.QFont()
        #     font.setPixelSize(40)
        #     self.eovsagraph.setYRange(0, 1)
        #     self.eovsatext = pg.TextItem("No EOVSA Data", color=(255,0,0), anchor=(0.5,0.5))
        #     self.eovsagraph.addItem(self.eovsatext)
        #     xloc = pd.Timestamp(self._get_datetime_now()-timedelta(minutes=15)).timestamp()
        #     self.eovsatext.setPos(xloc, .5)
        #     self.eovsatext.setFont(font)
            
        

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
        #self.graphWidget.getAxis('right').setLabel('GOES Class')
        self.graphWidget.getAxis('right').setGrid(False)
        self.graphWidget.getAxis('right').enableAutoSIPrefix(enable=False)

        keep_intermediate_classes = self.ticks_display()

        goes_labels_ints_keep = self._keep_goes_intermediate(intermediate_classes=intermediate_classes, classes_to_keep=keep_intermediate_classes)
        goes_value_ints_keep = log_value_ints[goes_labels_ints_keep]

        if self._logy:
            self.graphWidget.getAxis('right').setTicks([[(v, str(s)) if (v in goes_value_ints_keep) else (v,"") for v,s in zip(log_value_ints,goes_labels_ints)]])
            self.graphWidget.getAxis('left').setTicks([[(v, f"{s:0.0e}") if (v in goes_value_ints_keep) else (v,"") for v,s in zip(log_value_ints,value_ints)]])
            # if not self.no_eovsa: self.eovsagraph.setLogMode(False, True)
            # self.evegraph0.setLogMode(False, True)
            # self.evegraph30.setLogMode(False, True)
        else: 
            self.graphWidget.getAxis('right').setTicks([[(v, str(s)) if (v in goes_value_ints_keep) else (v,"") for v,s in zip(value_ints,goes_labels_ints)]])
            self.graphWidget.getAxis('left').setTicks([[(v, f"{s:0.0e}") if (v in goes_value_ints_keep) else (v,"") for v,s in zip(value_ints,value_ints)]])
            # self._lowest_yrange = 10**self._lowest_yrange
            # self._highest_yrange = 10**self._highest_yrange
            # if not self.no_eovsa: self.eovsagraph.setLogMode(False, False)
            # self.evegraph0.setLogMode(False, False)
            # self.evegraph30.setLogMode(False, False)
        
        self.xlims()

    def ticks_display(self):
        """ Chooses which ticks to display for certain y-ranges. """
        _max_arr = getattr(self,"new_"+self._max_arr) if hasattr(self, "new_"+self._max_arr) else self.goes['xrsb']
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
        _min_arr = getattr(self,"new_"+self._min_arr) if hasattr(self, "new_"+self._min_arr) else self.goes['xrsa']
        _max_arr = getattr(self,"new_"+self._max_arr) if hasattr(self, "new_"+self._max_arr) else self.goes['xrsb']

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
        
    def display_temp(self):
        ''' Sets the ylimits, and frame for the Temperature plot.
        '''
        #temperature:
        self.min_temp, self.max_temp = np.nanmin([2, np.nanmin(self.goes['Temp'].iloc[-27:]) * 0.9]), np.nanmax([18, np.nanmax(self.goes['Temp'].iloc[-27:]) * 1.1])
        self.line_min_temp, self.line_max_temp = np.nanmin([1, np.nanmin(self.goes['Temp'].iloc[-27:]) * 0.8]), np.nanmax([19, np.nanmax(self.goes['Temp'].iloc[-27:]) * 1.2])
        self.tempgraph.plotItem.vb.setLimits(yMin=self.min_temp, yMax=self.max_temp)
        
        self.tempgraph.showAxis('top')
        self.tempgraph.getAxis('top').setStyle(showValues=False)
        self.tempgraph.getAxis('top').setGrid(False)
        self.tempgraph.showAxis('right')
        self.tempgraph.getAxis('right').setGrid(False)
        self.tempgraph.getAxis('right').enableAutoSIPrefix(enable=False)
        self.tempgraph.plot()
        
    def display_em(self):
        ''' Sets the ylimits for emission measure plot.
        '''
        #emission measure:
        #self.min_em, self.max_em = np.nanmin([1e48, np.nanmin(self.goes['emission measure'].iloc[-27:]) * 0.33]), np.nanmax([6e48, np.nanmax(self.goes['emission measure'].iloc[-27:]) * 3])
        self.line_min_em, self.line_max_em = np.nanmin(self.goes['emission measure'].iloc[-27:]) * .8, np.nanmax(self.goes['emission measure'].iloc[-27:]) * 1.2 
        self.emgraph.setLogMode(False, False)
        #self.emgraph.plotItem.vb.setLimits(yMin=self.min_em, yMax=self.max_em)
        
        self.emgraph.showAxis('top')
        self.emgraph.getAxis('top').setStyle(showValues=False)
        self.emgraph.getAxis('top').setGrid(False)
        self.emgraph.showAxis('right')
        self.emgraph.getAxis('right').setGrid(False)
        self.emgraph.getAxis('right').enableAutoSIPrefix(enable=False)
        self.emgraph.plot()
        
    def display_eve0(self):
        ''' Sets the ylimits for ESP 0-7 plot. Also moves to log mode if that is set.
        '''
        #EVE 0-7
        self.min_eve0, self.max_eve0 = np.nanmin(self.eve_current['ESP_0_7_COUNTS']) * 0.6, np.nanmax(self.eve_current['ESP_0_7_COUNTS']) * 1.4
        self.line_min_eve0, self.line_max_eve0 = np.nanmin(self.eve_current['ESP_0_7_COUNTS']) * 0.5, np.nanmax(self.eve_current['ESP_0_7_COUNTS']) * 1.5
        if self._logy:
            self.evegraph0.setLogMode(False, True)
            self.evegraph0.plotItem.vb.setLimits(yMin=self._log_data(self.min_eve0), yMax=self._log_data(self.max_eve0))
        else:
            self.evegraph0.setLogMode(False, False)
            self.evegraph0.plotItem.vb.setLimits(yMin=self.min_eve0, yMax=self.max_eve0)
        self.evegraph0.showAxis('top')
        self.evegraph0.getAxis('top').setStyle(showValues=False)
        self.evegraph0.getAxis('top').setGrid(False)
        self.evegraph0.showAxis('right')
        self.evegraph0.getAxis('right').setGrid(False)
        self.evegraph0.getAxis('right').enableAutoSIPrefix(enable=False)
        self.evegraph0.plot()
        
    def display_eve30(self):
        ''' Sets the ylimits for ESP 30 plot. If plot is in log mode, it moves to that. 
        '''
        self.min_eve30, self.max_eve30 = np.nanmin(self.eve_current['ESP_30_COUNTS']) * 0.6, np.nanmax(self.eve_current['ESP_30_COUNTS']) * 1.4
        self.line_min_eve30, self.line_max_eve30 = np.nanmin(self.eve_current['ESP_30_COUNTS']) * 0.5, np.nanmax(self.eve_current['ESP_30_COUNTS']) * 1.5
        if self._logy:
            self.evegraph30.setLogMode(False, True)
            self.evegraph30.plotItem.vb.setLimits(yMin=self._log_data(self.min_eve30), yMax=self._log_data(self.max_eve30))
        else:
            self.evegraph30.setLogMode(False, False)
            self.evegraph30.plotItem.vb.setLimits(yMin=self.min_eve30, yMax=self.max_eve30)
        self.evegraph30.showAxis('top')
        self.evegraph30.getAxis('top').setStyle(showValues=False)
        self.evegraph30.getAxis('top').setGrid(False)
        self.evegraph30.showAxis('right')
        self.evegraph30.getAxis('right').setGrid(False)
        self.evegraph30.getAxis('right').enableAutoSIPrefix(enable=False)
        self.evegraph30.plot()
        

    def xlims(self):
        """ Control the x-limits for plots. """
        # self.graphWidget.plotItem.setXRange(pd.Timestamp(self.goes.iloc[-30]['time_tag']).timestamp(), pd.Timestamp(self._get_datetime_now()).timestamp())
        _now = self._get_datetime_now()
        xmin = pd.Timestamp(_now-timedelta(minutes=30)).timestamp()
        xmax = pd.Timestamp(_now).timestamp()
        _plot_offest = -60 #seconds, for some reason the plot extends by about this much :(
        self.graphWidget.plotItem.setXRange(xmin, xmax + _plot_offest)
        self.tempgraph.plotItem.setXRange(xmin, xmax + _plot_offest)
        self.emgraph.plotItem.setXRange(xmin, xmax + _plot_offest)
        if not self.no_eovsa: self.eovsagraph.plotItem.setXRange(xmin, xmax + _plot_offest)
        if not self.no_eve:
            self.evegraph0.plotItem.setXRange(xmin, xmax + _plot_offest)
            self.evegraph30.plotItem.setXRange(xmin, xmax + _plot_offest)

    def _log_data(self, array):
        """ Check if the data is to be logged with `self._logy`."""
        if self._logy:
            log = np.log10(array)
            return log
        return array
        
    def find_goes_proxy(self):
        goes_ave = np.median(self.goes_current['xrsb'])
        eve_ave = np.median(self.eve_current['ESP_0_7_COUNTS'])
        self.proxy_ratio = goes_ave/eve_ave

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
        
    #commenting out in case we want to add automated pre-launch back in the future
    # def change_to_pre_launch_state(self):
#         self.flare_prediction_state("pre-launch")
        
    def change_to_launched_state(self):
        self.flare_prediction_state("launched")
        
    def change_to_post_launch_state(self):
        self.flare_prediction_state("post-launch")
   ####################################################################################
     
    def plot(self, x, y, color, plotname):
        pen = pg.mkPen(color=color, width=5)
        return self.graphWidget.plot(x, self._log_data(y), name=plotname, pen=pen, symbol="o", symbolSize=3)
        
    def proxyplot(self, x, y, color, plotname):
        pen = pg.mkPen(color=color, width=3)
        return self.graphWidget.plot(x, self._log_data(y), name=plotname, pen=pen)
        
    def tempplot(self, x, y, color, plotname):
        pen = pg.mkPen(color=color, width=5)
        return self.tempgraph.plot(x, y, name=plotname, pen=pen, symbol="o", symbolSize=3)
        
    def emplot(self, x, y, color, plotname):
        pen = pg.mkPen(color=color, width=5)
        return self.emgraph.plot(x, y, name=plotname, pen=pen, symbol="o", symbolSize=3)
        
    def eovsaplot(self, x, y, color, plotname):
        pen = pg.mkPen(color=color, width=5)
        return self.eovsagraph.plot(x, y, name=plotname, pen=pen)
        
    def eveplot0(self, x, y, color, plotname):
        pen = pg.mkPen(color=color, width=5)
        return self.evegraph0.plot(x, y, name=plotname, pen=pen)
        
    def eveplot30(self, x, y, color, plotname):
        pen = pg.mkPen(color=color, width=5)
        return self.evegraph30.plot(x, y, name=plotname, pen=pen)
       
    def load_data(self, reload=True):
        if self.print_updates: print('Loading Data')
        self.goes_current = self.XRS_data()
        self.current_time = list(self.goes_current['time_tag'])[-1]
        self.current_realtime = self._get_datetime_now()# self.current_time + pd.Timedelta(3, unit='minutes') #to account for latency
        if not reload:
            self.goes = self.goes_current
            self.calculate_param_arrays(0, new=False)
            self.check_for_FAI(0, new=False)
            
    def load_eovsa_data(self, reload=True):
        self.eovsa_current = self.EOVSA_data()
        if not reload:
            self.eovsa = self.eovsa_current 
    
    def load_eve_data(self, reload=True):
        self.eve_current = self.EVE_data()
        if not reload:
            self.eve = self.eve_current
            
    def check_for_new_eovsa_data(self):
        """ Checking for new EOVSA data- this will update about once per second!"""
        self.new_eovsa_data = False
        new_times = self.eovsa_current.iloc[:]['time'] > list(self.eovsa['time'])[-1]
        
        if len(self.eovsa_current[new_times]['time']) > 0:
            added_points = len(self.eovsa_current[new_times]['time'])
            self.eovsa = self.eovsa._append(self.eovsa_current[new_times], ignore_index=True)
            self.new_eovsa_data=True
            
    def check_for_eovsa_alert(self):
        self.eovsa_current_alert = False
        self.eovsa_past_alert = False
        self.eovsa_alert_loc=0
        if self.eovsa.shape[0]>1800:
            where_alert = np.where(self.eovsa.iloc[-1800:]['Flare Flag']==True)[0]
        else:
            where_alert = np.where(self.eovsa['Flare Flag']==True)[0]
        if len(where_alert)> 0 and self.eovsa.iloc[-1]['Flare Flag']==True:
            self.eovsa_current_alert=True
            self.eovsa_alert_loc = where_alert[0]
        if len(where_alert)>0 and self.eovsa.iloc[-1]['Flare Flag']==False:
            self.eovsa_past_alert=True
            self.eovsa_alert_loc = where_alert[0]
            
    def check_for_new_eve_data(self):
        """ Checking for new EOVSA data- this will update about once per second!"""
        self.new_eve_data = False
        new_times = self.eve_current.iloc[:]['UTC_TIME'] > list(self.eve['UTC_TIME'])[-1]
        
        if len(self.eve_current[new_times]['UTC_TIME']) > 0:
            added_points = len(self.eve_current[new_times]['UTC_TIME'])
            self.eve = self.eve._append(self.eve_current[new_times], ignore_index=True)
            self.new_eve_data=True
            
    def check_for_new_data(self):
        """ Check for new data and add to what is plotted. """
        self.new_data = False
        # get indices for any data that has a newer time than the newest plotted
        new_times = self.goes_current.iloc[:]['time_tag']>list(self.goes['time_tag'])[-1]
        # if there are >0 new data-points then append them to the plotting data
        if len(self.goes_current[new_times]['time_tag']) > 0: 
            added_points = len(self.goes_current[new_times]['time_tag'])
            self.goes = self.goes._append(self.goes_current[new_times], ignore_index=True)
            self.calculate_param_arrays(added_points, new=True)
            self.check_for_FAI(added_points, new=True)
            self.new_data = True

            # make sure the y-limits change with the plot if needed and alert that new data is added
            self.display_goes()
            self.value_changed_new_xrsb.emit()
            
    def calculate_param_arrays(self, added_points, new=False):
        ''' Calculates temperature etc. and appends a new column to the data (or just last thing. work in progress)
        '''
        differences_to_calculate = [3, 5]
        if not new:
            for diff in differences_to_calculate:
                for xrs in ['xrsa', 'xrsb']:
                    xrsdiff = np.array(self.goes[xrs])
                    xrsdiff = xrsdiff[diff:] - xrsdiff[:-diff]
                    xrsdiff_final = np.concatenate([np.full(diff, math.nan), xrsdiff]) #appending correct # of 0's to front
                    self.goes[f'{diff}min{xrs}diff'] = xrsdiff_final
            #calculating em and temp here:
            em, temp = emission_measure.compute_goes_emission_measure(self.goes['xrsa'], self.goes['xrsb'], self.goes['satellite'])
            self.goes['emission measure'] = em #(em := emission_measure.compute_goes_emission_measure(self.goes))
            self.goes['Temp'] = temp
            #calculatign FAI param arrays here
            for diff in differences_to_calculate:
                em, temp = emission_measure.compute_goes_emission_measure(self.goes[f'{diff}minxrsadiff'], self.goes[f'{diff}minxrsbdiff'], self.goes['satellite'])
                self.goes[f'{diff}min emission measure'] = em
                self.goes[f'{diff}min Temp'] = temp
        if new:
            for i in range(added_points):
                new_point = -(added_points-i)
                #calculating 3-min difference is here:
                for diff in differences_to_calculate:
                    for xrs in ['xrsa', 'xrsb']:
                        self.goes.iloc[new_point, self.goes.columns.get_loc(f'{diff}min{xrs}diff')] = self.goes.iloc[new_point, self.goes.columns.get_loc(xrs)] - self.goes.iloc[new_point - diff, self.goes.columns.get_loc(xrs)]
                #calculating em and temp is here:
                em, temp = emission_measure.compute_goes_emission_measure(self.goes['xrsa'].iloc[new_point], self.goes['xrsb'].iloc[new_point], self.goes['satellite'].iloc[new_point])
                em_loc = self.goes.columns.get_loc('emission measure')
                temp_loc = self.goes.columns.get_loc('Temp')
                self.goes.iloc[new_point, em_loc] = em[0]
                self.goes.iloc[new_point, temp_loc] = temp[0]
                #calculating FAI param arrays here:
                for diff in differences_to_calculate:
                    em, temp = emission_measure.compute_goes_emission_measure(self.goes[f'{diff}minxrsadiff'].iloc[new_point], self.goes[f'{diff}minxrsbdiff'].iloc[new_point], self.goes['satellite'].iloc[new_point])
                    em_loc = self.goes.columns.get_loc(f'{diff}min emission measure')
                    temp_loc = self.goes.columns.get_loc(f'{diff}min Temp')
                    self.goes.iloc[new_point, em_loc] = em[0]
                    self.goes.iloc[new_point, temp_loc] = temp[0]

    def update_flare_alerts(self):  
        """ Function to update the alerts and emit a signal. """
        for a in self.flare_alert_names:
            self.flare_alerts.at['states', a] = fc.FLARE_ALERT_MAP[a](goes_data=self.goes)  
        self.value_changed_alerts.emit()
    
    def check_for_trigger(self):
        self.update_flare_alerts()
        if np.all(self.flare_alerts.loc['states']):
            self.change_to_triggered_state()
            self.flare_summary.loc[self.flare_summary_index, 'Trigger'] = self.current_time
            self.flare_summary.loc[self.flare_summary_index, 'Realtime Trigger'] = self.current_realtime
            print(f'FLARE TRIGGERED on {self.current_time} flux, at {self.current_realtime} UTC.')
            self.trigger_sound_effect.play()
        else:
            if self.print_updates: print('Still searching for flare')
            
    def check_for_FAI(self, added_points, new=True):
        ''' might want to move this somewehre else. For the initial load we want to see if there was any FAI for the 
        previous 30 min plotted, and plot that line if there was one (at the latest point.) Then, we want to have 
        the FAI get checked on just the last datapoint, and have it change to that if it is true. if not, stay at the 
        other most recent point.
        '''
        #self.FAI_loc = None
        if not new:
            potential_FAIs = np.where((self.goes['5min emission measure'] > .05e49) & (self.goes['5min Temp'] > 6))[0]
            if len(potential_FAIs) > 0:
                self.FAI_loc = potential_FAIs[-1]
                self.fai_summary_index += 1
                self.fai_summary.loc[self.fai_summary_index, 'Flare_Index'] = self.flare_summary_index
                self.fai_summary.loc[self.fai_summary_index, 'FAI_Time'] = self.goes['time_tag'].iloc[self.FAI_loc]
        if new:
            for i in range(added_points):
                new_point = -(added_points-i)
                new_FAI = (self.goes['5min emission measure'].iloc[new_point] > .05e49) & (self.goes['5min Temp'].iloc[new_point] > 6)
                if new_FAI:
                    self.FAI_loc = np.where(self.goes['time_tag'] == self.goes['time_tag'].iloc[new_point])[0][0]
                    self.fai_summary_index += 1
                    self.fai_summary.loc[self.fai_summary_index, 'Flare_Index'] = self.flare_summary_index
                    self.fai_summary.loc[self.fai_summary_index, 'FAI_Time'] = self.goes['time_tag'].iloc[self.FAI_loc]
             
    def check_for_flare_end(self):
        if fc.flare_end_condition(goes_data=self.goes):
            self.flare_summary.loc[self.flare_summary_index, 'Flare End'] = self.current_time
            if self._flare_prediction_state == "triggered":
                self.change_to_searching_state()
                print(f'Flare ended at {self.current_time}. DO NOT LAUNCH! Searching for another flare.')
            elif self._flare_prediction_state == "launched":
                self.flare_happening = False
                print(f'Flare ended during observation at {self.current_time}.')
            
             
    # def check_for_pre_launch(self):
    #     ''' This is used for automated pre-launch. Will be commented out as we are no longer including pre-launch.
    #     '''
    #     self.trigger_to_current_time = int(pd.Timedelta(pd.Timestamp(self.current_realtime) - self.flare_summary['Realtime Trigger'].iloc[-1]).seconds/60.0)
    #     if self.trigger_to_current_time == self.TRIGGER_WINDOW:
    #         print(f'Beginning 3-minute pre-launch window at {self.current_realtime}')
    #         # self.change_to_pre_launch_state()

    def _button_press_save_countdown_time(self):
        '''Button used to save when the launch countdown is started. We may want to build upon this and have
        a countdown window begin in the GUI itself.
        '''
        self.flare_summary.loc[self.flare_summary_index, 'Countdown Initiated'] = self.current_realtime
        
    def _button_press_launch(self):
        ''' Button used for changing to launch stage. Used to be to change to pre-launch stage, but now we are 
        surpassing that and going straight to launched state!
        '''
        if not hasattr(self,"coming_launch_time"):
            self.coming_launch_time = self.current_realtime #+timedelta(minutes=self.PRE_LAUNCH_WINDOW) #changed from get current time until we get the realtime vs. current_realtime all sorted
            self.coming_launch_time_hic = self.coming_launch_time + timedelta(minutes=1)
        self.change_to_launched_state()
        self.save_observation_times()
        
    def save_hold_time(self):
        ''' Saves the time the hold launch button was pressed, if pressed.
        '''
        self.flare_summary.loc[self.flare_summary_index, 'Hold'] = self.current_realtime

             
    # def check_for_launch(self):
    #     ''' Was used when we had pre-launch included. After 3 minutes, automatically switched to launch. Commenting
    #     out since we no longer automatically check for launch.
    #     '''
    #     self.trigger_to_current_time = int(pd.Timedelta(pd.Timestamp(self.current_realtime) - self.flare_summary['Launch Initiated'].iloc[-1]).seconds/60.0)
    #     if self.trigger_to_current_time >= self.PRE_LAUNCH_WINDOW and self._flare_prediction_state == "pre-launch":
    #         self.change_to_launched_state()
    #         self.save_observation_times()
    #         print(f'Launching FOXSI at {self.current_realtime}')
            
                  
    def save_observation_times(self):
        ''' Saves the time of launch, as well as the FOXSI and Hi-C observation start and end times, which are based off of
        the launch time.
        '''
        self.flare_summary.loc[self.flare_summary_index, 'Launch'] = self.current_realtime
        self.flare_summary.loc[self.flare_summary_index, 'HiC Launch'] = self.current_realtime + pd.Timedelta(1, unit='minutes')
        foxsi_obs_start = self.flare_summary['Launch'].iloc[-1] + pd.Timedelta(self.LAUNCH_TO_FOXSI_OBS_START, unit='minutes')
        foxsi_obs_end = self.flare_summary['Launch'].iloc[-1] + pd.Timedelta(self.LAUNCH_TO_FOXSI_OBS_END, unit='minutes')
        hic_obs_start = self.flare_summary['Launch'].iloc[-1] + pd.Timedelta(self.LAUNCH_TO_HIC_OBS_START, unit='minutes')
        hic_obs_end = self.flare_summary['Launch'].iloc[-1] + pd.Timedelta(self.LAUNCH_TO_HIC_OBS_END, unit='minutes')
        self.flare_summary.loc[self.flare_summary_index, 'FOXSI Obs Start'] = foxsi_obs_start
        self.flare_summary.loc[self.flare_summary_index, 'FOXSI Obs End'] = foxsi_obs_end
        self.flare_summary.loc[self.flare_summary_index, 'HiC Obs Start'] = hic_obs_start
        self.flare_summary.loc[self.flare_summary_index, 'HiC Obs End'] = hic_obs_end
        self._launched = None
        
    #commented this out so that we are no longer printing things in the terminal. Make this part of GUI instead? 
    # def provide_launch_updates(self):
    #     if self.current_realtime == self.flare_summary['FOXSI Obs Start'].iloc[-1]:
    #         print(f'Began FOXSI Observation at {self.current_realtime}')
    #     if self.current_realtime == self.flare_summary['FOXSI Obs End'].iloc[-1]:
    #         print(f'FOXSI Observation complete at {self.current_realtime}')
    #     if self.current_realtime == self.flare_summary['HiC Obs Start'].iloc[-1]:
    #         print(f'Beginning HiC Observation at {self.current_realtime}')
    #     if self.current_realtime == self.flare_summary['HiC Obs End'].iloc[-1]:
    #         print(f'HiC Observation complete at {self.current_realtime}')
    #     self._launched = None
            
    def check_for_post_launch(self):
        if self.current_realtime >= self.flare_summary['HiC Obs End'].iloc[-1] and self._flare_prediction_state == "launched":
            self.change_to_post_launch_state()
            print('Entering post-observation deadtime.')
            
    def check_for_search_again(self):
        if self.current_realtime >= self.flare_summary['HiC Obs End'].iloc[-1] + pd.Timedelta(self.DEADTIME, unit='minutes'): 
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
        now_time = self._get_datetime_now()
        if (now_time-self.current_realtime).seconds>(5*60):
            return self.current_realtime
        return now_time
    
    def _get_datetime_now(self):
        """ Always return the current UTC time. """
        return datetime.now(timezone.utc)
            
    def _update(self):
        self.load_data()
        if not self.no_eovsa:
            self.load_eovsa_data()
            self.check_for_new_eovsa_data()
            if self.new_eovsa_data:
                self.eovsa_plot_update()
                self.check_for_eovsa_alert()
                self.eovsa_alert_update()
        # if self.no_eovsa==True:
        #     self.no_eovsa_plot_update()
        if self.no_eve==False:
            self.load_eve_data()
            self.check_for_new_eve_data()
            if self.new_eve_data:
                self.eve_plot_update()
                self.update_eve_trigger_plots()
                self.update_eve_launch_plots()
                self.proxy_plot_update()
        if self.no_eve==True:
            self.no_eve_plot_update()
        self.check_for_new_data()
        #self.graphWidget.setTitle(f'GOES XRS Testing Status: {self._flare_prediction_state}') 
        if self.new_data:
            #self.all_ylims()
            self.xrs_plot_update()
            self.temp_plot_update()
            self.em_plot_update()
            self.update_FAI()
            self.update_temp_em_FAI()
            self.update_eve_FAI()
            if self.flare_happening: 
                self.check_for_flare_end()
            if self._flare_prediction_state == "searching":
                self.check_for_trigger()
            elif self._flare_prediction_state == "triggered":
                self.trigger_sound_effect.play()
            elif self._flare_prediction_state == "launched":
                #self.provide_launch_updates() #move this info to a GUI widget? 
                self.check_for_post_launch()
            elif self._flare_prediction_state == "post-launch":
                self.check_for_search_again()
            self.update_trigger_plot()
            self.update_eve_trigger_plots()
            self.update_temp_em_trigger_plots()
            self.update_launch_plot()
            self.update_eve_launch_plots()
            self.update_temp_em_launch_plots()
            self.save_data()
        self.xlims()
        self.update()
            
    def xrs_plot_update(self):
        
        if self.goes.shape[0]>30:
            self.time_tags = [pd.Timestamp(date).timestamp() for date in self.goes.iloc[-30:]['time_tag']]
            self.new_xrsa = np.array(self.goes.iloc[-30:]['xrsa'])
            self.new_xrsb = np.array(self.goes.iloc[-30:]['xrsb'])
        else: 
            self.time_tags = [pd.Timestamp(date).timestamp() for date in self.goes['time_tag']]
            self.new_xrsa = np.array(self.goes['xrsa'])
            self.new_xrsb = np.array(self.goes['xrsb'])

        self.display_goes()
        self.xrsa_data.setData(self.time_tags, self._log_data(self.new_xrsa))
        self.xrsb_data.setData(self.time_tags, self._log_data(self.new_xrsb))
        
    def temp_plot_update(self):
        if self.goes.shape[0]>30:
            self.time_tags = [pd.Timestamp(date).timestamp() for date in self.goes.iloc[-30:]['time_tag']]
            self.new_temp = np.array(self.goes.iloc[-30:]['Temp'])
        else: 
            self.time_tags = [pd.Timestamp(date).timestamp() for date in self.goes['time_tag']]
            self.new_temp = np.array(self.goes['Temp'])

        self.display_temp()
        self.temp_data.setData(self.time_tags, self.new_temp)
        
    def em_plot_update(self):
        if self.goes.shape[0]>30:
            self.time_tags = [pd.Timestamp(date).timestamp() for date in self.goes.iloc[-30:]['time_tag']]
            self.new_em = np.array(self.goes.iloc[-30:]['emission measure'])
        else: 
            self.time_tags = [pd.Timestamp(date).timestamp() for date in self.goes['time_tag']]
            self.new_em = np.array(self.goes['emission measure'])

        self.display_em()
        self.em_data.setData(self.time_tags, self.new_em)
        
    def eovsa_plot_update(self):
        self.new_eovsa_time_tags = [pd.Timestamp(str(date)).timestamp() for date in self.eovsa['time']]
        self.new_eovsa1 = np.array(self.eovsa['1-7 GHz'])
        self.new_eovsa2 = np.array(self.eovsa['7-13 GHz'])
        self.new_eovsa3 = np.array(self.eovsa['13-18 GHz'])
        
        self.eovsa1_data.setData(self.new_eovsa_time_tags, self.new_eovsa1)
        self.eovsa2_data.setData(self.new_eovsa_time_tags, self.new_eovsa2)
        self.eovsa3_data.setData(self.new_eovsa_time_tags, self.new_eovsa3)
        
    # def no_eovsa_plot_update(self):
    #     new_xloc = pd.Timestamp(self._get_datetime_now()-timedelta(minutes=15)).timestamp()
    #     self.eovsatext.setPos(new_xloc, .5)
        
    def eovsa_alert_update(self):
        if self.eovsa_current_alert == False and self.eovsa_past_alert == False:
            self.eovsa_alert.setData([pd.Timestamp(str(self.eovsa.iloc[0]['time'])).timestamp()]*2, [0, np.max(self.eovsa['1-7 GHz'])])
            self.eovsa_alert.setAlpha(0, False)
        if self.eovsa_current_alert == True:
            self.eovsa_alert.setData([pd.Timestamp(str(self.eovsa.iloc[self.eovsa_alert_loc]['time'])).timestamp()]*2, [0, np.max(self.eovsa['1-7 GHz'])])
            self.eovsa_alert.setAlpha(1, False)
        if self.eovsa_past_alert == True:
            self.eovsa_alert.setData([pd.Timestamp(str(self.eovsa.iloc[self.eovsa_alert_loc]['time'])).timestamp()]*2, [0, np.max(self.eovsa['1-7 GHz'])])
            self.eovsa_alert.setAlpha(0.5, False)
            
    def eve_plot_update(self):
        self.new_eve_time_tags = [pd.Timestamp(str(date)).timestamp() for date in self.eve['UTC_TIME']]
        self.new_eve0 = np.array(self.eve['ESP_0_7_COUNTS'])
        self.new_eve30 = np.array(self.eve['ESP_30_COUNTS'])
        
        self.display_eve0()
        self.display_eve30()
        self.eve0_data.setData(self.new_eve_time_tags, self.new_eve0)
        self.eve30_data.setData(self.new_eve_time_tags, self.new_eve30)
        
    def proxy_plot_update(self):
        self.find_goes_proxy()
        if self._logy:
            self.new_proxy = self._log_data(np.array(self.eve['ESP_0_7_COUNTS'])*self.proxy_ratio)
        else:
            self.new_proxy = np.array(self.eve['ESP_0_7_COUNTS'])*self.proxy_ratio
        if hasattr(self, "new_eve_data"):
            self.goes_proxy.setData(self.new_eve_time_tags, self.new_proxy)
        else:
            self.goes_proxy.setData(self.evetime_tags, self.new_proxy)
        
    def no_eve_plot_update(self):
        new_xloc = pd.Timestamp(self._get_datetime_now()-timedelta(minutes=15)).timestamp()
        self.evetext.setPos(new_xloc, .5)
            
    # def plot_update_FAI_alerts(self):
    #     ''' Sets plot line for FAI plot to most recent FAI.
    #     '''
    #     if pd.Timestamp(self.goes['time_tag'].iloc[self.FAI_loc]).timestamp() in list(self.time_tags):
    #         self.FAI_plot.setData([pd.Timestamp(self.goes['time_tag'].iloc[self.FAI_loc]).timestamp()]*2, [self._lowest_yrange, self._highest_yrange])
    #         self.FAI_tempplot.setData([pd.Timestamp(self.goes['time_tag'].iloc[self.FAI_loc]).timestamp()]*2, [self.line_min_temp, self.line_max_temp])
    #         self.FAI_emplot.setData([pd.Timestamp(self.goes['time_tag'].iloc[self.FAI_loc]).timestamp()]*2, [self.line_min_em, self.line_max_em])
    #         self.FAI_plot.setAlpha(1, False)
    #         self.FAI_tempplot.setAlpha(1, False)
    #         self.FAI_emplot.setAlpha(1, False)
    #     else:
    #         self.FAI_plot.setData([self.time_tags[0]]*2, [self._lowest_yrange, self._highest_yrange])
    #         self.FAI_tempplot.setData([self.time_tags[0]]*2, [self.line_min_temp, self.line_max_temp])
    #         self.FAI_emplot.setData([self.time_tags[0]]*2, [self.line_min_em, self.line_max_em])
    #         self.FAI_plot.setAlpha(0, False)
    #         self.FAI_tempplot.setAlpha(0, False)
    #         self.FAI_emplot.setAlpha(0, False)
            
    def update_FAI(self):
        ''' Sets plot line for GOES FAI alerts
        '''
        if self._logy:
            lower = self._lowest_yrange
            higher = self._highest_yrange
        else:
            lower = 10**self._lowest_yrange
            higher = 10**self._highest_yrange
        if pd.Timestamp(self.goes['time_tag'].iloc[self.FAI_loc]).timestamp() in list(self.time_tags):
            self.FAI_plot.setData([pd.Timestamp(self.goes['time_tag'].iloc[self.FAI_loc]).timestamp()]*2, [lower, higher])
            self.FAI_plot.setAlpha(1, False)
        else:
            self.FAI_plot.setData([self.time_tags[0]]*2, [lower, higher])
            self.FAI_plot.setAlpha(0, False)
            
    def update_temp_em_FAI(self):
        ''' Sets plot line for temp and emission measure FAI alerts.
        '''
        if pd.Timestamp(self.goes['time_tag'].iloc[self.FAI_loc]).timestamp() in list(self.time_tags):
            self.FAI_tempplot.setData([pd.Timestamp(self.goes['time_tag'].iloc[self.FAI_loc]).timestamp()]*2, [self.line_min_temp, self.line_max_temp])
            self.FAI_emplot.setData([pd.Timestamp(self.goes['time_tag'].iloc[self.FAI_loc]).timestamp()]*2, [self.line_min_em, self.line_max_em])
            self.FAI_tempplot.setAlpha(1, False)
            self.FAI_emplot.setAlpha(1, False)
        else:
            self.FAI_tempplot.setData([self.time_tags[0]]*2, [self.line_min_temp, self.line_max_temp])
            self.FAI_emplot.setData([self.time_tags[0]]*2, [self.line_min_em, self.line_max_em])
            self.FAI_tempplot.setAlpha(0, False)
            self.FAI_emplot.setAlpha(0, False)
            
    def update_eve_FAI(self):
        ''' Sets plot line for EVE FAI alerts.
        '''
        FAI_time = pd.Timestamp(self.goes['time_tag'].iloc[self.FAI_loc]).timestamp()
        if FAI_time > self.new_eve_time_tags[0]:
            self.FAI_eveplot0.setData([FAI_time]*2, [self.line_min_eve0, self.line_max_eve0])
            self.FAI_eveplot0.setAlpha(1, False)
            self.FAI_eveplot30.setData([FAI_time]*2, [self.line_min_eve30, self.line_max_eve30])
            self.FAI_eveplot30.setAlpha(1, False)
        elif FAI_time <= self.new_eve_time_tags[0]:
            self.FAI_eveplot0.setData([self.new_eve_time_tags[0]]*2, [self.line_min_eve0, self.line_max_eve0])
            self.FAI_eveplot0.setAlpha(0, False)
            self.FAI_eveplot30.setData([self.new_eve_time_tags[0]]*2, [self.line_min_eve30, self.line_max_eve30])
            self.FAI_eveplot30.setAlpha(0, False)
        
    def update_trigger_plot(self): 
        ''' Updates trigger lines for GOES. Call this whenever the GOES plot is updated (also during linear and log switch)
        '''
        if self._logy:
            lower = self._lowest_yrange
            higher = self._highest_yrange
        else:
            lower = 10**self._lowest_yrange
            higher = 10**self._highest_yrange
        if self.flare_summary.shape[0]!=0:
            if self.flare_summary['Trigger'].iloc[-1] in list(self.goes['time_tag'].iloc[-30:]):
                self.flare_trigger_plot.setData([pd.Timestamp(self.flare_summary['Trigger'].iloc[-1]).timestamp()]*2, [lower, higher])
                self.flare_trigger_plot.setAlpha(1, False)
            if self.flare_summary['Trigger'].iloc[-1] not in list(self.goes['time_tag'].iloc[-30:]):
                self.flare_trigger_plot.setData([self.time_tags[0]]*2, [lower, higher])
                self.flare_trigger_plot.setAlpha(0, False)
            if pd.Timestamp(self.flare_summary['Realtime Trigger'].iloc[-1]).timestamp() > pd.Timestamp(self.goes['time_tag'].iloc[-30]).timestamp():
                self.flare_realtrigger_plot.setData([pd.Timestamp(self.flare_summary['Realtime Trigger'].iloc[-1]).timestamp()]*2, [lower, higher])
                self.flare_realtrigger_plot.setAlpha(1, False)
            if pd.Timestamp(self.flare_summary['Realtime Trigger'].iloc[-1]).timestamp() <= pd.Timestamp(self.goes['time_tag'].iloc[-30]).timestamp():
                self.flare_realtrigger_plot.setData([self.time_tags[0]]*2, [lower, higher])
                self.flare_realtrigger_plot.setAlpha(0, False)
        else:
            self.flare_trigger_plot.setData([self.time_tags[0]]*2, [lower, higher])
            self.flare_trigger_plot.setAlpha(0, False)
            self.flare_realtrigger_plot.setData([self.time_tags[0]]*2, [lower, higher])
            self.flare_realtrigger_plot.setAlpha(0, False)
    
    def update_temp_em_trigger_plots(self):
        ''' Updates the trigger lines for temp and emission measure plots. Separate from GOES and ESP because these plots
        do not change from log to linear.
        '''
        if self.flare_summary.shape[0]!=0:
            if self.flare_summary['Trigger'].iloc[-1] in list(self.goes['time_tag'].iloc[-30:]):
                self.flare_trigger_tempplot.setData([pd.Timestamp(self.flare_summary['Trigger'].iloc[-1]).timestamp()]*2, [self.line_min_temp, self.line_max_temp])
                self.flare_trigger_tempplot.setAlpha(1, False)
                self.flare_trigger_emplot.setData([pd.Timestamp(self.flare_summary['Trigger'].iloc[-1]).timestamp()]*2, [self.line_min_em, self.line_max_em])
                self.flare_trigger_emplot.setAlpha(1, False)
            if self.flare_summary['Trigger'].iloc[-1] not in list(self.goes['time_tag'].iloc[-30:]):
                self.flare_trigger_tempplot.setData([self.time_tags[0]]*2, [self.line_min_temp, self.line_max_temp])
                self.flare_trigger_tempplot.setAlpha(0, False)
                self.flare_trigger_emplot.setData([self.time_tags[0]]*2, [self.line_min_em, self.line_max_em])
                self.flare_trigger_emplot.setAlpha(0, False)
            if pd.Timestamp(self.flare_summary['Realtime Trigger'].iloc[-1]).timestamp() > pd.Timestamp(self.goes['time_tag'].iloc[-30]).timestamp():
                self.flare_realtrigger_tempplot.setData([pd.Timestamp(self.flare_summary['Realtime Trigger'].iloc[-1]).timestamp()]*2, [self.line_min_temp, self.line_max_temp])
                self.flare_realtrigger_tempplot.setAlpha(1, False)
                self.flare_realtrigger_emplot.setData([pd.Timestamp(self.flare_summary['Realtime Trigger'].iloc[-1]).timestamp()]*2, [self.line_min_em, self.line_max_em])
                self.flare_realtrigger_emplot.setAlpha(1, False)
            if pd.Timestamp(self.flare_summary['Realtime Trigger'].iloc[-1]).timestamp() <= pd.Timestamp(self.goes['time_tag'].iloc[-30]).timestamp():
                self.flare_realtrigger_tempplot.setData([self.time_tags[0]]*2, [self.line_min_temp, self.line_max_temp])
                self.flare_realtrigger_tempplot.setAlpha(0, False)
                self.flare_realtrigger_emplot.setData([self.time_tags[0]]*2, [self.line_min_em, self.line_max_em])
                self.flare_realtrigger_emplot.setAlpha(0, False)
        else:
            self.flare_trigger_tempplot.setData([self.time_tags[0]]*2, [self.line_min_temp, self.line_max_temp])
            self.flare_trigger_tempplot.setAlpha(0, False)
            self.flare_trigger_emplot.setData([self.time_tags[0]]*2, [self.line_min_em, self.line_max_em])
            self.flare_trigger_emplot.setAlpha(0, False)
            self.flare_realtrigger_tempplot.setData([self.time_tags[0]]*2, [self.line_min_temp, self.line_max_temp])
            self.flare_realtrigger_tempplot.setAlpha(0, False)
            self.flare_realtrigger_emplot.setData([self.time_tags[0]]*2, [self.line_min_em, self.line_max_em])
            self.flare_realtrigger_emplot.setAlpha(0, False)
            
    def update_eve_trigger_plots(self):
        ''' Updates the trigger lines whenever the EVE plot is updated. This will be called after updating the EVE plot,
        and whenever we switch from log to linear.
        '''
        if self.flare_summary.shape[0]!=0:
            if self.flare_summary['Trigger'].iloc[-1] in list(self.goes['time_tag'].iloc[-30:]):
                self.flare_trigger_eveplot0.setData([pd.Timestamp(self.flare_summary['Trigger'].iloc[-1]).timestamp()]*2, [self.line_min_eve0, self.line_max_eve0])
                self.flare_trigger_eveplot30.setData([pd.Timestamp(self.flare_summary['Trigger'].iloc[-1]).timestamp()]*2, [self.line_min_eve30, self.line_max_eve30])
                self.flare_trigger_eveplot0.setAlpha(1, False)
                self.flare_trigger_eveplot30.setAlpha(1, False)
            if self.flare_summary['Trigger'].iloc[-1] not in list(self.goes['time_tag'].iloc[-30:]):
                self.flare_trigger_eveplot0.setData([self.new_eve_time_tags[0]]*2, [self.line_min_eve0, self.line_max_eve0])
                self.flare_trigger_eveplot30.setData([self.new_eve_time_tags[0]]*2, [self.line_min_eve30, self.line_max_eve30])
                self.flare_trigger_eveplot0.setAlpha(0, False)
                self.flare_trigger_eveplot30.setAlpha(0, False)
            if pd.Timestamp(self.flare_summary['Realtime Trigger'].iloc[-1]).timestamp() > pd.Timestamp(self.goes['time_tag'].iloc[-30]).timestamp():
                self.flare_realtrigger_eveplot0.setData([pd.Timestamp(self.flare_summary['Realtime Trigger'].iloc[-1]).timestamp()]*2, [self.line_min_eve0, self.line_max_eve0])
                self.flare_realtrigger_eveplot30.setData([pd.Timestamp(self.flare_summary['Realtime Trigger'].iloc[-1]).timestamp()]*2, [self.line_min_eve30, self.line_max_eve30])
                self.flare_realtrigger_eveplot0.setAlpha(1, False)
                self.flare_realtrigger_eveplot30.setAlpha(1, False)
            if pd.Timestamp(self.flare_summary['Realtime Trigger'].iloc[-1]).timestamp() <= pd.Timestamp(self.goes['time_tag'].iloc[-30]).timestamp():
                self.flare_realtrigger_eveplot0.setData([self.new_eve_time_tags[0]]*2, [self.line_min_eve0, self.line_max_eve0])
                self.flare_realtrigger_eveplot30.setData([self.new_eve_time_tags[0]]*2, [self.line_min_eve30, self.line_max_eve30])
                self.flare_realtrigger_eveplot0.setAlpha(0, False)
                self.flare_realtrigger_eveplot30.setAlpha(0, False)
        else:
            self.flare_trigger_eveplot0.setData([self.new_eve_time_tags[0]]*2, [self.line_min_eve0, self.line_max_eve0])
            self.flare_trigger_eveplot0.setAlpha(0, False)
            self.flare_trigger_eveplot30.setData([self.new_eve_time_tags[0]]*2, [self.line_min_eve30, self.line_max_eve30])
            self.flare_trigger_eveplot30.setAlpha(0, False)     
            
    def _plot_hic_launch_lines(self, plotitem, line_min, line_max):
        ''' Given a specific plotItem and its min/max values, update the launch line plot for HIC.
        '''
        if (list(self.goes['time_tag'])[-1]<=self.coming_launch_time_hic) and \
            (self._flare_prediction_state != "post-launch") and \
                not hasattr(self,"_launched"):
            plotitem.setData([pd.Timestamp(self.coming_launch_time_hic).timestamp()]*2, 
                                            [line_min, line_max], 
                                            pen=pg.mkPen('orange', width=5))
        else:
            pen_details = {"color":'orange',"width":4} if hasattr(self,"_launched") else {"color":(100,100,100),"width":4,"style":QtCore.Qt.PenStyle.DotLine}
            plotitem.setData([pd.Timestamp(self.coming_launch_time_hic).timestamp()]*2, 
                                           [line_min, line_max], 
                                            pen=pg.mkPen(**pen_details))
        plotitem.setAlpha(1, False)
        
    def _plot_foxsi_launch_lines(self, plotitem, line_min, line_max):
        ''' Given a specific plotItem and its min/max values, update the launch line plot for FOXSI.
        '''
        if (list(self.goes['time_tag'])[-1]<=self.coming_launch_time) and \
            (self._flare_prediction_state != "post-launch") and \
                not hasattr(self,"_launched"):
            plotitem.setData([pd.Timestamp(self.coming_launch_time).timestamp()]*2, 
                                            [line_min, line_max], 
                                            pen=pg.mkPen('g', width=5))
        else:
            pen_details = {"color":'g',"width":4} if hasattr(self,"_launched") else {"color":(100,100,100),"width":4,"style":QtCore.Qt.PenStyle.DotLine}
            plotitem.setData([pd.Timestamp(self.coming_launch_time).timestamp()]*2, 
                                           [line_min, line_max], 
                                            pen=pg.mkPen(**pen_details))
        plotitem.setAlpha(1, False)
        
    def update_temp_em_launch_plots(self):
        ''' Call function for updating the launch line plots for temp and emission measure.
        '''
        if self.flare_summary.shape[0] != 0:
            #setting launch lines to the right time
            if hasattr(self,"coming_launch_time") and (list(self.goes['time_tag'])[-30]<=self.coming_launch_time):
                self._plot_foxsi_launch_lines(self.FOXSI_launch_tempplot, self.line_min_temp, self.line_max_temp)
                self._plot_foxsi_launch_lines(self.FOXSI_launch_emplot, self.line_min_em, self.line_max_em)
            if hasattr(self, "coming_launch_time") and (list(self.goes['time_tag'])[-30]<=self.coming_launch_time):
                self._plot_hic_launch_lines(self.HIC_launch_tempplot, self.line_min_temp, self.line_max_temp)
                self._plot_hic_launch_lines(self.HIC_launch_emplot, self.line_min_em, self.line_max_em)
            #removing launch lines when they are out of range
            if hasattr(self,"coming_launch_time") and (list(self.goes['time_tag'])[-30]>self.coming_launch_time):
                self.FOXSI_launch_tempplot.setData([np.nan]*2, [self.line_min_temp, self.line_max_temp])
                self.FOXSI_launch_tempplot.setAlpha(0, False)
                self.FOXSI_launch_emplot.setData([np.nan]*2, [self.line_min_em, self.line_max_em])
                self.FOXSI_launch_emplot.setAlpha(0, False)
                del self.coming_launch_time
                if hasattr(self,"_launched"):
                    del self._launched
            #if self.flare_summary['FOXSI Obs Start'].iloc[-1] not in list(self.goes['time_tag'].iloc[-30:]):
            if hasattr(self,"coming_launch_time") and (list(self.goes['time_tag'])[-30]>self.coming_launch_time_hic): 
                self.HIC_launch_tempplot.setData([np.nan]*2, [self.line_min_temp, self.line_max_temp])
                self.HIC_launch_tempplot.setAlpha(0, False)
                self.HIC_launch_emplot.setData([np.nan]*2, [self.line_min_em, self.line_max_em])
                self.HIC_launch_emplot.setAlpha(0, False)
                del self.coming_launch_time_hic
        else:
              self.FOXSI_launch_tempplot.setData([np.nan]*2, [self.line_min_temp, self.line_max_temp])
              self.FOXSI_launch_tempplot.setAlpha(0, False)
              self.FOXSI_launch_emplot.setData([np.nan]*2, [self.line_min_em, self.line_max_em])
              self.FOXSI_launch_emplot.setAlpha(0, False)
              self.HIC_launch_tempplot.setData([np.nan]*2, [self.line_min_temp, self.line_max_temp])
              self.HIC_launch_tempplot.setAlpha(0, False)
              self.HIC_launch_emplot.setData([np.nan]*2, [self.line_min_em, self.line_max_em])
              self.HIC_launch_emplot.setAlpha(0, False)
              
    def update_eve_launch_plots(self):
        ''' Updates the EVE launch lines. Separate so that it can change immediately when switching from log/linear.
        '''
        if self.flare_summary.shape[0] != 0:
            #setting launch lines to the right time
            if hasattr(self,"coming_launch_time") and (list(self.goes['time_tag'])[-30]<=self.coming_launch_time):
                self._plot_foxsi_launch_lines(self.FOXSI_launch_eveplot0, self.line_min_eve0, self.line_max_eve0)
                self._plot_foxsi_launch_lines(self.FOXSI_launch_eveplot30, self.line_min_eve30, self.line_max_eve30)
            if hasattr(self, "coming_launch_time") and (list(self.goes['time_tag'])[-30]<=self.coming_launch_time):
                self._plot_hic_launch_lines(self.HIC_launch_eveplot0, self.line_min_eve0, self.line_max_eve0)
                self._plot_hic_launch_lines(self.HIC_launch_eveplot30, self.line_min_eve30, self.line_max_eve30)
            #removing launch lines when they are out of range
            if hasattr(self,"coming_launch_time") and (list(self.goes['time_tag'])[-30]>self.coming_launch_time):
                self.FOXSI_launch_eveplot0.setData([np.nan]*2, [self.line_min_eve0, self.line_max_eve0])
                self.FOXSI_launch_eveplot0.setAlpha(0, False)
                self.FOXSI_launch_eveplot30.setData([np.nan]*2, [self.line_min_eve30, self.line_max_eve30])
                self.FOXSI_launch_eveplot30.setAlpha(0, False)
            #if self.flare_summary['FOXSI Obs Start'].iloc[-1] not in list(self.goes['time_tag'].iloc[-30:]):
            if hasattr(self,"coming_launch_time") and (list(self.goes['time_tag'])[-30]>self.coming_launch_time_hic): 
                self.HIC_launch_eveplot0.setData([np.nan]*2, [self.line_min_eve0, self.line_max_eve0])
                self.HIC_launch_eveplot0.setAlpha(0, False)
                self.HIC_launch_eveplot30.setData([np.nan]*2, [self.line_min_eve30, self.line_max_eve30])
                self.HIC_launch_eveplot30.setAlpha(0, False)
        else:
              self.FOXSI_launch_eveplot0.setData([np.nan]*2, [self.line_min_eve0, self.line_max_eve0])
              self.FOXSI_launch_eveplot0.setAlpha(0, False)
              self.FOXSI_launch_eveplot30.setData([np.nan]*2, [self.line_min_eve30, self.line_max_eve30])
              self.FOXSI_launch_eveplot30.setAlpha(0, False)
              self.HIC_launch_eveplot0.setData([np.nan]*2, [self.line_min_eve0, self.line_max_eve0])
              self.HIC_launch_eveplot0.setAlpha(0, False)
              self.HIC_launch_eveplot30.setData([np.nan]*2, [self.line_min_eve30, self.line_max_eve30])
              self.HIC_launch_eveplot30.setAlpha(0, False)
        
    
    def update_launch_plot(self):
        if self._logy:
            lower = self._lowest_yrange
            higher = self._highest_yrange
        else:
            lower = 10**self._lowest_yrange
            higher = 10**self._highest_yrange
        if self.flare_summary.shape[0] != 0:
            #setting launch lines to the right time
            if hasattr(self,"coming_launch_time") and (list(self.goes['time_tag'])[-30]<=self.coming_launch_time):
                self._plot_foxsi_launch_lines(self.FOXSI_launch_plot, lower, higher)
            if hasattr(self, "coming_launch_time") and (list(self.goes['time_tag'])[-30]<=self.coming_launch_time):
                self._plot_hic_launch_lines(self.HIC_launch_plot, lower, higher)
            #removing launch lines when they are out of range
            if hasattr(self,"coming_launch_time") and (list(self.goes['time_tag'])[-30]>self.coming_launch_time):
                self.FOXSI_launch_plot.setData([np.nan]*2, [lower, higher])
                self.FOXSI_launch_plot.setAlpha(0, False)
            #if self.flare_summary['FOXSI Obs Start'].iloc[-1] not in list(self.goes['time_tag'].iloc[-30:]):
            if hasattr(self,"coming_launch_time") and (list(self.goes['time_tag'])[-30]>self.coming_launch_time_hic):
                self.HIC_launch_plot.setData([np.nan]*2, [lower, higher])
                self.HIC_launch_plot.setAlpha(0, False)  
        else:
              self.FOXSI_launch_plot.setData([np.nan]*2, [lower, higher])
              self.FOXSI_launch_plot.setAlpha(0, False)

        
    def save_data(self):
        
        self.flare_summary.to_csv(os.path.join(PACKAGE_DIR, "SessionSummaries", self.foldername, "timetag_summary.csv"))
        self.goes.to_csv(os.path.join(PACKAGE_DIR, "SessionSummaries", self.foldername, "GOES.csv"))
        self.fai_summary.to_csv(os.path.join(PACKAGE_DIR, "SessionSummaries", self.foldername, 'fai_summary.csv'))
        if not self.no_eovsa:
            self.eovsa.to_csv(os.path.join(PACKAGE_DIR, "SessionSummaries", self.foldername, "EOVSA.csv"))
        if not self.no_eve:
            self.eve.to_csv(os.path.join(PACKAGE_DIR, "SessionSummaries", self.foldername, "EVE.csv"))
        
            
        
	