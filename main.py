import sys
import PyQt6
from pyqtgraph.Qt import QtGui, QtCore, QtWidgets

import pyqtgraph.graphicsItems.ViewBox.axisCtrlTemplate_pyqt6
import pyqtgraph.graphicsItems.PlotItem.plotConfigTemplate_pyqt6
import pyqtgraph.imageview.ImageViewTemplate_pyqt6


from pyafmgui.main_window import MainWindow
from pyafmgui.session import Session

def main():
	app = QtWidgets.QApplication(sys.argv)
	# Force the style to be the same on all OSs:
	app.setStyle("Fusion")
	
	# Define the colour palette of the application:
	palette = QtGui.QPalette()
	palette.setColor(QtGui.QPalette.ColorRole.Window, QtGui.QColor(53, 53, 53))
	palette.setColor(QtGui.QPalette.ColorRole.WindowText, QtCore.Qt.GlobalColor.white)
	palette.setColor(QtGui.QPalette.ColorRole.Base, QtGui.QColor(25, 25, 25))
	palette.setColor(QtGui.QPalette.ColorRole.AlternateBase, QtGui.QColor(53, 53, 53))
	palette.setColor(QtGui.QPalette.ColorRole.ToolTipBase, QtCore.Qt.GlobalColor.black)
	palette.setColor(QtGui.QPalette.ColorRole.ToolTipText, QtCore.Qt.GlobalColor.white)
	palette.setColor(QtGui.QPalette.ColorRole.Text, QtCore.Qt.GlobalColor.white)
	palette.setColor(QtGui.QPalette.ColorRole.Button, QtGui.QColor(53, 53, 53))
	palette.setColor(QtGui.QPalette.ColorRole.ButtonText, QtCore.Qt.GlobalColor.white)
	palette.setColor(QtGui.QPalette.ColorRole.BrightText, QtCore.Qt.GlobalColor.red)
	palette.setColor(QtGui.QPalette.ColorRole.Link, QtGui.QColor(42, 130, 218))
	palette.setColor(QtGui.QPalette.ColorRole.Highlight, QtGui.QColor(42, 130, 218))
	palette.setColor(QtGui.QPalette.ColorRole.HighlightedText, QtCore.Qt.GlobalColor.black)
	
	# Set colour palette on the application.
	app.setPalette(palette)
	session = Session()
	ex = MainWindow(session)
	ex.show()
	sys.exit(app.exec())
	
if __name__ == '__main__':
    main()