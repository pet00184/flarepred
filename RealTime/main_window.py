""" The main GUI window class for the flare prediction package. """

import pandas as pd
from PyQt6 import QtWidgets, QtCore
import realtime_flare_trigger as rft
import GOES_data_upload as GOES_data
import EOVSA_data_upload as EOVSA_data
import post_analysis as pa
from run_realtime_algorithm import post_analysis, utc_time_folder
from QTimeWidget import QTimeWidget
from QStatusWidget import QStatusWidget
from QAlertsWidget import QAlertsWidget
from QDataValues import QGOESValueWidget
from QLed import QLed
from QButtonsInteractions import QButtonsWidget
import os

_utc_folder = utc_time_folder() #automated folders based on time

class main_window(QtWidgets.QWidget):
    """ Designed to be the main window for the flare prediction GUI.

    This brings together the GOES plotting (historical or real time), the time display, and 
    start and stop plotting buttons. 

    Parameters
    ----------
        None

    Properties
    ----------
        plot : `realtime_flare_trigger.RealTimeTrigger` object
            The class that defined the GOES plotted data, fare triggers (essentially all the 
            important stuff).

    Example
    -------
    # imports
    from PyQt6 import QtWidgets
    from . import main_window
    from run_realtime_algorithm import post_analysis

    # initialise the PyQt application and then the main window
    app = QtWidgets.QApplication([])
    window = main_window()
    window.show()
    app.exec()

    # for some post processing of results once GUI window is closed
    post_analysis(utc_time_here)
    """
    def __init__(self, sound_file, no_eovsa=False):
        """ Initialise a grid on a widget and add different iterations of the QTimeWidget widget. """
        QtWidgets.QWidget.__init__(self)
        
        self.no_eovsa=no_eovsa #defining if we are including EOVSA or not for rft
        self.sound_file = sound_file #defining what sound we want to use

        self.setWindowTitle("FlarePred 3000 : Realtime Data")
        self.setStyleSheet("border-width: 2px; border-style: outset; border-radius: 10px; border-color: white; background-color: white;")
        self.setMinimumSize(600,400)

        # define main layouts for the status window, LED, buttons, times, and plot
        status_layout = QtWidgets.QGridLayout()
        led_layout = QtWidgets.QVBoxLayout()
        buttons_layout = QtWidgets.QGridLayout()
        datad_layout = QtWidgets.QGridLayout()
        time_layout = QtWidgets.QVBoxLayout()
        plot_layout = QtWidgets.QVBoxLayout()

        self.panels = dict()
        
        # widget for displaying the automated recommendation
        self._status_layout = self.layout_bkg(main_layout=status_layout, 
                                         panel_name="panel_status", 
                                         style_sheet_string=self._layout_style("grey", "white"))
        self.status = QStatusWidget()
        self.status.setStyleSheet("border-width: 0px;")
        self._status_layout.addWidget(self.status) # widget, -y, x
        self.status.mousePressEvent = self.click_on_status#lambda event:print('on')
        
        # widget for displaying the most recent goes values
        _datad_layout = self.layout_bkg(main_layout=datad_layout, 
                                         panel_name="panel_datad", 
                                         style_sheet_string=self._layout_style("grey", "white"))
        self.goes_values_window = QGOESValueWidget(title_label="GOES Value, Time, Real Time")
        self.goes_values_window.setStyleSheet("border-width: 0px;")
        _datad_layout.addWidget(self.goes_values_window)
        self.real_times = []

        # LED indicator
        self.led = QLed()
        led_layout.addWidget(self.led) # widget, -y, x

        # create time widget and add it to the appropriate layout
        _time_layout = self.layout_bkg(main_layout=time_layout, 
                                         panel_name="panel_time", 
                                         style_sheet_string=self._layout_style("grey", "white"))
        times = QTimeWidget()
        times.setStyleSheet("border-width: 0px;")
        self.panels["panel_time"].setMinimumSize(265,10) # stops the panel from stretching and squeezing when changing times
        _time_layout.addWidget(times) # widget, -y, x

        # setup the main plot and add to the layout
        self.plot = rft.RealTimeTrigger(self.data_source(no_eovsa=self.no_eovsa)[0], self.data_source(no_eovsa=self.no_eovsa)[1], _utc_folder, self.sound_file, self.no_eovsa)
        plot_layout.addWidget(self.plot) # widget, -y, x
        
        # create time widget and add it to the appropriate layout
        _buttons_layout = self.layout_bkg(main_layout=buttons_layout, 
                                         panel_name="panel_buttons", 
                                         style_sheet_string=self._layout_style("grey", "white"))
        buttons = QButtonsWidget(plotting_widget=self.plot, status_widget=self.status, led_widget=self.led)
        _buttons_layout.addWidget(buttons) # widget, -y, x

        # update the status initially with the manual status then connect the the changing status of the GOES data
        buttons.manual_stat(self.plot._flare_prediction_state)

        # when new data is plotted make sure to update the "latest value" display
        self.update_goes_values()
        self.plot.value_changed_new_xrsb.connect(self.update_goes_values)

        # widget for the individual alerts
        self.alerts = QAlertsWidget(self.plot.flare_alerts)
        self.plot.value_changed_alerts.connect(lambda : self.alerts.update_labels(self.plot.flare_alerts))

        # combine the status and LED layouts
        status_values_and_led_layout = QtWidgets.QGridLayout()
        status_values_and_led_layout.addLayout(buttons_layout,0,0, alignment=QtCore.Qt.AlignmentFlag.AlignLeft)#-y, x
        status_values_and_led_layout.addLayout(status_layout,0,1, alignment=QtCore.Qt.AlignmentFlag.AlignLeft)#-y, x
        status_values_and_led_layout.addLayout(datad_layout,0,2, alignment=QtCore.Qt.AlignmentFlag.AlignLeft)#-y, x
        status_values_and_led_layout.addLayout(led_layout,0,3,1,1, alignment=QtCore.Qt.AlignmentFlag.AlignRight)#-y, x, 1 row, 1 columns

        # combine the button/radio and time layouts
        # buttons_layout = QtWidgets.QGridLayout()
        # buttons_layout.addLayout(buttons_layout,0,0,1,2)#-y, x, 1 row, 2 columns
        # buttons_and_time_layout.addLayout(time_layout,0,2,1,1)
        # br_and_time_layout.setColumnStretch(0,2)
        # buttons_and_time_layout.setColumnStretch(1,1)

        # now all together
        global_layout = QtWidgets.QGridLayout()
        global_layout.addLayout(plot_layout,0, 0, 12, 4)
        global_layout.addLayout(time_layout,12, 0, 1, 4)
        global_layout.addLayout(status_values_and_led_layout,13, 0, 1, 4)
        # global_layout.addLayout(buttons_layout,11, 0, 1, 4)

        # make sure the status and led stretch to the same width as the plot
        # status_values_and_led_layout.setColumnStretch(0,2)
        # status_values_and_led_layout.setColumnStretch(1,2)
        # status_values_and_led_layout.setColumnStretch(2,1)

        # actually display the layout
        self.setLayout(global_layout)
        unifrom_layout_stretch(global_layout, grid=True)
        unifrom_layout_stretch(self.plot.layout, grid=True)

    def data_source(self, no_eovsa=False):
        """ Return GOES and EOVSA realtime data sources. """
        if no_eovsa:
            return GOES_data.load_realtime_XRS, None
        else:
            return GOES_data.load_realtime_XRS, EOVSA_data.load_realtime_EOVSA
    
    def layout_bkg(self, main_layout, panel_name, style_sheet_string, grid=False):
            """ Adds a background widget (panel) to a main layout so border, colours, etc. can be controlled. """
            # create panel widget
            self.panels[panel_name] = QtWidgets.QWidget()

            # make the panel take up the main layout 
            main_layout.addWidget(self.panels[panel_name])

            # edit the main layout widget however you like
            self.panels[panel_name].setStyleSheet(style_sheet_string)

            # now return a new, child layout that inherits from the panel widget
            if grid:
                return QtWidgets.QGridLayout(self.panels[panel_name])
            else:
                return QtWidgets.QVBoxLayout(self.panels[panel_name])
            
    def click_on_status(self, event=None):
        """ Open a dialogue box when the status widget is clicked. """

        if hasattr(self,"dlg"):
            self.dlg.close()
            
        self.dlg = PopUpAlertsDialog(self.alerts)
        
        self.dlg.show() # show, not exec, otherwise GUI will wait for pop-up
        
    def _layout_style(self, border_colour, background_colour):
        """ Define a global layout style. """
        return f"border-width: 2px; border-style: outset; border-radius: 10px; border-color: {border_colour}; background-color: {background_colour};"
    
    def _goes_time_strings(self):
        """ 
        Get the data and real time of the goes data to display along 
        with the class. 
        """
        _time_strings = list(pd.to_datetime(self.plot.goes["time_tag"][-self.goes_values_window.number_of_vals:]).dt.strftime('%H:%M:%S'))
        self.real_times.append(self.plot.current_realtime.strftime('%H:%M:%S'))

        if len(self.real_times)>len(_time_strings):
            self.real_times = self.real_times[-self.goes_values_window.number_of_vals:]

        for c in range(1,len(self.real_times)+1):
            _time_strings[-1*c] += f" @ {self.real_times[-1*c]}"
        return _time_strings

    def update_goes_values(self):
        """ Used to update the goes values widget `self.***`."""
        _time_strings = self._goes_time_strings()
        self.goes_values_window.update_labels(self.plot.goes['xrsb'][-self.goes_values_window.number_of_vals:], _time_strings)

    def closeEvent(self, event):
        """ Ensure the pop-up window closes if the main window is closed. """
        if hasattr(self,"dlg"):
            self.dlg.close()
    
    
