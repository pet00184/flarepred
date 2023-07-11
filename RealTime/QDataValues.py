"""
A widget to display different status conditions.
"""


#https://www.pythonguis.com/tutorials/pyqt6-creating-your-own-custom-widgets/
#https://doc.qt.io/qtforpython-5/PySide2/QtGui/QPainterPath.html
#https://coderslegacy.com/python/pyqt6-qlabel-widget/

import numpy as np
import pytz
import datetime
from PyQt6.QtWidgets import QWidget, QApplication, QSizePolicy,QVBoxLayout,QGridLayout, QLabel
from PyQt6.QtCore import Qt, QSize, QTimer
from itertools import cycle


class QValueWidget(QWidget):
    """
    A widget to be added to a GUI to display the last data points plotted.

    Example
    -------
    class test(QWidget):
    \""" A test widget class to use QTimeWidget. \"""
    def __init__(self, parent=None):
        \""" Initialise a grid on a widget and add different iterations of the QTimeWidget widget. \"""
        QWidget.__init__(self,parent)

        # define layout
        l = QGridLayout()

        # create value widget and add it to the layout
        self.values = QValueWidget()
        l.addWidget(self.values, 0, 0) # widget, -y, x

        # actually display the layout
        self.setLayout(l)

        # generate values strings
        self._auto = list(self.values_in_range(self.values.number_of_vals-1))
        

        # test the changing values
        self.timer = QTimer()
        self.timer.setInterval(500) # fastest is every millisecond here
        self.timer.timeout.connect(self.cycle_values) # call self.update_plot_data every cycle
        self.timer.start()

    def values_in_range(self, number):
        \""" Provide numbers in a range almost all classable by GOES. \"""
        return 10**(-np.random.rand(number)*11)

    def cycle_values(self):
        \""" Add new data, update widget, then remove first point so it is ready for new point.\"""
        self._auto.append(self.values_in_range(1)[0])
        self.values.update_labels(self._auto)
        self._auto = self._auto[1:]

    app = QApplication([])
    window = test()
    window.show()
    app.exec()
    """
    def __init__(self, parent=None, **kwargs):
        """ Constructs the widget and adds the latest plotted data to the widget."""
        QWidget.__init__(self,parent, **kwargs)
        self.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding,
            QSizePolicy.Policy.MinimumExpanding
        )

        self._layout = QGridLayout()

        self.number_of_vals = 5

        self._auto_prefix = [""]*self.number_of_vals

        self._build_labels()

        self._add_labels()

        self.setLayout(self._layout)

    def _build_labels(self):
        """ Assign a default empty label to the values. """
        self._value_labels = list()
        for v in range(self.number_of_vals):
            self._value_labels.append(QLabel(""))

    def _add_labels(self):
        """ Add labels to widget. """
        for lbl in self._value_labels:
            self._layout.addWidget(lbl)

    def update_labels(self, new_values):
        """ Get the most current data values and update the relevant QLabels. """

        if len(new_values)<self.number_of_vals:
            # if not enough values to fill labels then add empty ones at the end
            new_values = [np.nan]*(self.number_of_vals-len(new_values)) + list(new_values)

        # update the labels in so newest is always at the top, even if 
        # more than `self.number_of_vals` values are given
        for count, (lbr, nvr) in enumerate(zip(self._value_labels, new_values[::-1])):
            f, c = goes_class_str(goes_flux=nvr)
            lbr.setText(f"{count+1} : {f}, {c}") 

        self._trigger_label_update()

    def sizeHint(self):
        """ Helps define the size of the widget. """
        return QSize(40,120)

    def smallest_dim(self, painter_obj):
        """ Might be usedul to help define the size of the widget. """
        return painter_obj.device().width() if (painter_obj.device().width()<painter_obj.device().height()) else painter_obj.device().height()

    def _trigger_label_update(self):
        """ A dedicated method to call and update the widget. """
        self.update()

def goes_class_str(goes_flux):
    """ 
    Return the GOES flux value in scientific notation and the class letter grade given a GOES XRSB flux.
    
    Parameters
    ----------
    goes_flux : `int`, `float`
        The XRSB GOES flux to be converted into scientific notation and class letter + value.
    
    Returns
    -------
    `tuple` : length 2
        The first entry is the GOES flux value in scientific notation and the second is the class letter + value.
    """
    # make map of the log-goes fluxes to the class prefixes
    goes_class_pre = {-10:"A0.0", -9:"A0.", -8:"A", -7:"B", -6:"C", -5:"M", -4:"X", -3:"X1", -2:"X10", -1:"X10"}

    # find the flux order of magnitude for the class, else make it a nan if it isn't a number 
    try:
        class_v = np.floor(np.log10(goes_flux)) # floors the float
    except ValueError:
        class_v = np.nan

    # try to get the correct class letter
    class_pre = goes_class_pre.get(class_v, "N/A") # return N/A if it can't work it out for some reason, NaNs or something? I don't know

    # find the goes class value to 1 d.p.
    level = round(goes_flux/(10**class_v),1)

    # put the flux in e.g. 1e-6 W/m^-2
    goes_flux_str = f"{level}e{class_v}"+" W/m^-2"

    # if the class letter isn't found then just return what we have
    if class_pre=="N/A":
        return goes_flux_str, f"{class_pre}"
    
    # if the class letter is found then edit the level if <A since the 0. is already there
    level_edit = level if class_v>=-8 else int(level*10**(-8-class_v)) 

    # return value as a string in a certain format and the class+class value
    return goes_flux_str, f"{class_pre}{level_edit}"


class test(QWidget):
    """ A test widget class to use QTimeWidget. """
    def __init__(self, parent=None):
        """ Initialise a grid on a widget and add different iterations of the QTimeWidget widget. """
        QWidget.__init__(self,parent)

        # define layout
        l = QGridLayout()

        # create value widget and add it to the layout
        self.values = QValueWidget()
        l.addWidget(self.values, 0, 0) # widget, -y, x

        # actually display the layout
        self.setLayout(l)

        # generate values strings
        # should start at self.values.number_of_vals-2 but pretend we don't have enough values to fill up all labels first
        self._auto = list(self.values_in_range(self.values.number_of_vals-2))
        

        # test the changing values
        self.timer = QTimer()
        self.timer.setInterval(1000) # fastest is every millisecond here
        self.timer.timeout.connect(self.cycle_values) # call self.update_plot_data every cycle
        self.timer.start()

    def values_in_range(self, number):
        """ Provide numbers in a range almost all classable by GOES. """
        return 10**(-np.random.rand(number)*11)

    def cycle_values(self):
        """ Add new data, update widget, then remove first point so it is ready for new point."""
        self._auto.append(self.values_in_range(1)[0])
        self.values.update_labels(self._auto)
        if len(self._auto)==self.values.number_of_vals:
            self._auto = self._auto[1:]


if __name__=="__main__":
    # for testing
    app = QApplication([])
    window = test()
    window.show()
    app.exec()