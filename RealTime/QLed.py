# see: https://github.com/jazzycamel/QLed/blob/ebbf71a270ed58c6c77ce2e0ace7c985bba80155/QLed.py#L8
#https://www.pythonguis.com/tutorials/pyqt6-creating-your-own-custom-widgets/
#https://doc.qt.io/qtforpython-5/PySide2/QtGui/QPainterPath.html

import numpy as np
import numpy as np
from PyQt6.QtWidgets import QWidget, QApplication, QSizePolicy,QVBoxLayout,QGridLayout
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QPainter, QBrush, QColor,QPainterPath, QPen
from itertools import cycle

class Status:
    """
    A class to contain properties for each status.

    Overkill just now but might make it easier in the future.
    """
    def __init__(self, colour, flash):
        self.colour = colour
        self.flash = flash

class QLed(QWidget):
    """
    A widget to be added to a GUI to display a status LED.
    
    Example
    -------
    class test(QWidget):
        \""" A test widget class to use QLed. \"""
        def __init__(self, parent=None):
            QWidget.__init__(self,parent)

            # define layout
            l = QGridLayout()

            # create light indicator and add it to the layout
            self.light1 = QLed()
            l.addWidget(self.light1, 0, 0) # widget, -y, x

            self.light2 = QLed()
            self.light2.update_shape(shape="square")
            l.addWidget(self.light2, 1, 0)

            self.light3 = QLed()
            self.light3.update_shape(shape="diamond")
            l.addWidget(self.light3, 0, 1)

            self.light4 = QLed()
            self.light4.update_shape(shape="ellipse")
            l.addWidget(self.light4, 1, 1)

            # actually display the layout
            self.setLayout(l)

            self._settings = cycle(self.light1.status_str) 

            # test the changing colour
            self.timer = QTimer()
            self.timer.setInterval(2000) # fastest is every millisecond here, call every 0.5 sec
            self.timer.timeout.connect(self.cycle_colour) # call self.update_plot_data every cycle
            self.timer.start()

        def cycle_colour(self):
            s = next(self._settings)
            self.light1.update_status(s)
            self.light2.update_status(s)
            self.light3.update_status(s)
            self.light4.update_status(s)

    app = QApplication([])
    window = test()
    window.show()
    app.exec()
    """
    def __init__(self, parent=None, **kwargs):
        QWidget.__init__(self,parent, **kwargs)
        self.setSizePolicy(
            QSizePolicy.Policy.MinimumExpanding,
            QSizePolicy.Policy.MinimumExpanding
        )

        # so RGBA=(0,255,0, 255) or RGB=(0,255,0) 
        self.status_map = {"searching":Status((125,125,125),False), 
                           "triggered":Status((235,186,52),True), 
                           "pre-launch":Status((0,255,0),True), 
                           "launched":Status((0,255,0),False), 
                           "post-launch":Status((255,0,0),False), 
                           "hold":Status((255,0,0),True), 
                           "stop":Status((255,0,0),False)} 
        self.status_str = list(self.status_map.keys())
        self.update_status("searching")

        # define colour to flash against and how often it should flash
        self._flash_against = (0,0,0)
        self._flash_freq = 200 # in ms

        # shape of widget
        self.update_shape(shape="circle")

    def start_flash(self):
        """ If called, it will start a timer to flash the LED. """
        self.timer_flash = QTimer()
        self.timer_flash.setInterval(self._flash_freq) # fastest is every millisecond here, call every 100 ms
        self.timer_flash.timeout.connect(self.change_colour) # call self.flash_colour every cycle
        self.timer_flash.start()
    
    def stop_flash(self):
        """ If called, it will stop the timer that is flashing the LED. """
        self.timer_flash.stop()
        del self.timer_flash

    def sizeHint(self):
        """ Helps PyQt with sizing apparently. """
        return QSize(40,120)
    
    def update_shape(self, shape="circle"):
        """Shapes are:
            circle, ellipse, diamond, rectangle, square    
        """
        self.shape = shape
        self.update()
    
    def change_colour(self):
        """ change the LED colour, if flashing then alternate between colour and `self._flash_against`. """
        if self.flash:
            self.colour = self.status_map[self.status].colour if (self.colour==self._flash_against) else self._flash_against
        else:
            self.colour = self.status_map[self.status].colour
            
        # oncce the colour has been assigned then update the LED with it
        self._trigger_stat_update()

    def smallest_dim(self, painter_obj):
        """ Try to make sure the LED scales well with the space it has. """
        return painter_obj.device().width() if (painter_obj.device().width()<painter_obj.device().height()) else painter_obj.device().height()
    
    def _ellipse(self, path, sx, sy, big_r, r):
        """ Make the LED an ellipse. """
        rad_values = np.linspace(0,2*np.pi, num=100) 
        xs = sx + (big_r) * np.cos(rad_values)
        ys = sy + (r) * np.sin(rad_values)

        path.moveTo(xs[0], ys[0])
        for x, y in zip(xs[1:], ys[1:]):
            path.lineTo(x, y)

        return path

    def ellipse_coords(self, painter_obj, outline_buffer):
        """ Draw the LED as an ellipse. """

        path = QPainterPath()
        #outline_buffer to avoid getting cutoff at edges
        path = self._ellipse(path=path, 
                             sx=painter_obj.device().width()/2, 
                             sy=painter_obj.device().height()/2, 
                             big_r=(painter_obj.device().width()/2)-outline_buffer, 
                             r=(painter_obj.device().height()/2)-outline_buffer)
        path.closeSubpath()

        return path
    
    def circle_coords(self, painter_obj, outline_buffer):
        """ Draw the LED as a circle. """
        smallest_dim = self.smallest_dim(painter_obj)

        path = QPainterPath()
        #outline_buffer to avoid getting cutoff at edges
        path = self._ellipse(path=path, 
                             sx=smallest_dim/2, 
                             sy=smallest_dim/2, 
                             big_r=(smallest_dim/2)-outline_buffer, 
                             r=(smallest_dim/2)-outline_buffer)
        path.closeSubpath()

        return path
    
    def _diamond(self, path, sx, sy, w, h):
        """ Make the LED a diamond. """
        path.moveTo(sx, (h+sy)/2)
        path.lineTo((w+sx)/2, sy)
        path.lineTo(w, (h+sy)/2)
        path.lineTo((w+sx)/2, h)
        return path

    def diamond_coords(self, painter_obj, outline_buffer):
        """ Draw the LED as a diamond. """
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
        """ Make the LED a rectangle. """
        path.moveTo(sx, sy)
        path.lineTo(w, sy)
        path.lineTo(w, h)
        path.lineTo(sx, h)
        return path

    def rectangle_coords(self, painter_obj, outline_buffer):
        """ Draw the LED as a rectangle. """
        path = QPainterPath()
        path = self._rect(path=path, 
                          sx=0+outline_buffer, 
                          sy=0+outline_buffer, 
                          w=painter_obj.device().width()-2*outline_buffer, 
                          h=painter_obj.device().height()-2*outline_buffer)
        path.closeSubpath()

        return path
    
    def square_coords(self, painter_obj, outline_buffer):
        """ Draw the LED as a square. """
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
        """ Choose LED shape. """
        
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

        # draw the shape
        painter_obj.drawPath(path)
        self.draw_path = path

        # update LED widget
        self._trigger_stat_update()

    def paintEvent(self, event):
        """Defines how the widget is redrawn. Very important."""

        # define pen and pen attributes
        painter = QPainter(self) 
        pen_width = 20
        pen = QPen(Qt.GlobalColor.black,  pen_width, Qt.PenStyle.SolidLine)
        painter.setPen(pen)
        
        # make brush and brush attributes
        brush = QBrush()
        brush.setColor(QColor(*self.colour))
        brush.setStyle(Qt.BrushStyle.SolidPattern)

        # draw the chosen shape with the pen
        self.draw_shape(painter_obj=painter, outline_buffer=pen_width/2)

        # fill the shape with the brush
        painter.fillPath(self.draw_path, brush)

    def update_status(self, status):
        """ 
        When a new status comes in, update the status attribute and get the properties of it 
        if it is known.
        
        make sure to update how the LED should behave with the status and update the widget.
        """
        if status in self.status_str:
            self.status = status
            self.colour, self.flash = self.status_map[self.status].colour, self.status_map[self.status].flash
            self.update_led_params()
            self._trigger_stat_update()

    def update_led_params(self):
        """ 
        Start a flashing timer if needed for the set status and initiate the change in widget 
        colour.
        """
        if self.flash and not hasattr(self, "timer_flash"):
                self.start_flash()
        elif not self.flash and hasattr(self, "timer_flash"):
            self.stop_flash()
        self.change_colour()

    def _trigger_stat_update(self):
        """ A bit redundant but might be needed if the update needs to become more complicated."""
        self.update()