class main_window_historical(main_window):
    """ 
    Exactly the same as `main_window` but source historical data 
    instead of realtime data. 
    """
    def __init__(self, no_eovsa=True):
        self.no_eovsa = no_eovsa
        main_window.__init__(self, self.no_eovsa)
        self.setWindowTitle("FlarePred 3000 : Historical Data")
    
    def data_source(self, no_eovsa):
        """ Return the historical data source. """
        return GOES_data.FakeDataUpdator(GOES_data.historical_GOES_XRS).append_new_data, None

class PopUpAlertsDialog(QtWidgets.QDialog):
    """
    Define the pop-up window for the individual alerts widget. 

    Parameters
    ----------
    widget : `PyQt6.QtWidgets.QWidget`
            The widget to be displayed in the pop-up window.

    Example
    -------
    # taken from a class
    # make sure to close the previous one if trying to open again
    if hasattr(self,"dlg"):
        self.dlg.close()

    # allows the cycle of new alert statuses when pop-up is opened
    t_or_f = np.random.randint(2, size=self.alerts.number_of_alerts)
    self.alerts.update_labels(t_or_f)

    # add widget to the pop-up dialogue box
    self.dlg = PopUpAlertsDialog(self.alerts)
    # show, not exec, otherwise GUI will wait for pop-up
    self.dlg.show() 
    """
    def __init__(self, widget):
        super().__init__()
        # title the box
        self.setWindowTitle("Solar Activity Alerts")
        self.setStyleSheet("border-width: 2px; border-style: outset; border-radius: 10px; border-color: white; background-color: white;")
        # define layout
        self.layout = QtWidgets.QVBoxLayout()

        # define a layout for colour, etc.
        self.bkg = QtWidgets.QWidget()
        self.layout.addWidget(self.bkg)
        self.bkg.setStyleSheet("border-width: 2px; border-style: outset; border-radius: 10px; border-color: black; background-color: white;")
        self.sub_layout = QtWidgets.QVBoxLayout(self.bkg)

        # add widget to box
        self.sub_layout.addWidget(widget)
        # set main layout
        self.setLayout(self.layout)

