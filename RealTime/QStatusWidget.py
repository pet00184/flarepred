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


class QStatusWidget(QWidget):
    """
    A widget to be added to a GUI to display certain status strings.

    Example
    -------
    class test(QWidget):
        \""" A test widget class to use QStatusWidget. \"""
        def __init__(self, parent=None):
            QWidget.__init__(self,parent)

            # define layout
            l = QGridLayout()

            # create time widget and add it to the layout
            self.status = QStatusWidget()
            l.addWidget(self.status, 0, 0) # widget, -y, x

            # actually display the layout
            self.setLayout(l)

    app = QApplication([])
    window = test()
    window.show()
    app.exec()
    """
    def __init__(self, parent=None, **kwargs):
        """ Constructs the widget and adds the status labels to the widget."""
        QWidget.__init__(self,parent, **kwargs)
        self.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding,
            QSizePolicy.Policy.MinimumExpanding
        )

        self._layout = QGridLayout()

        self._auto_prefix, self._auto_postfix = "Automated Recommendation: ", ""
        self._stat_prefix, self._stat_postfix = "Status: ", ""

        self._build_labels()

        self._layout.addWidget(self._label_auto)
        self._layout.addWidget(self._label_stat)

        self.setLayout(self._layout)

    def _build_labels(self):
        """ Assign a default empty label to the times. """
        # self._label_auto, self._label_stat = QLabel(f"{self._auto_prefix}{self._auto_postfix}"), QLabel(f"{self._stat_prefix}{self._stat_postfix}")
        self._label_auto, self._label_stat = QLabel(f"{self._stat_prefix}{self._stat_postfix}"), QLabel("")

    def update_labels(self, auto_rec, current):
        """ Get the most current status strings and update the relevant QLabels. """

        # self._label_auto.setText(f"{self._auto_prefix}{auto_rec}{self._auto_postfix}")
        # self._label_stat.setText(f"{self._stat_prefix}{current}{self._stat_postfix}")
        self._label_auto.setText(f"{self._stat_prefix}{auto_rec}{self._stat_postfix}")

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



class test(QWidget):
    """ A test widget class to use QTimeWidget. """
    def __init__(self, parent=None):
        """ Initialise a grid on a widget and add different iterations of the QTimeWidget widget. """
        QWidget.__init__(self,parent)

        # define layout
        l = QGridLayout()

        # create time widget and add it to the layout
        self.status = QStatusWidget()
        l.addWidget(self.status, 0, 0) # widget, -y, x

        # actually display the layout
        self.setLayout(l)

        # auto and stat strings
        self._auto = cycle(["Calculating", "Beep Boop", "Destroy all humans", "The cake is a lie"]) 
        self._stat = cycle(["Doing nothing", "Still doing nothing", "I\'m bored", "The computer is scaring me..."])

        # test the changing status
        self.timer = QTimer()
        self.timer.setInterval(2000) # fastest is every millisecond here, call every 0.5 sec
        self.timer.timeout.connect(self.cycle_status) # call self.update_plot_data every cycle
        self.timer.start()

    def cycle_status(self):
        self.status.update_labels(f"{next(self._auto)}", f"{next(self._stat)}")


if __name__=="__main__":
    # for testing
    app = QApplication([])
    window = test()
    window.show()
    app.exec()