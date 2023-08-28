""" The main GUI window class for the flare prediction package. """

from PyQt6 import QtWidgets, QtCore
import realtime_flare_trigger as rft
import GOES_data_upload as GOES_data
import post_analysis as pa
from run_realtime_algorithm import post_analysis, utc_time_folder
from QTimeWidget import QTimeWidget
from QStatusWidget import QStatusWidget
from QDataValues import QValueWidget
from QLed import QLed
from QButtonsInteractions import QButtonsWidget

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
    def __init__(self):
        """ Initialise a grid on a widget and add different iterations of the QTimeWidget widget. """
        QtWidgets.QWidget.__init__(self)

        self.setWindowTitle("FlarePred 3000 : Realtime Data")
        self.setStyleSheet("border-width: 2px; border-style: outset; border-radius: 10px; border-color: white; background-color: white;")

        # define main layouts for the status window, LED, buttons, times, and plot
        status_layout = QtWidgets.QGridLayout()
        led_layout = QtWidgets.QVBoxLayout()
        buttons_layout = QtWidgets.QGridLayout()
        datad_layout = QtWidgets.QGridLayout()
        time_layout = QtWidgets.QVBoxLayout()
        plot_layout = QtWidgets.QVBoxLayout()

        self.panels = dict()
        
        # widget for displaying the automated recommendation
        _status_layout = self.layout_bkg(main_layout=status_layout, 
                                         panel_name="panel_status", 
                                         style_sheet_string=self._layout_style("grey", "white"))
        self.status = QStatusWidget()
        self.status.setStyleSheet("border-width: 0px;")
        _status_layout.addWidget(self.status) # widget, -y, x
        
        # widget for displaying the most recent goes values
        _datad_layout = self.layout_bkg(main_layout=datad_layout, 
                                         panel_name="panel_datad", 
                                         style_sheet_string=self._layout_style("grey", "white"))
        self.goes_values_window = QValueWidget()
        self.goes_values_window.setStyleSheet("border-width: 0px;")
        _datad_layout.addWidget(self.goes_values_window)

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
        self.plot = rft.RealTimeTrigger(self.data_source(), _utc_folder)
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

        # combine the status and LED layouts
        status_values_and_led_layout = QtWidgets.QGridLayout()
        status_values_and_led_layout.addLayout(status_layout,0,0, alignment=QtCore.Qt.AlignmentFlag.AlignLeft)#-y, x
        status_values_and_led_layout.addLayout(datad_layout,0,1, alignment=QtCore.Qt.AlignmentFlag.AlignLeft)#-y, x
        status_values_and_led_layout.addLayout(led_layout,0,2,1,1, alignment=QtCore.Qt.AlignmentFlag.AlignRight)#-y, x, 1 row, 1 columns

        # combine the button/radio and time layouts
        buttons_and_time_layout = QtWidgets.QGridLayout()
        buttons_and_time_layout.addLayout(buttons_layout,0,0,1,2)#-y, x, 1 row, 2 columns
        buttons_and_time_layout.addLayout(time_layout,0,2,1,1)
        # br_and_time_layout.setColumnStretch(0,2)
        buttons_and_time_layout.setColumnStretch(1,1)

        # now all together
        global_layout = QtWidgets.QGridLayout()
        global_layout.addLayout(plot_layout,0,0)
        global_layout.addLayout(status_values_and_led_layout,1,0)
        global_layout.addLayout(buttons_and_time_layout,2,0)

        # make sure the status and led stretch to the same width as the plot
        status_values_and_led_layout.setColumnStretch(0,2)
        status_values_and_led_layout.setColumnStretch(1,2)
        # status_values_and_led_layout.setColumnStretch(2,1)

        # actually display the layout
        self.setLayout(global_layout)

    def data_source(self):
        """ Return realtime data source. """
        return GOES_data.load_realtime_XRS
    
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
            
    def _layout_style(self, border_colour, background_colour):
        return f"border-width: 2px; border-style: outset; border-radius: 10px; border-color: {border_colour}; background-color: {background_colour};"

    def update_goes_values(self):
        """ Used to update the goes values widget `self.***`."""
        self.goes_values_window.update_labels(self.plot.xrsb['flux'][-self.goes_values_window.number_of_vals:])
    
    
class main_window_historical(main_window):
    def __init__(self):
        main_window.__init__(self)
        self.setWindowTitle("FlarePred 3000 : Historical Data")
    
    def data_source(self):
        """ Return the historical data source. """
        return GOES_data.FakeDataUpdator(GOES_data.historical_GOES_XRS).append_new_data


if __name__=="__main__":
    import sys

    app = QtWidgets.QApplication([])
    if (len(sys.argv)==2) and (sys.argv[1]=="historical"):
        print("In HISTORICAL mode!")
        window = main_window_historical()
    else:
        print("In REALTIME mode!")
        window = main_window()
    window.show()
    app.exec()
    post_analysis(_utc_folder)
