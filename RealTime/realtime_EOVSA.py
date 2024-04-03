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
    
    ms_timing = 4000 #amount of ms between each new data download.

    def __init__(self, eovsa_data, eve_data, foldername, parent=None):
        QtWidgets.QWidget.__init__(self,parent)
            
        if not os.path.exists(os.path.join(PACKAGE_DIR, "SessionSummaries_EOVSAgui", foldername)):
            os.makedirs(os.path.join(PACKAGE_DIR, "SessionSummaries_EOVSAgui", foldername))
         
        #defining data:
        self.EOVSA_data = eovsa_data
        self.EVE_data = eve_data
        self.foldername = foldername
        
        #initial loading of the data: 
        self.load_eovsa_data(reload=False)
        self.load_eve_data(reload=False)
        self._logy = True
        
        #initial plotting of data: 
        #initializing plot: 
        self.layout = QtWidgets.QGridLayout()

        self.evegraph30 = pg.PlotWidget(axisItems={'bottom': pg.DateAxisItem()})
        self.eovsagraph = pg.PlotWidget(axisItems={'bottom': pg.DateAxisItem()})

        self.layout.addWidget(self.evegraph30, 0, 0, 1, 1)
        self.layout.addWidget(self.eovsagraph, 0, 1, 1, 1)
        self.setLayout(self.layout)

        #prepare EOVSA widget
        self.eovsagraph.setMouseEnabled(x=False, y=False)  # Disable mouse panning & zooming
    
        self.eovsagraph.setBackground('w')
        styles = {'color':'k', 'font-size':'20pt', "units":None} 
        self.eovsagraph.setLabel('left', 'amplitude sums', **styles)
        self.eovsagraph.setLabel('bottom', 'Time', **styles)
        self.eovsagraph.setTitle(f'EOVSA', color='k', size='24pt')
        self.eovsagraph.addLegend()
        self.eovsagraph.showGrid(x=True, y=True)
        self.eovsagraph.getAxis('left').enableAutoSIPrefix(enable=False)
        
        # # Prepare EVE30 widget
        self.evegraph30.setMouseEnabled(x=False, y=False)  # Disable mouse panning & zooming

        self.evegraph30.setBackground('w')
        styles = {'color':'k', 'font-size':'20pt', "units":None}
        self.evegraph30.setLabel('left', 'Raw Counts', **styles)
        self.evegraph30.setLabel('bottom', 'Time', **styles)
        self.evegraph30.setTitle(f'EVE ESP 30nm', color='k', size='24pt')
        self.evegraph30.addLegend()
        self.evegraph30.showGrid(x=True, y=True)
        self.evegraph30.getAxis('left').enableAutoSIPrefix(enable=False)

        self.display_eve30()
        self.display_eovsa()
        self.xlims()
        
        
        #PLOTTING EOVSA: 
        self.eovsatime_tags = [pd.Timestamp(str(date)).timestamp() for date in self.eovsa['time']]
        self.eovsa1_data = self.eovsaplot(self.eovsatime_tags, self.eovsa['1-7 GHz'], color='purple', plotname='1-7 GHz')
        self.eovsa2_data = self.eovsaplot(self.eovsatime_tags, self.eovsa['7-13 GHz'], color='blue', plotname='7-13 GHz')
        self.eovsa3_data = self.eovsaplot(self.eovsatime_tags, self.eovsa['13-18 GHz'], color='green', plotname='13-18 GHz')
    
        self.eovsa_alert = self.eovsaplot([self.eovsatime_tags[0]]*2, [self.line_min_eovsa, self.line_max_eovsa], color='k', plotname='EOVSA Flare Trigger')
        self.eovsa_alert.setAlpha(0, False)
            
        # #PLOTTING EVE:
        self.evetime_tags = [pd.Timestamp(str(date)).timestamp() for date in self.eve['UTC_TIME']]
        self.eve30_data = self.eveplot30(self.evetime_tags, self.eve['ESP_30_COUNTS'], color='cyan', plotname='ESP 30 nm')
        self.eve_line = self.eveplot30([self.evetime_tags[0]]*2, [self.line_min_eve30, self.line_max_eve30], color='k', plotname=None)
        self.eve_line.setAlpha(0, False)
        
        #updating data
        self.timer = QtCore.QTimer()
        self.timer.setInterval(self.ms_timing)
        self.timer.timeout.connect(self._update)
        self.timer.start()
        
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
        
    def display_eovsa(self):
        ''' Sets the ylimits for the EOVSA plot. If plot is in log mode, it moves to that.
        '''
        self.min_eovsa, self.max_eovsa = np.nanmax([1e3, np.nanmin(self.eovsa_current['13-18 GHz']) * 0.9]), np.nanmax(self.eovsa_current['1-7 GHz']) * 1.1
        self.line_min_eovsa, self.line_max_eovsa = np.nanmax([1e3, np.nanmin(self.eovsa_current['13-18 GHz']) * 0.8]), np.nanmax(self.eovsa_current['1-7 GHz']) * 1.2
        if self._logy:
            self.eovsagraph.setLogMode(False, True)
            self.eovsagraph.plotItem.vb.setLimits(yMin=self._log_data(self.min_eovsa), yMax=self._log_data(self.max_eovsa))
        else:
            self.eovsagraph.setLogMode(False, False)
            self.eovsagraph.plotItem.vb.setLimits(yMin=self.min_eovsa, yMax=self.max_eovsa)
        self.eovsagraph.showAxis('top')
        self.eovsagraph.getAxis('top').setStyle(showValues=False)
        self.eovsagraph.getAxis('top').setGrid(False)
        self.eovsagraph.showAxis('right')
        self.eovsagraph.getAxis('right').setGrid(False)
        self.eovsagraph.getAxis('right').enableAutoSIPrefix(enable=False)
        self.eovsagraph.plot()
 

    def xlims(self):
        """ Control the x-limits for plots. """
        _now = self._get_datetime_now()
        xmin = pd.Timestamp(_now-timedelta(minutes=30)).timestamp()
        xmax = pd.Timestamp(_now).timestamp()
        _plot_offest = -60 #seconds, for some reason the plot extends by about this much :(
        self.eovsagraph.plotItem.setXRange(xmin, xmax + _plot_offest)
        self.evegraph30.plotItem.setXRange(xmin, xmax + _plot_offest)

    def _log_data(self, array):
        """ Check if the data is to be logged with `self._logy`."""
        if self._logy:
            log = np.log10(array)
            return log
        return array
        
    def eovsaplot(self, x, y, color, plotname):
        pen = pg.mkPen(color=color, width=5)
        return self.eovsagraph.plot(x, y, name=plotname, pen=pen)
        
    def eveplot30(self, x, y, color, plotname):
        pen = pg.mkPen(color=color, width=5)
        return self.evegraph30.plot(x, y, name=plotname, pen=pen)
            
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
        self.load_eovsa_data()
        self.check_for_new_eovsa_data()
        self.load_eve_data()
        self.check_for_new_eve_data()
        if self.new_eovsa_data:
            self.eovsa_plot_update()
            self.check_for_eovsa_alert()
            self.eovsa_alert_update()
        if self.new_eve_data:
            self.eve_plot_update()
        self.xlims()
        self.update()
        
    def eovsa_plot_update(self):
        self.new_eovsa_time_tags = [pd.Timestamp(str(date)).timestamp() for date in self.eovsa['time']]
        self.new_eovsa1 = np.array(self.eovsa['1-7 GHz'])
        self.new_eovsa2 = np.array(self.eovsa['7-13 GHz'])
        self.new_eovsa3 = np.array(self.eovsa['13-18 GHz'])
        
        self.display_eovsa()
        self.eovsa1_data.setData(self.new_eovsa_time_tags, self.new_eovsa1)
        self.eovsa2_data.setData(self.new_eovsa_time_tags, self.new_eovsa2)
        self.eovsa3_data.setData(self.new_eovsa_time_tags, self.new_eovsa3)
        
    def eovsa_alert_update(self):
        if self.eovsa_current_alert == False and self.eovsa_past_alert == False:
            self.eovsa_alert.setData([pd.Timestamp(str(self.eovsa.iloc[0]['time'])).timestamp()]*2, [self.line_min_eovsa, self.line_max_eovsa])
            self.eovsa_alert.setAlpha(0, False)
        if self.eovsa_current_alert == True:
            self.eovsa_alert.setData([pd.Timestamp(str(self.eovsa.iloc[self.eovsa_alert_loc]['time'])).timestamp()]*2, [self.line_min_eovsa, self.line_max_eovsa])
            self.eovsa_alert.setAlpha(1, False)
        if self.eovsa_past_alert == True:
            self.eovsa_alert.setData([pd.Timestamp(str(self.eovsa.iloc[self.eovsa_alert_loc]['time'])).timestamp()]*2, [self.line_min_eovsa, self.line_max_eovsa])
            self.eovsa_alert.setAlpha(0.5, False)
            
    def eve_plot_update(self):
        self.new_eve_time_tags = [pd.Timestamp(str(date)).timestamp() for date in self.eve['UTC_TIME']]
        self.new_eve30 = np.array(self.eve['ESP_30_COUNTS'])

        self.display_eve30()
        self.eve30_data.setData(self.new_eve_time_tags, self.new_eve30)
        self.eve_line.setData([self.new_eve_time_tags[0]]*2, [self.line_min_eve30, self.line_min_eve30])

    def no_eve_plot_update(self):
        new_xloc = pd.Timestamp(self._get_datetime_now()-timedelta(minutes=15)).timestamp()
        self.evetext.setPos(new_xloc, .5)

        
    def save_data(self):
        self.eovsa.to_csv(os.path.join(PACKAGE_DIR, "SessionSummaries_EOVSAgui", self.foldername, "EOVSA.csv"))
        self.eve.to_csv(os.path.join(PACKAGE_DIR, "SessionSummaries_EOVSAgui", self.foldername, "EVE.csv"))