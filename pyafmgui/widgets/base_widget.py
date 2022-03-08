import PyQt6
from pyqtgraph.Qt import QtGui, QtWidgets

class BaseWidget(QtGui.QWidget):
    def __init__(self, session, parent=None):
        super(BaseWidget, self).__init__(parent)
        self.session = session
        self.session.hertz_fit_widget = self
        self.init_gui()
    
    def init_gui(self):
        pass

    def file_changed(self):
        pass

    def curve_changed(self):
        pass