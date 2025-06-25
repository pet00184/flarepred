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
from datetime import timedelta


class QButtonsWidget(QWidget):
    """
    A widget to be added to a GUI to display the buttons we want.
    """
    def __init__(self, plotting_widget, parent=None, **kwargs):
        """ Constructs the widget and adds the buttons to the widget."""
        QWidget.__init__(self,parent, **kwargs)

        self.plot = plotting_widget

        # layout for all buttons
        self._layout = QGridLayout()

        # layout for radio buttons and press buttons 
        self.scale_radio_layout = QGridLayout()

        # create the radio buttons and press buttons, add to individual layouts
        self._add_scale_radio_buttons()

        # style the button widgets
        self.slabel.setStyleSheet(self._radio_style())
        self.log.setStyleSheet(self._radio_style())
        self.linear.setStyleSheet(self._radio_style())

        # add both button layouts to the main one
        self._layout.addLayout(self.scale_radio_layout,0,0)#-y, x

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
        self.plot.eve_plot_update()
        self.plot.xlims()
        self.plot.display_eve30()
        
        
    def linearyscale(self):
        """ Change y-scale range of `self.plot` to linear. """
        self.plot._logy = False
        self.plot.eve_plot_update()
        self.plot.xlims()
        self.plot.display_eve30()

    def sizeHint(self):
        """ Helps define the size of the widget. """
        return QSize(40,120)
