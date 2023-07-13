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

        # define layouts for the status window, LED, buttons, times, and plot
        status_layout = QtWidgets.QGridLayout()
        led_layout = QtWidgets.QVBoxLayout()
        radio_layout = QtWidgets.QGridLayout()
        button_layout = QtWidgets.QGridLayout()
        datad_layout = QtWidgets.QGridLayout()
        time_layout = QtWidgets.QVBoxLayout()
        plot_layout = QtWidgets.QVBoxLayout()

        # widget for displaying the automated recommendation
        self.status = QStatusWidget()
        status_layout.addWidget(self.status) # widget, -y, x
        
        # widget for displaying the most recent goes values
        self.goes_values_window = QValueWidget()
        datad_layout.addWidget(self.goes_values_window)

        # LED indicator
        self.led = QLed()
        led_layout.addWidget(self.led) # widget, -y, x

        # create time widget and add it to the appropriate layout
        times = QTimeWidget()
        time_layout.addWidget(times) # widget, -y, x

        # setup the main plot and add to the layout
        self.plot = rft.RealTimeTrigger(self.data_source(), _utc_folder)
        plot_layout.addWidget(self.plot) # widget, -y, x

        # update the status initially with the manual status then connect the the changing status of the GOES data
        self.manual_stat(self.plot._flare_prediction_state)
        self.plot.value_changed_signal_status.connect(self.update_stat)

        # when new data is plotted make sure to update the "latest value" display
        self.update_goes_values()
        self.plot.value_changed_new_xrsb.connect(self.update_goes_values)

        # add radio options
        self.xrsa_b = QtWidgets.QRadioButton("Follow XRSA and B", self)
        self.xrsa = QtWidgets.QRadioButton("Follow XRSA", self)
        self.xrsb = QtWidgets.QRadioButton("Follow XRSB", self)
        self.xrsa_b.setChecked(True)
        self.xrsa.setChecked(False)
        self.xrsb.setChecked(False)
        radio_layout.addWidget(self.xrsa_b,0,0)
        radio_layout.addWidget(self.xrsa,0,1)
        radio_layout.addWidget(self.xrsb,0,2)
        self.xrsa_b.clicked.connect(self.scale2xrsab)
        self.xrsa.clicked.connect(self.scale2xrsa)
        self.xrsb.clicked.connect(self.scale2xrsb)
        
        # add buttons
        self.startLaunchButton = QtWidgets.QPushButton("Launch", self)
        self.stopLaunchButton = QtWidgets.QPushButton("Stop Launch/Hold", self)
        # add buttons to layout
        button_layout.addWidget(self.startLaunchButton,0,0)#-y, x
        button_layout.addWidget(self.stopLaunchButton,0,1)
        # make the buttons do something
        self.startLaunchButton.clicked.connect(self.startLaunch)
        self.stopLaunchButton.clicked.connect(self.stopLaunch)

        # combine the status and LED layouts
        status_values_and_led_layout = QtWidgets.QGridLayout()
        status_values_and_led_layout.addLayout(status_layout,0,0, alignment=QtCore.Qt.AlignmentFlag.AlignLeft)#-y, x
        status_values_and_led_layout.addLayout(datad_layout,0,1, alignment=QtCore.Qt.AlignmentFlag.AlignLeft)#-y, x
        status_values_and_led_layout.addLayout(led_layout,0,2, alignment=QtCore.Qt.AlignmentFlag.AlignRight)

        # combine radio and buttons layouts
        radio_and_button_layout = QtWidgets.QGridLayout()
        radio_and_button_layout.addLayout(radio_layout,0,0)#-y, x
        radio_and_button_layout.addLayout(button_layout,1,0)

        # combine the button/radio and time layouts
        br_and_time_layout = QtWidgets.QGridLayout()
        br_and_time_layout.addLayout(radio_and_button_layout,0,0)#-y, x
        br_and_time_layout.addLayout(time_layout,0,1)

        # now all together
        global_layout = QtWidgets.QGridLayout()
        global_layout.addLayout(plot_layout,0,0)
        global_layout.addLayout(status_values_and_led_layout,1,0)
        global_layout.addLayout(br_and_time_layout,2,0)

        # make sure the buttons and times stretch to the same width as the plot
        br_and_time_layout.setColumnStretch(0,1) # col, stretch
        # make sure the status and led stretch to the same width as the plot
        status_values_and_led_layout.setColumnStretch(0,2)
        status_values_and_led_layout.setColumnStretch(1,2)
        status_values_and_led_layout.setColumnStretch(2,1)

        # actually display the layout
        self.setLayout(global_layout)

    def data_source(self):
        """ Return realtime data source. """
        return GOES_data.load_realtime_XRS

    def update_stat(self):
        """ Used to update the status widget `self.status`."""
        self.status.update_labels(self.plot._flare_prediction_state, self._man_stat)

        led_status = self._man_stat if self._man_stat in ["stop"] else self.plot._flare_prediction_state 
        self._man_stat = ""

        # if the same status keeps coming in don't want it to update all the time
        if hasattr(self, "old_led_status") and (led_status==self.old_led_status):
            return
        
        self.led.update_status(led_status)
        self._old_led_status = led_status

    def manual_stat(self, stat):
        """ 
        Used to update the status widget `self.status` from user interactions.

        Parameters
        ----------
        stat : `str`
            A string describing the status that is changed from user interaction.
        """
        self._man_stat = stat
        self.update_stat()

    def update_goes_values(self):
        """ Used to update the goes values widget `self.***`."""
        self.goes_values_window.update_labels(self.plot.xrsb['flux'][-self.goes_values_window.number_of_vals:])
    
    def scale2xrsab(self):
        self.plot._min_arr, self.plot._max_arr = "xrsa", "xrsb"
        self.plot.ylims()
        self.plot.update()
        
    def scale2xrsa(self):
        self.plot._min_arr, self.plot._max_arr = "xrsa", "xrsa"
        self.plot.ylims()
        self.plot.update()

    def scale2xrsb(self):
        self.plot._min_arr, self.plot._max_arr = "xrsb", "xrsb"
        self.plot.ylims()
        self.plot.update()

    def _include_startstop(self):
        """ A place for the start/stop buttons code. """
        startstop_layout = QtWidgets.QVBoxLayout()

        self.modalStartPlotDataButton = QtWidgets.QPushButton("Start plotting data", self)
        self.modalStopPlotDataButton = QtWidgets.QPushButton("Stop plotting data", self)
        self.startPlotUpdate() # to colour the buttons straight away, not essential

        startstop_layout.addWidget(self.modalStartPlotDataButton,0,0)
        startstop_layout.addWidget(self.modalStopPlotDataButton,0,1)

        self.modalStartPlotDataButton.clicked.connect(self.startPlotUpdate)
        self.modalStopPlotDataButton.clicked.connect(self.stopPlotUpdate)

        return startstop_layout
    
    def startLaunch(self):
        """ Called when `modalStartPlotDataButton` is pressed. """
        if (self.plot._flare_prediction_state!="post-launch") and (self.plot._flare_prediction_state=="triggered"):
            print(f"Launch initiated at {self.plot.current_realtime}. Let's go get Lunch!")
            self.manual_stat("Start launch")
            self.plot._button_press_pre_launch()
        elif (self.plot._flare_prediction_state!="post-launch") and (self.plot._flare_prediction_state=="pre-launch"):
            print("Launch already initiated.")
        else:
            # print("In post-launch, cannot start.")
            print("Now is not the time, only launch when triggered.")

    def stopLaunch(self):
        """ Called when `modalStopPlotDataButton` is pressed. """
        if self.plot._flare_prediction_state=="pre-launch":
            print(f"LAUNCH HELD AT {self.plot.current_realtime}. (Let's stop going to get Lunch!)")
            self.manual_stat("stop")
            self.plot.change_to_post_launch_state()
        else:
            print("Nothing to stop.")

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

        self.manual_stat(self.plot._flare_prediction_state)

    def stopPlotUpdate(self):
        """
        Called when the `modalStopPlotDataButton` button is pressed.
        
        This stops a QTimer set by `self.startPlotUpdate()`. 
        """
        self.modalStartPlotDataButton.setStyleSheet('QPushButton {background-color: white; color: black;}')
        self.modalStopPlotDataButton.setStyleSheet('QPushButton {background-color: white; color: red;}')
        self.plot.timer.stop()

        self.manual_stat("Stopped plotting data")
    
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
