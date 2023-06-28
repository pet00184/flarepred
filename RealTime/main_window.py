""" The main GUI window class for the flare prediction package. """

from PyQt6 import QtWidgets, QtCore
import realtime_flare_trigger as rft
import GOES_data_upload as GOES_data
import post_analysis as pa
from run_realtime_algorithm import post_analysis
from QTimeWidget import QTimeWidget
from QLed import QLed

HISTORICAL = True
run_name = 'EXAMPLE_HISTORICAL_RUN2' #utilize this to specify your saved runs

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
            The class that defined the GOES plotted data, fare triggers (esentially all the 
            importnt stuff).

    Example
    -------
    # imports
    from PyQt6 import QtWidgets
    from . import main_window, post_analysis

    # initialise the PyQt application and then the main window
    app = QtWidgets.QApplication([])
    window = main_window()
    window.show()
    app.exec()

    # for some post processing of results once GUI window is closed
    post_analysis(run_name)
    """
    def __init__(self):
        """ Initialise a grid on a widget and add different iterations of the QTimeWidget widget. """
        QtWidgets.QWidget.__init__(self)

        self.setWindowTitle("FlarePred 3000")

        # define layouts for the buttons, times, and plot
        button_layout = QtWidgets.QGridLayout()
        time_layout = QtWidgets.QVBoxLayout()
        plot_layout = QtWidgets.QVBoxLayout()

        # create time widget and add it to the appropriate layout
        times = QTimeWidget()
        time_layout.addWidget(times) # widget, -y, x

        # setup the main plot and add to the layout
        _data = GOES_data.FakeDataUpdator(GOES_data.historical_GOES_XRS).append_new_data if HISTORICAL else GOES_data.load_realtime_XRS
        self.plot = rft.RealTimeTrigger(_data, run_name)
        plot_layout.addWidget(self.plot) # widget, -y, x

        # add buttons
        self.modalStartPlotDataButton = QtWidgets.QPushButton("Start plotting data", self)
        self.modalStopPlotDataButton = QtWidgets.QPushButton("Stop plotting data", self)
        self.startPlotUpdate() # to colour the buttons straight away, not essential
        self.startLaunchButton = QtWidgets.QPushButton("Launch", self)
        self.stopLaunchButton = QtWidgets.QPushButton("Stop Launch/Hold", self)
        # add buttons to layout
        button_layout.addWidget(self.modalStartPlotDataButton,0,0)
        button_layout.addWidget(self.modalStopPlotDataButton,0,1)
        button_layout.addWidget(self.startLaunchButton,1,0)
        button_layout.addWidget(self.stopLaunchButton,1,1)
        # make the buttons do something
        self.modalStartPlotDataButton.clicked.connect(self.startPlotUpdate)
        self.modalStopPlotDataButton.clicked.connect(self.stopPlotUpdate)
        self.startLaunchButton.clicked.connect(self.startLaunch)
        self.stopLaunchButton.clicked.connect(self.stopLaunch)

        # combine the button and time layouts
        button_and_time_layout = QtWidgets.QGridLayout()
        button_and_time_layout.addLayout(button_layout,0,0)#-y, x
        button_and_time_layout.addLayout(time_layout,0,1)

        # now all together
        global_layout = QtWidgets.QGridLayout()
        global_layout.addLayout(plot_layout,0,0)
        global_layout.addLayout(button_and_time_layout,1,0)

        # make sure the buttons and times stretch to the same width as the plot
        button_and_time_layout.setColumnStretch(0,1)

        # actually display the layout
        self.setLayout(global_layout)

    def startLaunch(self):
        print("Let's go get Lunch!")

    def stopLaunch(self):
        print("Let's stop going to get Lunch!")

    def startPlotUpdate(self):
        """
        Called when the `modalStartPlotDataButton` button is pressed.
        
        This starts a QTimer which calls `self.plot.update` with a cycle every `self.plot.ms_timing` 
        milliseconds. 

        [1] https://doc.qt.io/qtforpython/PySide6/QtCore/QTimer.html
        """

        # define what happens to GUI buttons and start call timer
        self.modalStartPlotDataButton.setStyleSheet('QPushButton {background-color: white; color: green;}')
        self.modalStopPlotDataButton.setStyleSheet('QPushButton {background-color: white; color: black;}')
        self.plot.timer = QtCore.QTimer()
        self.plot.timer.setInterval(self.plot.ms_timing) # fastest is every millisecond 
        self.plot.timer.timeout.connect(self.plot.update) # call self.plot.update every cycle
        self.plot.timer.start()

    def stopPlotUpdate(self):
        """
        Called when the `modalStopPlotDataButton` button is pressed.
        
        This stops a QTimer set by `self.startPlotUpdate()`. 
        """
        self.modalStartPlotDataButton.setStyleSheet('QPushButton {background-color: white; color: black;}')
        self.modalStopPlotDataButton.setStyleSheet('QPushButton {background-color: white; color: red;}')
        self.plot.timer.stop()
    
if __name__=="__main__":
    app = QtWidgets.QApplication([])
    window = main_window()
    window.show()
    app.exec()
    post_analysis(run_name)