class test(QWidget):
    """ A test widget class to use QLed. """
    def __init__(self, parent=None):
        QWidget.__init__(self,parent)

        # define layout
        l = QGridLayout()

        # create light indicator and add it to the layout
        self.light1 = QLed()
        l.addWidget(self.light1, 0, 0) # widget, -y, x

        self.light2 = QLed()
        self.light2.update_shape(shape="square")
        l.addWidget(self.light2, 1, 0)

        self.light3 = QLed()
        self.light3.update_shape(shape="diamond")
        l.addWidget(self.light3, 0, 1)

        self.light4 = QLed()
        self.light4.update_shape(shape="ellipse")
        l.addWidget(self.light4, 1, 1)

        # actually display the layout
        self.setLayout(l)

        self._settings = cycle(self.light1.status_str) 

        # test the changing colour
        self.timer = QTimer()
        self.timer.setInterval(2000) # fastest is every millisecond here, call every 0.5 sec
        self.timer.timeout.connect(self.cycle_colour) # call self.update_plot_data every cycle
        self.timer.start()

    def cycle_colour(self):
        s = next(self._settings)
        self.light1.update_status(s)
        self.light2.update_status(s)
        self.light3.update_status(s)
        self.light4.update_status(s)


if __name__=="__main__":

    app = QApplication([])
    window = test()
    window.show()
    app.exec()