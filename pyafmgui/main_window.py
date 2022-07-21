import glob
import PyQt5
from pyqtgraph.Qt import QtGui, QtCore, QtWidgets

from pyafmgui.loadfiles import loadfiles

from pyafmgui.widgets.customdialog import CustomDialog
from pyafmgui.widgets.exportdialog import ExportDialog
from pyafmgui.widgets.hertzfit_widget import HertzFitWidget
from pyafmgui.widgets.tingfit_widget import TingFitWidget
from pyafmgui.widgets.piezochar_widget import PiezoCharWidget
from pyafmgui.widgets.vdrag_widget import VDragWidget
from pyafmgui.widgets.microrheo_widget import MicrorheoWidget
from pyafmgui.widgets.dataviewer_widget import DataViewerWidget
from pyafmgui.widgets.thermaltune_widget import ThermalTuneWidget
from pyafmgui.widgets.macro_widget import MacroWidget

class MainWindow(QtWidgets.QMainWindow):
	def __init__(self, session, parent = None):
		super(MainWindow, self).__init__(parent)
		self.session = session
		self.init_gui()
		
	def init_gui(self):
		self.setWindowTitle("PyAFMRheo v.0.0.3")

		self.mdi = QtWidgets.QMdiArea()
		self.setCentralWidget(self.mdi)
		
		bar = self.menuBar()
		file = bar.addMenu("File")
		file.addAction("Load Single File")
		file.addAction("Load Folder")
		file.addAction("Export Results")
		file.addAction("Remove All Files And Results")
		view = bar.addMenu("View")
		view.addAction("Cascade")
		view.addAction("Tiled")
		file.triggered[QtGui.QAction].connect(self.windowaction)
		view.triggered[QtGui.QAction].connect(self.windowaction)

		self.toolbar = QtWidgets.QToolBar("My main toolbar")
		self.toolbar.setIconSize(QtCore.QSize(16,16))
		self.addToolBar(self.toolbar)

		openDataViewer = QtGui.QAction("Data Viewer", self)
		openDataViewer.setToolTip("Open Data Viewer window.")
		openDataViewer.triggered.connect(self.open_analysis_window)

		openCalibrationManager = QtGui.QAction("Thermal Tune", self)
		openCalibrationManager.setToolTip("Open new thermal tune window.")
		openCalibrationManager.triggered.connect(self.open_analysis_window)
		
		openHertzFit = QtGui.QAction("Elasticity Fit", self)
		openHertzFit.setToolTip("Open new Hertz Fit data analysis window.")
		openHertzFit.triggered.connect(self.open_analysis_window)

		openTingFit = QtGui.QAction("Viscoelasticity Fit", self)
		openTingFit.setToolTip("Open new Hertz Fit data analysis window.")
		openTingFit.triggered.connect(self.open_analysis_window)

		openPiezoChar = QtGui.QAction("Piezo Characterization", self)
		openPiezoChar.setToolTip("Open new Hertz Fit data analysis window.")
		openPiezoChar.triggered.connect(self.open_analysis_window)

		openVDrag = QtGui.QAction("Viscous Drag", self)
		openVDrag.setToolTip("Open new Hertz Fit data analysis window.")
		openVDrag.triggered.connect(self.open_analysis_window)

		openMicrorheo = QtGui.QAction("Microrheology", self)
		openMicrorheo.setToolTip("Open new Hertz Fit data analysis window.")
		openMicrorheo.triggered.connect(self.open_analysis_window)

		openMacro = QtGui.QAction("Macrowidget", self)
		openMacro.setToolTip("Open new Macro window.")
		openMacro.triggered.connect(self.open_analysis_window)
		
		self.toolbar.addAction(openDataViewer)
		self.toolbar.addAction(openCalibrationManager)
		self.toolbar.addAction(openHertzFit)
		self.toolbar.addAction(openTingFit)
		self.toolbar.addAction(openPiezoChar)
		self.toolbar.addAction(openVDrag)
		self.toolbar.addAction(openMicrorheo)
		self.toolbar.addAction(openMacro)
	
	def add_subwindow(self, widget, tittle):
		sub = QtWidgets.QMdiSubWindow()
		sub.setWidget(widget)
		sub.setWindowTitle(tittle)
		self.mdi.addSubWindow(sub)
		sub.show()
	
	@QtCore.pyqtSlot()
	def open_analysis_window(self):
		widget_to_open = None
		action = self.sender().text()
		if action == "Data Viewer" and self.session.data_viewer_widget is None:
			widget_to_open = DataViewerWidget(self.session)
		elif action == "Thermal Tune" and self.session.thermal_tune_widget is None:
			widget_to_open = ThermalTuneWidget(self.session)
		elif action == "Elasticity Fit" and self.session.hertz_fit_widget is None:
			widget_to_open = HertzFitWidget(self.session)
		elif action == "Viscoelasticity Fit" and self.session.ting_fit_widget is None:
			widget_to_open = TingFitWidget(self.session)
		elif action == "Piezo Characterization" and self.session.piezo_char_widget is None:
			widget_to_open = PiezoCharWidget(self.session)
		elif action == "Viscous Drag" and self.session.vdrag_widget is None:
			widget_to_open = VDragWidget(self.session)
		elif action == "Microrheology" and self.session.microrheo_widget is None:
			widget_to_open = MicrorheoWidget(self.session)
		elif action == "Macrowidget":
			widget_to_open = MacroWidget(self.session)
		if widget_to_open is not None:
			self.add_subwindow(widget_to_open, action)
			
	def windowaction(self, q):
		if q.text() == "Load Single File":
			fname, _ = QtWidgets.QFileDialog.getOpenFileName(
				self, 
				'Open file', 
				'./', 
				"""
				JPK files (*.jpk-force *.jpk-force-map *.jpk-qi-data);;
				Nanoscope files (*.spm *.pfc)
				"""
			)
			if fname != "" and fname is not None:
				self.load_files([fname])
		if q.text() == "Load Folder":
			dirname = QtWidgets.QFileDialog.getExistingDirectory(
				self, 'Choose Directory', './'
			)
			if dirname != "" and dirname is not None:
				valid_files = self.getFileList(dirname)
				if valid_files != []:
					self.load_files(valid_files)
		if q.text() == "Export Results":
			export_dialog = ExportDialog(self.session)
			self.add_subwindow(export_dialog, 'Export Data')
		if q.text() == "Cascade":
			self.mdi.cascadeSubWindows()
		if q.text() == "Tiled":
			self.mdi.tileSubWindows()
		if q.text() == "Remove All Files And Results":
			self.remove_all_files_and_results()
	
	def getFileList(self, directory):
		types = ('*.jpk-force', '*.jpk-force-map', '*.jpk-qi-data', '*.spm', '*.pfc')
		dataset_files = []
		for files in types:
			dataset_files.extend(glob.glob(f'{directory}/**/{files}', recursive=True))
		return dataset_files
	
	def load_files(self, filelist):
		loadfiles(self.session, filelist)
		self.close_dialog()

	def signal_accept(self, msg):
		self.dialog.pbar_files.setValue(int(msg))
	
	def signal_accept2(self, msg):
		self.dialog.label.setText(msg)
	
	def close_dialog(self):
		if self.session.data_viewer_widget:
			self.session.data_viewer_widget.updateTable()
		if self.session.hertz_fit_widget:
			self.session.hertz_fit_widget.updateCombo()
		if self.session.ting_fit_widget:
			self.session.ting_fit_widget.updateCombo()
		if self.session.piezo_char_widget:
			self.session.piezo_char_widget.updateCombo()
		if self.session.vdrag_widget:
			self.session.vdrag_widget.updateCombo()
		if self.session.microrheo_widget:
			self.session.microrheo_widget.updateCombo()
	
	def remove_all_files_and_results(self):
		self.session.remove_data_and_results()
		if self.session.data_viewer_widget:
			self.session.data_viewer_widget.clear()
		if self.session.hertz_fit_widget:
			self.session.hertz_fit_widget.clear()
		if self.session.ting_fit_widget:
			self.session.ting_fit_widget.clear()
		if self.session.piezo_char_widget:
			self.session.piezo_char_widget.clear()
		if self.session.vdrag_widget:
			self.session.vdrag_widget.clear()
		if self.session.microrheo_widget:
			self.session.microrheo_widget.clear()