def unifrom_layout_stretch(layout, grid=False):
    """ 
    Uniformly stretches the cells of a A Pyqt6 layout object.

    From GSE code.
    
    Parameters
    ----------
    layout : `PyQt6.QtWidgets.QLayout`
            A Pyqt6 layout object.

    grid : `bool`
            Is the layout a grid layout (rows and columns).
            Default: False
    Returns
    -------
    None
    """
    # make sure all cell sizes in the grid expand in proportion
    if grid:
        for col in range(layout.columnCount()):
                layout.setColumnStretch(col, 1)
        for row in range(layout.rowCount()):
                layout.setRowStretch(row, 1)
    else:
        for w in range(layout.count()):
            layout.setStretch(w, 1)
        layout.addStretch()

if __name__=="__main__":
    import sys

    sound_file = os.path.dirname(__file__) + '/'
    app = QtWidgets.QApplication([])
    if (len(sys.argv)==2) and (sys.argv[1]=="historical"):
        print("In HISTORICAL mode!")
        sound_file += "alert.wav"
        window = main_window_historical(sound_file, no_eovsa=True)
    elif (len(sys.argv)==2) and (sys.argv[1]=="no_eovsa"):
        print("In REALTIME mode! NO EOVSA DATA")
        sound_file += "alert.wav"
        window = main_window(sound_file, no_eovsa=True)
    elif (len(sys.argv)==2) and (sys.argv[1]=="office_mode"):
        print("In REALTIME mode! **The Office mode**")
        sound_file += "office.wav"
        window = main_window(sound_file, no_eovsa=False)
    else:
        print("In REALTIME mode!")
        sound_file += "alert.wav"
        window = main_window(sound_file, no_eovsa=False)
    
    window.show()
    app.exec()
    post_analysis(_utc_folder)
