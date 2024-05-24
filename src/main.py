import sys
import multiprocessing
import PyQt5
from pyqtgraph.Qt import QtGui, QtCore, QtWidgets

# Imports needed to give PyQT5 reference about these
# objects when freezing the code.
# import pyqtgraph.console.template_pyqt5
# import pyqtgraph.graphicsItems.ViewBox.axisCtrlTemplate_pyqt5
# import pyqtgraph.graphicsItems.PlotItem.plotConfigTemplate_pyqt5
# import pyqtgraph.imageview.ImageViewTemplate_pyqt5


from pyfmgui.main_window import MainWindow
from pyfmgui.session import Session

def main():
	print("hell ya")
	# Create PyQT5 application object
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
	
	# Create session object to hold data and results
	session = Session()

	# Create and show main MDI window
	ex = MainWindow(session)
	ex.show()
	sys.exit(app.exec())
	
if __name__ == '__main__':
	# Fork is the deault method for multiprocessing in MacOS and Linux.
	# I have had isssues with the locking of processes and the application
	# failing. To overcome this issue, spawn is denoted as the default method.
	# This is documented in this ticket: https://bugs.python.org/issue33725
	multiprocessing.set_start_method('spawn')
	# Add support for multiprocessing in frozen app
	# # See http://docs.python.org/3/library/multiprocessing.html
	multiprocessing.freeze_support()
	# Launch
	main()
