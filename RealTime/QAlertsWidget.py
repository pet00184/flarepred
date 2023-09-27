"""
A widget to display different status conditions.
"""


#https://www.pythonguis.com/tutorials/pyqt6-creating-your-own-custom-widgets/
#https://doc.qt.io/qtforpython-5/PySide2/QtGui/QPainterPath.html
#https://coderslegacy.com/python/pyqt6-qlabel-widget/

import numpy as np
from PyQt6.QtWidgets import QWidget, QApplication, QSizePolicy,QVBoxLayout,QGridLayout, QLabel
from PyQt6.QtCore import QSize, QTimer


class QAlertsWidget(QWidget):
    """
    A widget to be added to a GUI to display alert statuses.

    Example
    -------
    class test(QWidget):
    # A test widget class to use QAlertsWidget. 
    def __init__(self, parent=None):
        # Initialise a grid on a widget and add different iterations of the QAlertsWidget widget. 
        QWidget.__init__(self,parent)

        # define layout
        l = QGridLayout()

        # create value widget and add it to the layout
        self.alerts = ("first_one", "another",) #
        self.flare_alerts =  np.zeros(1, np.dtype({'names':self.alerts, 
                                              'formats':('bool',)*len(self.alerts)}))
        self.values = QAlertsWidget(self.flare_alerts)
        l.addWidget(self.values, 0, 0) # widget, -y, x

        # actually display the layout
        self.setLayout(l)

        # test the changing values
        self.timer = QTimer()
        self.timer.setInterval(1000) # fastest is every millisecond here
        self.timer.timeout.connect(self.cycle_values) # call self.update_plot_data every cycle
        self.timer.start()

    def cycle_values(self):
        # Add new data, update widget, then remove first point so it is ready for new point.
        t_or_f = np.random.randint(2, size=self.values.number_of_alerts)
        self.flare_alerts[self.alerts[0]] = t_or_f[0] 
        self.flare_alerts[self.alerts[1]] = t_or_f[1] 
        self.values.update_labels(self.flare_alerts)

    # for testing
    app = QApplication([])
    window = test()
    window.show()
    app.exec()
    """
    def __init__(self, alert_list, parent=None, **kwargs):
        """ 
        Constructs the widget and adds the latest plotted data to the widget.
        
        Parameters
        ----------
        alert_list : numpy structured array
                Array of the boolean alerts and their names.
        """
        QWidget.__init__(self,parent, **kwargs)
        self.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding,
            QSizePolicy.Policy.MinimumExpanding
        )

        # set main layout for widget
        self._layout = QGridLayout()

        # set the number of most reccent data points to be displayed
        self._define_alerts(alert_list.dtype.names)

        # make the appropriate number of labels for the number of data points
        self._build_labels()

        # add the labels to the layout
        self._add_labels()

        # style the label widgets
        self._style_labels()

        # set the main layout for the widget
        self.setLayout(self._layout)

    def _define_alerts(self, alert_list):
        """ Easily add new alerts. """
        self.alert_name_list = alert_list
        self.number_of_alerts = len(alert_list)

    def _data_style(self):
        """ Define the style for the label widgets. """
        return "border-width: 0px; color: black;"
    
    def _style_labels(self):
        """ Assign the style for the label widgets. """
        for lbl in self._value_labels:
            lbl.setStyleSheet(self._data_style())

    def _build_labels(self):
        """ Assign a default empty label to the values. """
        self._value_labels = list()
        for a in range(self.number_of_alerts):
            # https://www.compart.com/en/unicode/U+2753
            # \u2753=red question mark, \u2754= grey, hollow question mark
            self._value_labels.append(QLabel(f"{self.alert_name_list[a]} : \u2754"))

    def _add_labels(self):
        """ Add labels to widget. """
        for lbl in self._value_labels:
            self._layout.addWidget(lbl)

        self._layout.addWidget(QLabel("\u2754=N/A | \u2705=Alert | \u274C=No Alert"))

    def update_labels(self, new_alert_status):
        """ Get the most current data values and update the relevant QLabels. """

        # update the labels in so newest is always at the top, even if 
        # more than `self.number_of_alerts` values are given
        for (lbr, alert) in zip(self._value_labels, self.alert_name_list):
            a = alert_status_str(alert_stat=new_alert_status[alert])
            lbr.setText(f"{alert} : {a}") 

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

def alert_status_str(alert_stat):
    """ 
    Return a string to represent the given status of an alert.

    For more unicodes: https://www.i2symbol.com/symbols/check
    
    Parameters
    ----------
    alert_stat : `bool`
        Whether an alert is active or not.
    
    Returns
    -------
    `str` : 
        The string representation of active/non-active alert.
    """
    if alert_stat:
        return "\u2705" #"Aye", `&#x2705;`=tick
    return "\u274C" #"Naw", `&#x274C;`=cross


class test(QWidget):
    """ A test widget class to use QAlertsWidget. """
    def __init__(self, parent=None):
        """ Initialise a grid on a widget and add different iterations of the QAlertsWidget widget. """
        QWidget.__init__(self,parent)

        # define layout
        l = QGridLayout()

        # create value widget and add it to the layout
        self.alerts = ("first_one", "another",) #
        self.flare_alerts =  np.zeros(1, np.dtype({'names':self.alerts, 
                                              'formats':('bool',)*len(self.alerts)}))
        self.values = QAlertsWidget(self.flare_alerts)
        l.addWidget(self.values, 0, 0) # widget, -y, x

        # actually display the layout
        self.setLayout(l)

        # test the changing values
        self.timer = QTimer()
        self.timer.setInterval(1000) # fastest is every millisecond here
        self.timer.timeout.connect(self.cycle_values) # call self.update_plot_data every cycle
        self.timer.start()

    def cycle_values(self):
        """ Add new data, update widget, then remove first point so it is ready for new point."""
        t_or_f = np.random.randint(2, size=self.values.number_of_alerts)
        self.flare_alerts[self.alerts[0]] = t_or_f[0] 
        self.flare_alerts[self.alerts[1]] = t_or_f[1] 
        self.values.update_labels(self.flare_alerts)


if __name__=="__main__":
    # for testing
    app = QApplication([])
    window = test()
    window.show()
    app.exec()