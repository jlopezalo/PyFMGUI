import sys
import multiprocessing
from platform import system, release
import PyQt5
from pyqtgraph.Qt import QtGui, QtCore, QtWidgets

import pyqtgraph.graphicsItems.ViewBox.axisCtrlTemplate_pyqt5
import pyqtgraph.graphicsItems.PlotItem.plotConfigTemplate_pyqt5
import pyqtgraph.imageview.ImageViewTemplate_pyqt5


from pyafmgui.main_window import MainWindow
from pyafmgui.session import Session

def main():
	app = QtWidgets.QApplication(sys.argv)
	# Force the style to be the same on all OSs:
	app.setStyle("Fusion")
	
	# Define the colour palette of the application:
	palette = QtGui.QPalette()
	palette.setColor(QtGui.QPalette.Window, QtGui.QColor(53, 53, 53))
	palette.setColor(QtGui.QPalette.WindowText, QtCore.Qt.white)
	palette.setColor(QtGui.QPalette.Base, QtGui.QColor(25, 25, 25))
	palette.setColor(QtGui.QPalette.AlternateBase, QtGui.QColor(53, 53, 53))
	palette.setColor(QtGui.QPalette.ToolTipBase, QtCore.Qt.black)
	palette.setColor(QtGui.QPalette.ToolTipText, QtCore.Qt.white)
	palette.setColor(QtGui.QPalette.Text, QtCore.Qt.white)
	palette.setColor(QtGui.QPalette.Button, QtGui.QColor(53, 53, 53))
	palette.setColor(QtGui.QPalette.ButtonText, QtCore.Qt.white)
	palette.setColor(QtGui.QPalette.BrightText, QtCore.Qt.red)
	palette.setColor(QtGui.QPalette.Link, QtGui.QColor(42, 130, 218))
	palette.setColor(QtGui.QPalette.Highlight, QtGui.QColor(42, 130, 218))
	palette.setColor(QtGui.QPalette.HighlightedText, QtCore.Qt.black)
	
	# Set colour palette on the application.
	app.setPalette(palette)
	session = Session()
	ex = MainWindow(session)
	ex.show()
	sys.exit(app.exec())
	
if __name__ == '__main__':
	# If running macOS catalina use forkserver instead of fork for creating new processes.
    # See https://bugs.python.org/issue33725
    if system() == "Darwin" and "19.0" <= release()[:-2] < "20.0":
        multiprocessing.set_start_method("forkserver")

    # Add support for multiprocessing in frozen app
    # See http://docs.python.org/3/library/multiprocessing.html
    multiprocessing.freeze_support()
    main()