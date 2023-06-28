# see: https://github.com/jazzycamel/QLed/blob/ebbf71a270ed58c6c77ce2e0ace7c985bba80155/QLed.py#L8
#https://www.pythonguis.com/tutorials/pyqt6-creating-your-own-custom-widgets/
#https://doc.qt.io/qtforpython-5/PySide2/QtGui/QPainterPath.html

import numpy as np
import numpy as np
import time
from PyQt6.QtWidgets import QWidget, QApplication, QSizePolicy,QVBoxLayout,QGridLayout
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QPainter, QBrush, QColor,QPainterPath, QPen


class QLed(QWidget):
    def __init__(self, parent=None, **kwargs):
        QWidget.__init__(self,parent, **kwargs)
        self.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding,
            QSizePolicy.Policy.MinimumExpanding
        )

        self.status = "Good"
        # RGBA=(0,255,0, 255) or RGB=(0,255,0)
        self.status_map = {"Good":(0,255,0), "OK":(255,150,0), "Bad":(255,0,0)}
        self.status_str = list(self.status_map.keys())

        # shape of widget
        self.update_shape(shape="circle")

        # test the changing status
        self.timer = QTimer()
        self.timer.setInterval(5000) # fastest is every millisecond here, call every 5 sec
        self.timer.timeout.connect(self.cycle_status) # call self.update_plot_data every cycle
        self.timer.start()

        self.timer_fade = QTimer()
        self.start_colour_fade()
        self.fade_over = 5 # fade colour over 5 seconds, a new start time is generate in `self.cycle_status`
        self.timer_fade.setInterval(100) # fastest is every millisecond here, call every 100 ms
        self.timer_fade.timeout.connect(self.fade_colour) # call self.update_plot_data every cycle
        self.timer_fade.start()

    def sizeHint(self):
        return QSize(40,120)
    
    def update_shape(self, shape="circle"):
        """Shapes are:
            circle, ellipse, diamond, rectangle, square    
        """
        self.shape = shape
        self.update()
    
    def _calc_intermediate_col(self, new_col, old_col):
        # calc with a weighted mean using the fade_counter and fade_over
        fade_counter = self.fade_new_time-self.fade_start
        # print(self.fade_new_time,self.fade_start)
        return int((old_col*(self.fade_over-fade_counter)+new_col*fade_counter)/self.fade_over)
    
    def fade_colour(self):

        r, g, b = self.status_map[self.status]

        self.fade_new_time = time.time()

        if hasattr(self, "old_status"):
            o_r, o_g, o_b = self.status_map[self.old_status]
            r = self._calc_intermediate_col(new_col=r, old_col=o_r)
            g = self._calc_intermediate_col(new_col=g, old_col=o_g)
            b = self._calc_intermediate_col(new_col=b, old_col=o_b)

        if ((self.fade_new_time-self.fade_start)>self.fade_over) and hasattr(self, "old_status"):
            # if we have completely faded to next colour then remove old colour and reset fade counter
            del self.old_status
            

        self.colour = (r,g,b)
        # print((r,g,b), self.fade_new_time-self.fade_start)
            
        self._trigger_stat_update()

    def smallest_dim(self, painter_obj):
        return painter_obj.device().width() if (painter_obj.device().width()<painter_obj.device().height()) else painter_obj.device().height()
    
    def _ellipse(self, path, sx, sy, R, r):
        # x = Rcos(theta)
        # y = rsin(theta)
        rad_values = np.linspace(0,2*np.pi, num=100) 
        xs = sx + (R) * np.cos(rad_values)
        ys = sy + (r) * np.sin(rad_values)

        path.moveTo(xs[0], ys[0])
        for x, y in zip(xs[1:], ys[1:]):
            path.lineTo(x, y)

        return path

    def ellipse_coords(self, painter_obj, outline_buffer):

        path = QPainterPath()
        #outline_buffer to avoid getting cutoff at edges
        path = self._ellipse(path=path, 
                             sx=painter_obj.device().width()/2, 
                             sy=painter_obj.device().height()/2, 
                             R=(painter_obj.device().width()/2)-outline_buffer, 
                             r=(painter_obj.device().height()/2)-outline_buffer)
        path.closeSubpath()

        return path
    
    def circle_coords(self, painter_obj, outline_buffer):
        smallest_dim = self.smallest_dim(painter_obj)

        path = QPainterPath()
        #outline_buffer to avoid getting cutoff at edges
        path = self._ellipse(path=path, 
                             sx=smallest_dim/2, 
                             sy=smallest_dim/2, 
                             R=(smallest_dim/2)-outline_buffer, 
                             r=(smallest_dim/2)-outline_buffer)
        path.closeSubpath()

        return path
    
    def _diamond(self, path, sx, sy, w, h):
        path.moveTo(sx, (h+sy)/2)
        path.lineTo((w+sx)/2, sy)
        path.lineTo(w, (h+sy)/2)
        path.lineTo((w+sx)/2, h)
        return path

    def diamond_coords(self, painter_obj, outline_buffer):
        smallest_dim = self.smallest_dim(painter_obj)

        path = QPainterPath()
        # outline_buffer to avoid getting cutoff at edges
        path = self._diamond(path=path, 
                             sx=0+outline_buffer, 
                             sy=0+outline_buffer, 
                             w=smallest_dim-2*outline_buffer, 
                             h=smallest_dim-2*outline_buffer)
        path.closeSubpath()

        return path
    
    def _rect(self, path, sx, sy, w, h):
        path.moveTo(sx, sy)
        path.lineTo(w, sy)
        path.lineTo(w, h)
        path.lineTo(sx, h)
        return path

    def rectangle_coords(self, painter_obj, outline_buffer):
        path = QPainterPath()
        path = self._rect(path=path, 
                          sx=0+outline_buffer, 
                          sy=0+outline_buffer, 
                          w=painter_obj.device().width()-2*outline_buffer, 
                          h=painter_obj.device().height()-2*outline_buffer)
        path.closeSubpath()

        return path
    
    def square_coords(self, painter_obj, outline_buffer):
        smallest_dim = self.smallest_dim(painter_obj)

        path = QPainterPath()
        path = self._rect(path=path, 
                          sx=0+outline_buffer, 
                          sy=0+outline_buffer, 
                          w=smallest_dim-2*outline_buffer, 
                          h=smallest_dim-2*outline_buffer)
        path.closeSubpath()

        return path

    def draw_shape(self, painter_obj, outline_buffer):
        
        if self.shape=="rectangle":
            path = self.rectangle_coords(painter_obj, outline_buffer)
        elif self.shape=="square":
            path = self.square_coords(painter_obj, outline_buffer)
        elif self.shape=="circle":
            path = self.circle_coords(painter_obj, outline_buffer)
        elif self.shape=="ellipse":
            path = self.ellipse_coords(painter_obj, outline_buffer)
        elif self.shape=="diamond":
            path = self.diamond_coords(painter_obj, outline_buffer)
        else:
            # just exlicitly define default as rectangle, don't need first if then
            path = self.rectangle_coords(painter_obj, outline_buffer)

        painter_obj.drawPath(path)

        self.draw_path = path

        self._trigger_stat_update()

    
    def paintEvent(self, event):
        """Defines how the widget is redrawn. Very important."""

        painter = QPainter(self)
        
        pen_width = 20
        pen = QPen(Qt.GlobalColor.black,  pen_width, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        
        brush = QBrush()
        self.fade_colour()
        brush.setColor(QColor(*self.colour))
        brush.setStyle(Qt.BrushStyle.SolidPattern)

        self.draw_shape(painter_obj=painter, outline_buffer=pen_width/2)

        painter.fillPath(self.draw_path, brush)

    def update_status(self, status):
        if status in self.status_str:
            self.old_status = self.status
            self.status = status
            self._trigger_stat_update()

    def start_colour_fade(self):
            self.fade_start = time.time() # to restart timer and initialise the fading clock

    def cycle_status(self):
        ind = (self.status_str.index(self.status) + 1)%(len(self.status_str))
        self.update_status(self.status_str[ind])
        self.start_colour_fade()

    def _trigger_stat_update(self):
        self.update()

class test(QWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self,parent)

        # define layout
        # l = QVBoxLayout()
        l = QGridLayout()

        # create light indicator and add it to the layout
        self.light = QLed()
        l.addWidget(self.light, 0, 0) # widget, -y, x

        self.light2 = QLed()
        self.light2.fade_over = 2
        self.light2.update_shape(shape="square")
        l.addWidget(self.light2, 1, 0)

        self.light3 = QLed()
        self.light3.fade_over = 0.5
        self.light3.update_shape(shape="diamond")
        l.addWidget(self.light3, 0, 1)

        self.light4 = QLed()
        self.light4.update_shape(shape="ellipse")
        l.addWidget(self.light4, 1, 1)

        # actually display the layout
        self.setLayout(l)


if __name__=="__main__":

    app = QApplication([])
    window = test()
    window.show()
    app.exec()