""" The main GUI window class for the flare prediction package. """

import pandas as pd
from PyQt6 import QtWidgets, QtCore
import realtime_ANNA as rft
import GOES_data_upload as GOES_data
import EVE_data_upload as EVE_data
from run_realtime_algorithm import utc_time_folder
from QTimeWidget import QTimeWidget
from QANNAButtons import QButtonsWidget
import os
import glob

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

        self.setWindowTitle("ANNA")
        self.setStyleSheet("border-width: 2px; border-style: outset; border-radius: 10px; border-color: white; background-color: white;")
        self.setMinimumSize(600,400)

        # define main layouts for the status window, LED, buttons, times, and plot
        buttons_layout = QtWidgets.QGridLayout()
        time_layout = QtWidgets.QVBoxLayout()
        plot_layout = QtWidgets.QVBoxLayout()

        self.panels = dict()

        # create time widget and add it to the appropriate layout
        _time_layout = self.layout_bkg(main_layout=time_layout, 
                                         panel_name="panel_time", 
                                         style_sheet_string=self._layout_style("grey", "white"))
        times = QTimeWidget()
        times.setStyleSheet("border-width: 0px;")
        self.panels["panel_time"].setMinimumSize(265,10) # stops the panel from stretching and squeezing when changing times
        _time_layout.addWidget(times) # widget, -y, x

        # setup the main plot and add to the layout
        self.plot = rft.RealTimeTrigger(self.data_source()[0], self.data_source()[1], _utc_folder)
        plot_layout.addWidget(self.plot) # widget, -y, x
        
        # create time widget and add it to the appropriate layout
        _buttons_layout = self.layout_bkg(main_layout=buttons_layout, 
                                         panel_name="panel_buttons", 
                                         style_sheet_string=self._layout_style("grey", "white"))
        buttons = QButtonsWidget(plotting_widget=self.plot)
        _buttons_layout.addWidget(buttons) # widget, -y, x
        
        # combine the status and LED layouts
        status_values_and_led_layout = QtWidgets.QGridLayout()
        status_values_and_led_layout.addLayout(buttons_layout,0,0, alignment=QtCore.Qt.AlignmentFlag.AlignLeft)

        # now all together
        global_layout = QtWidgets.QGridLayout()
        global_layout.addLayout(plot_layout,0, 0, 8, 4)
        global_layout.addLayout(time_layout,8, 1, 1, 3)
        global_layout.addLayout(status_values_and_led_layout,8, 0, 1, 1)

        # actually display the layout
        self.setLayout(global_layout)
        unifrom_layout_stretch(global_layout, grid=True)
        unifrom_layout_stretch(self.plot.layout, grid=True)

    def data_source(self, no_eve=False):
        """ Return GOES and EOVSA realtime data sources. """
        return GOES_data.load_realtime_XRS, EVE_data.load_realtime_EVE
    
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
        """ Define a global layout style. """
        return f"border-width: 2px; border-style: outset; border-radius: 10px; border-color: {border_colour}; background-color: {background_colour};"
    

    def closeEvent(self, event):
        """ Ensure the pop-up window closes if the main window is closed. """
        if hasattr(self,"dlg"):
            self.dlg.close()

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
    print("Starting ANNA GUI!")
    window = main_window()
    
    window.show()
    app.exec()
    for filename in glob.glob('flaretest*'):
        os.remove(filename)
    for filename in glob.glob('LATEST_EVE*'):
        os.remove(filename)