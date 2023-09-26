"""
A widget to display different times.
"""


#https://www.pythonguis.com/tutorials/pyqt6-creating-your-own-custom-widgets/
#https://doc.qt.io/qtforpython-5/PySide2/QtGui/QPainterPath.html
#https://coderslegacy.com/python/pyqt6-qlabel-widget/

import numpy as np
import pytz
import datetime
from PyQt6.QtWidgets import QWidget, QApplication, QSizePolicy,QGridLayout, QLabel
from PyQt6.QtCore import QSize, QTimer, Qt


class QTimeWidget(QWidget):
    """
    A widget to be added to a GUI to display time in UTC, user local time, and the time in Alaska (PST - 1 hr).

    Example
    -------
    class test(QWidget):
        \""" A test widget class to use QTimeWidget. \"""
        def __init__(self, parent=None):
            QWidget.__init__(self,parent)

            # define layout
            l = QGridLayout()

            # create time widget and add it to the layout
            self.times = QTimeWidget()
            l.addWidget(self.times, 0, 0) # widget, -y, x

            # actually display the layout
            self.setLayout(l)

    app = QApplication([])
    window = test()
    window.show()
    app.exec()
    """
    def __init__(self, parent=None, **kwargs):
        """ Constructs the widget, works out the times, and adds the time labels to the widget."""
        QWidget.__init__(self,parent, **kwargs)
        self.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding,
            QSizePolicy.Policy.MinimumExpanding
        )

        # set main layout for widget
        self._layout = QGridLayout()

        # this is the format for the time strings
        self._datetime_str_format = "%Y/%m/%d, %H:%M:%S"

        # default is to include all these times
        self.include_utc("True")
        self.include_local("True")
        self.include_alaska("True")

        # define the label for each time and a post-fix for future, maybe?
        self._utc_prefix, self._utc_postfix = "UTC Time: ", ""
        self._local_prefix, self._local_postfix = "Local Time: ", ""
        self._alaska_prefix, self._alaska_postfix = "Alaska Time: ", ""

        # make QLabel()s for all labels
        self._build_labels()

        # add the label widgets to the layout
        self._layout.addWidget(self._label_utc)
        self._layout.addWidget(self._label_local)
        self._layout.addWidget(self._label_alaska)

        self._label_utc.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._label_local.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self._label_alaska.setAlignment(Qt.AlignmentFlag.AlignLeft)

        # set the main layout
        self.setLayout(self._layout)

        # style the labels
        self._label_utc.setStyleSheet(self._time_style())
        self._label_local.setStyleSheet(self._time_style())
        self._label_alaska.setStyleSheet(self._time_style())

        # test the changing status
        self.timer = QTimer()
        self.timer.setInterval(900) # fastest is every millisecond here, make sure only one update is in this range
        self.timer.timeout.connect(self.cycle_times) # call self.update_plot_data every cycle
        self.timer.start()

    def _time_style(self):
        """ Define the style for the label widgets. """
        return "border-width: 0px; color: black;"

    def include_utc(self, include):
        """
        Used to indicate that the time in UTC should be displayed.

        Parameters
        ----------
        include : `Bool`
            Should the UTC time be included in the widget.

        Sets
        ----
            self._utc=include
        """
        self._utc = include
        if not include:
            self._layout.removeWidget(self._label_utc)
        self._trigger_label_update()

    def include_local(self, include):
        """
        Used to indicate that the user's local time should be displayed.

        Parameters
        ----------
        include : `Bool`
            Should the user's local time be included in the widget.

        Sets
        ----
            self._local=include
        """
        self._local = include
        if not include:
            self._layout.removeWidget(self._label_local)
        self._trigger_label_update()

    def include_alaska(self, include):
        """
        Used to indicate that Alaska time should be displayed.

        Parameters
        ----------
        include : `Bool`
            Should Alaska time be included in the widget.

        Sets
        ----
            self._alaska=include
        """
        self._alaska = include
        if not include:
            self._layout.removeWidget(self._label_alaska)
        self._trigger_label_update()

    def _get_times(self):
        """ Get the time strings of the current times in the different time zones. """
        self._utc_str = datetime.datetime.now(datetime.timezone.utc).strftime(self._datetime_str_format)
        self._local_str = datetime.datetime.now().strftime(self._datetime_str_format)
        self._alaska_str = (datetime.datetime.now(pytz.timezone('US/Pacific'))-datetime.timedelta(hours=1)).strftime(self._datetime_str_format)

    def _build_labels(self):
        """ Assign a default empty label to the times. """
        self._label_utc, self._label_local, self._label_alaska = QLabel(""), QLabel(""), QLabel("")

        self._update_labels()

    def _update_labels(self):
        """ Get the most current time for the time zones and update the relevant QLabels. """
        self._get_times()

        if self._utc:
            self._label_utc.setText(f"{self._utc_prefix:15}{self._utc_str:20}{self._utc_postfix}")
            # self._label_utc.setFont(QFont(self.font))

        if self._local:
            self._label_local.setText(f"{self._local_prefix:15}{self._local_str:20}{self._local_postfix}")
            # self._label_local.setFont(QFont(self.font))
        
        if self._alaska:
            self._label_alaska.setText(f"{self._alaska_prefix:15}{self._alaska_str:20}{self._alaska_postfix}")
            # self._label_alaska.setFont(QFont(self.font))

    def sizeHint(self):
        """ Helps define the size of the widget. """
        return QSize(80,120)

    def smallest_dim(self, painter_obj):
        """ Might be usedul to help define the size of the widget. """
        return painter_obj.device().width() if (painter_obj.device().width()<painter_obj.device().height()) else painter_obj.device().height()

    def cycle_times(self):
        """ Called every timer cycle to get the new times and update the widget. """
        self._update_labels()
        self._trigger_label_update()

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
        self.times = QTimeWidget()
        l.addWidget(self.times, 0, 0) # widget, -y, x

        self.times2 = QTimeWidget()
        self.times2.include_local(False)
        l.addWidget(self.times2, 1, 0)

        self.times3 = QTimeWidget()
        self.times3.include_alaska(False)
        l.addWidget(self.times3, 0, 1)

        self.times4 = QTimeWidget()
        self.times4.include_local(False)
        self.times4.include_alaska(False)
        l.addWidget(self.times4, 1, 1)

        # actually display the layout
        self.setLayout(l)


if __name__=="__main__":
    # for testing
    app = QApplication([])
    window = test()
    window.show()
    app.exec()