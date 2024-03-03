"""
A widget to display different status conditions.
"""


#https://www.pythonguis.com/tutorials/pyqt6-creating-your-own-custom-widgets/
#https://doc.qt.io/qtforpython-5/PySide2/QtGui/QPainterPath.html
#https://coderslegacy.com/python/pyqt6-qlabel-widget/

import numpy as np
import pytz
import datetime
from PyQt6.QtWidgets import QWidget, QApplication, QSizePolicy,QPushButton,QGridLayout, QVBoxLayout, QLabel, QRadioButton, QButtonGroup
from PyQt6.QtCore import Qt, QSize, QTimer
from itertools import cycle


class QButtonsWidget(QWidget):
    """
    A widget to be added to a GUI to display the buttons we want.
    """
    def __init__(self, plotting_widget, status_widget, led_widget, parent=None, **kwargs):
        """ Constructs the widget and adds the buttons to the widget."""
        QWidget.__init__(self,parent, **kwargs)
        # self.setSizePolicy(
        #     QSizePolicy.Policy.MinimumExpanding,
        #     QSizePolicy.Policy.MinimumExpanding
        # )

        # these buttons interact with other GUI elements but were getting out of hand in the main window
        self.plot, self.status, self.led = plotting_widget, status_widget, led_widget

        # connect changing status in the GOES plot to an update for everything
        self.plot.value_changed_signal_status.connect(self.update_stat)

        # layout for all buttons
        self._layout = QGridLayout()

        # layout for radio buttons and press buttons 
        self.scale_radio_layout = QGridLayout()
        self.radio_layout = QGridLayout()
        self.button_layout = QGridLayout()

        # create the radio buttons and press buttons, add to individual layouts
        self._add_scale_radio_buttons()
        self._add_radio_buttons()
        self.add_buttons()

        # style the button widgets
        self.slabel.setStyleSheet(self._radio_style())
        self.log.setStyleSheet(self._radio_style())
        self.linear.setStyleSheet(self._radio_style())
        self.label.setStyleSheet(self._radio_style())
        self.xrsa_b.setStyleSheet(self._radio_style())
        self.xrsa.setStyleSheet(self._radio_style())
        self.xrsb.setStyleSheet(self._radio_style())
        self.startLaunchButton.setStyleSheet(self._button_style("black", "white"))
        self.stopLaunchButton.setStyleSheet(self._button_style("black", "white"))

        # add both button layouts to the main one
        self._layout.addLayout(self.scale_radio_layout,0,0)#-y, x
        self._layout.addLayout(self.radio_layout,1,0)#-y, x
        self._layout.addLayout(self.button_layout,2,0)

        # set the main layout
        self.setLayout(self._layout)

    def _radio_style(self):
        """ Define the style for the radio button widgets. """
        return "border-width: 0px; color: black;"
        
    def _button_style(self, border_colour, background_colour):
        """ Define the style for the press button widgets. """
        return f"border-width: 2px; border-style: outset; border-radius: 10px; color: black; border-color: {border_colour}; background-color: {background_colour};"

    def _add_scale_radio_buttons(self):
        """ 
        Define the radio buttons to change y-scale and add to 
        `self.scale_radio_layout`. 
        """
        self.radio_group1 = QButtonGroup(self)
        # add radio options
        self.slabel = QLabel("Y-scale: ")
        self.log = QRadioButton("log", self)
        self.linear = QRadioButton("linear", self)
        self.log.setChecked(True)
        self.linear.setChecked(False)
        self.scale_radio_layout.addWidget(self.slabel,0,0)
        self.scale_radio_layout.addWidget(self.log,0,1)
        self.scale_radio_layout.addWidget(self.linear,0,2)
        self.log.clicked.connect(self.logyscale)
        self.linear.clicked.connect(self.linearyscale)
        self.scale_radio_layout.setColumnStretch(0,3)
        self.scale_radio_layout.setColumnStretch(1,6)
        self.scale_radio_layout.setColumnStretch(2,6)
        self.radio_group1.addButton(self.log)
        self.radio_group1.addButton(self.linear)

    def logyscale(self):
        """ Change y-scale range of `self.plot` to log. """
        self.plot._logy = True
        self.plot.xrs_plot_update()
        
    def linearyscale(self):
        """ Change y-scale range of `self.plot` to linear. """
        self.plot._logy = False
        self.plot.xrs_plot_update()

    def _add_radio_buttons(self):
        """ Define the radio buttons and add to `self.radio_layout`. """
        self.radio_group2 = QButtonGroup(self)
        # add radio options
        self.label = QLabel("Focus on: ")
        self.xrsa_b = QRadioButton("XRSA and B", self)
        self.xrsa = QRadioButton("XRSA", self)
        self.xrsb = QRadioButton("XRSB", self)
        self.xrsa_b.setChecked(True)
        self.xrsa.setChecked(False)
        self.xrsb.setChecked(False)
        self.radio_layout.addWidget(self.label,0,0)
        self.radio_layout.addWidget(self.xrsa_b,0,1)
        self.radio_layout.addWidget(self.xrsa,0,2)
        self.radio_layout.addWidget(self.xrsb,0,3)
        self.xrsa_b.clicked.connect(self.scale2xrsab)
        self.xrsa.clicked.connect(self.scale2xrsa)
        self.xrsb.clicked.connect(self.scale2xrsb)
        self.radio_layout.setColumnStretch(0,3)
        self.radio_layout.setColumnStretch(1,6)
        self.radio_layout.setColumnStretch(2,5)
        self.radio_layout.setColumnStretch(3,5)
        self.radio_group2.addButton(self.xrsa_b)
        self.radio_group2.addButton(self.xrsa)
        self.radio_group2.addButton(self.xrsb)

    def scale2xrsab(self):
        """ Change y-limit range of `self.plot` to focus on both XRSA and B. """
        self.plot._min_arr, self.plot._max_arr = "xrsa", "xrsb"
        self.plot.display_goes()
        self.plot.xrs_plot_update()
        
    def scale2xrsa(self):
        """ Change y-limit range of `self.plot` to focus on both XRSA. """
        self.plot._min_arr, self.plot._max_arr = "xrsa", "xrsa"
        self.plot.display_goes()
        self.plot.xrs_plot_update()

    def scale2xrsb(self):
        """ Change y-limit range of `self.plot` to focus on both XRSB. """
        self.plot._min_arr, self.plot._max_arr = "xrsb", "xrsb"
        self.plot.display_goes()
        self.plot.xrs_plot_update()

    def add_buttons(self):
        """ Define the press buttons and add to `self.button_layout`. """
        # add buttons
        self.startLaunchButton = QPushButton("Launching Now", self)
        self.stopLaunchButton = QPushButton("Holding Launch", self)
        self.startCountdownButton = QPushButton("Starting Countdown", self)
        # add buttons to layout
        self.button_layout.addWidget(self.startCountdownButton,0,0)#-y, x
        self.button_layout.addWidget(self.startLaunchButton,0,1)
        self.button_layout.addWidget(self.stopLaunchButton,0,2)
        # make the buttons do something
        self.startCountdownButton.clicked.connect(self.startCountdown)
        self.startLaunchButton.clicked.connect(self.startLaunch)
        self.stopLaunchButton.clicked.connect(self.stopLaunch)

    def startLaunch(self):
        """ Called when `modalStartPlotDataButton` is pressed. """
        if (self.plot._flare_prediction_state!="post-launch") and (self.plot._flare_prediction_state=="triggered"):
            print(f"Launch initiated at {self.plot.current_realtime}.")
            self.manual_stat("Start launch")
            self.plot._button_press_launch()
            self.plot._update() #update states and everything
            self.plot.update_launch_plots() # make sure to plot launch lines
        elif (self.plot._flare_prediction_state!="post-launch") and (self.plot._flare_prediction_state=="launched"):
            print("Launch already initiated.")
        else:
            # print("In post-launch, cannot start.")
            print("Now is not the time, only launch when triggered.")

    def stopLaunch(self):
        """ Called when `modalStopPlotDataButton` is pressed. """
        if self.plot._flare_prediction_state=="triggered":
            print(f"LAUNCH HELD AT {self.plot.current_realtime}.")
            self.manual_stat("stop")
            self._cancelled = True
            self.plot.change_to_post_launch_state()
            self.plot._update() #update states and everything
            self.plot.update_launch_plots() # make sure to plot launch lines
        elif self.plot._flare_prediction_state=="launched":
            print("Launch already initiated.")
        else:
            print("Nothing to stop.")
            
    def startCountdown(self):
        """ Called when 'startCountdownButton' is pressed"""
        if self.plot._flare_prediction_state=="triggered":
            print('Starting Launch Countdown at {self.plot.current_realtime}.')
            self.plot._button_press_save_countdown_time()
        elif self.plot._flare_prediction_state=="searching":
            print('No Trigger, do not begin countdown.')
        else:
            print("Launch already initiated, wait until next trigger to begin countdown.")
            
    def update_stat(self):
        """ Used to update the status widget `self.status`."""
        self.status.update_labels(self.plot._flare_prediction_state, self._man_stat)

        led_status = self._man_stat if self._man_stat in ["stop"] else self.plot._flare_prediction_state 
        self._man_stat = ""

        # if the same status keeps coming in don't want it to update all the time
        if hasattr(self, "old_led_status") and (led_status==self.old_led_status):
            return
        
        # set logic for button colour depending on state
        if (self.plot._flare_prediction_state=="searching") or (self.plot._flare_prediction_state=="post-launch"):
            # grey-out if searching or in post-launch, keep 'stop' button red if launch was cancelled
            self.startLaunchButton.setStyleSheet(self._button_style("black", "grey"))
            self.startCountdownButton.setStyleSheet(self._button_style("black", "grey"))
            stop_col = "red" if hasattr(self,"_cancelled") and self._cancelled else "grey"
            self.stopLaunchButton.setStyleSheet(self._button_style("black", stop_col))
            self._cancelled = False
        elif (self.plot._flare_prediction_state=="triggered"):
            # both buttons come into play when triggered (for now) so make them white
            self.startLaunchButton.setStyleSheet(self._button_style("green", "white"))
            self.startLaunchButton.setStyleSheet(self._button_style("black", "white"))
            self.stopLaunchButton.setStyleSheet(self._button_style("red", "white"))
        # elif (self.plot._flare_prediction_state=="pre-launch"):
        #     # the launch button has been pressed, turn bkg of launch button light green and make the stop button border red
        #     self.startLaunchButton.setStyleSheet(self._button_style("green", "#D5FFCE"))
        #     self.stopLaunchButton.setStyleSheet(self._button_style("red", "white"))
        elif (self.plot._flare_prediction_state=="launched"):
            # if launched then grey-out the stop button again and make the launch button solid green for the launch
            self.startLaunchButton.setStyleSheet(self._button_style("black", "green"))
            self.startLaunchButton.setStyleSheet(self._button_style("black", "grey"))
            self.stopLaunchButton.setStyleSheet(self._button_style("black", "grey"))
        else:
            # if I've missed anything then just made the buttons look white
            self.startLaunchButton.setStyleSheet(self._button_style("black", "white"))
            self.startCountdownButton.setStyleSheet(self._button_style("black", "white"))
            self.stopLaunchButton.setStyleSheet(self._button_style("black", "white"))
        
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

    def sizeHint(self):
        """ Helps define the size of the widget. """
        return QSize(40,120)
    
    def _include_startstop(self):
        """ A place for the start/stop buttons code. """
        startstop_layout = QVBoxLayout()

        self.modalStartPlotDataButton = QPushButton("Start plotting data", self)
        self.modalStopPlotDataButton = QPushButton("Stop plotting data", self)
        self.startPlotUpdate() # to colour the buttons straight away, not essential

        startstop_layout.addWidget(self.modalStartPlotDataButton,0,0)
        startstop_layout.addWidget(self.modalStopPlotDataButton,0,1)

        self.modalStartPlotDataButton.clicked.connect(self.startPlotUpdate)
        self.modalStopPlotDataButton.clicked.connect(self.stopPlotUpdate)

        return startstop_layout

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
        self.plot.timer = QTimer()
        self.plot.timer.setInterval(self.plot.ms_timing) # fastest is every millisecond 
        self.plot.timer.timeout.connect(self.plot._update) # call self.plot.update every cycle
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


