import sys
from PyQt6 import QtWidgets, QtCore
import PyQt6
import realtime_flare_trigger as rft
import GOES_data_upload as GOES_data
import post_analysis as pa
from QTimeWidget import QTimeWidget

HISTORICAL = True
run_name = 'EXAMPLE_HISTORICAL_RUN2' #utilize this to specify your saved runs

class main_window(QtWidgets.QWidget):
    #
    """ A test widget class to use QTimeWidget. """
    def __init__(self):
        """ Initialise a grid on a widget and add different iterations of the QTimeWidget widget. """
        QtWidgets.QWidget.__init__(self)

        # define layout
        l = QtWidgets.QGridLayout()

        # create time widget and add it to the layout
        times = QTimeWidget()
        l.addWidget(times, 1, 0) # widget, -y, x

        # self.setCentralWidget(rft.RealTimeTrigger(GOES_data.load_realtime_XRS, foldername))

        _data = GOES_data.FakeDataUpdator(GOES_data.historical_GOES_XRS).append_new_data if HISTORICAL else GOES_data.load_realtime_XRS
        plot = rft.RealTimeTrigger(_data, run_name)
        l.addWidget(plot, 0, 0) # widget, -y, x

        # actually display the layout
        self.setLayout(l)
    
def post_analysis(foldername):
    pra = pa.PostRunAnalysis(foldername)
    pra.sort_summary()
    pra.do_launch_analysis()
    pra.write_text_summary()
    
if __name__=="__main__":
    app = QtWidgets.QApplication([])
    window = main_window()
    window.show()
    app.exec()
    post_analysis(run_name)
