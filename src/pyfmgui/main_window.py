# Import glob to find files in os
import glob
# Import GUI framework
import PyQt5
from pyqtgraph.Qt import QtGui, QtCore, QtWidgets
# Import logging and get global logger
import logging
logger = logging.getLogger()
# Get methods and objects needed
from pyfmgui.const import pyFM_VERSION
from pyfmgui.loadfiles import loadfiles
from pyfmgui.threading import Worker
from pyfmgui.widgets.exportdialog import ExportDialog
from pyfmgui.widgets.hertzfit_widget import HertzFitWidget
from pyfmgui.widgets.tingfit_widget import TingFitWidget
from pyfmgui.widgets.piezochar_widget import PiezoCharWidget
from pyfmgui.widgets.vdrag_widget import VDragWidget
from pyfmgui.widgets.microrheo_widget import MicrorheoWidget
from pyfmgui.widgets.dataviewer_widget import DataViewerWidget
from pyfmgui.widgets.thermaltune_widget import ThermalTuneWidget
from pyfmgui.widgets.macro_widget import MacroWidget
from pyfmgui.widgets.logger_dialog import LoggerDialog
from pyfmgui.widgets.progress_dialog import ProgressDialog

class MainWindow(QtWidgets.QMainWindow):
	def __init__(self, session, parent = None):
		super(MainWindow, self).__init__(parent)
		self.session = session
		self.init_gui()
		
	def init_gui(self):
		self.setWindowTitle(pyFM_VERSION)

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

		openLoggerDialog = QtGui.QAction("Logs", self)
		openLoggerDialog.setToolTip("Open Logger Dialog.")
		openLoggerDialog.triggered.connect(self.open_analysis_window)
		
		self.toolbar.addAction(openDataViewer)
		self.toolbar.addAction(openCalibrationManager)
		self.toolbar.addAction(openHertzFit)
		self.toolbar.addAction(openTingFit)
		self.toolbar.addAction(openPiezoChar)
		self.toolbar.addAction(openVDrag)
		self.toolbar.addAction(openMicrorheo)
		self.toolbar.addAction(openMacro)
		self.toolbar.addAction(openLoggerDialog)

		# Setup the logger widget
		self.session.logger_wiget = LoggerDialog(self)
		self.add_subwindow(self.session.logger_wiget, 'Logs')
		logger.info('Started application')
		logger.info('No data loaded')

		# Setup the progressbar widget
		self.session.pbar_widget = ProgressDialog()
		# self.add_subwindow(self.session.pbar_widget, 'Progress Bar')
		# self.session.pbar_widget.setVisible(False)

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
		if action == "Data Viewer":
			if self.session.data_viewer_widget is None:
				widget_to_open = DataViewerWidget(self.session)
			elif self.session.data_viewer_widget.isMaximized():
				self.session.data_viewer_widget.showMinimized()
			else:
				self.session.data_viewer_widget.showMaximized()
		elif action == "Thermal Tune":
			if self.session.thermal_tune_widget is None:
				widget_to_open = ThermalTuneWidget(self.session)
			elif self.session.thermal_tune_widget.isMaximized():
				self.session.thermal_tune_widget.showMinimized()
			else:
				self.session.thermal_tune_widget.showMaximized()
		elif action == "Elasticity Fit":
			if self.session.hertz_fit_widget is None:
				widget_to_open = HertzFitWidget(self.session)
			elif self.session.hertz_fit_widget.isMaximized():
				self.session.hertz_fit_widget.showMinimized()
			else:
				self.session.hertz_fit_widget.showMaximized()
		elif action == "Viscoelasticity Fit":
			if self.session.ting_fit_widget is None:
				widget_to_open = TingFitWidget(self.session)
			elif self.session.ting_fit_widget.isMaximized():
				self.session.ting_fit_widget.showMinimized()
			else:
				self.session.ting_fit_widget.showMaximized()
		elif action == "Piezo Characterization":
			if self.session.piezo_char_widget is None:
				widget_to_open = PiezoCharWidget(self.session)
			elif self.session.piezo_char_widget.isMaximized():
				self.session.piezo_char_widget.showMinimized()
			else:
				self.session.piezo_char_widget.showMaximized()
		elif action == "Viscous Drag":
			if self.session.vdrag_widget is None:
				widget_to_open = VDragWidget(self.session)
			elif self.session.vdrag_widget.isMaximized():
				self.session.vdrag_widget.showMinimized()
			else:
				self.session.vdrag_widget.showMaximized()
		elif action == "Microrheology":
			if self.session.microrheo_widget is None:
				widget_to_open = MicrorheoWidget(self.session)
			elif self.session.microrheo_widget.isMaximized():
				self.session.microrheo_widget.showMinimized()
			else:
				self.session.microrheo_widget.showMaximized()
		elif action == "Macrowidget":
			if self.session.macro_widget is None:
				widget_to_open = MacroWidget(self.session)
			elif self.session.macro_widget.isMaximized():
				self.session.macro_widget.showMinimized()
			else:
				self.session.macro_widget.showMaximized()
		elif action == "Logs":
			if self.session.logger_wiget is None:
				widget_to_open = self.session.logger_wiget
			elif self.session.logger_wiget.isMaximized():
				self.session.logger_wiget.showMinimized()
			else:
				self.session.logger_wiget.showMaximized()
		
		if widget_to_open is not None:
			self.add_subwindow(widget_to_open, action)
			
	def windowaction(self, q):
		if q.text() == "Load Single File":
			fname, _ = QtWidgets.QFileDialog.getOpenFileName(
				self, 
				'Open file', 
				r'./', 
				"""
				JPK files (*.jpk-force *.jpk-force-map *.jpk-qi-data, *.jpk-force.zip *.jpk-force-map.zip *.jpk-qi-data.zip);;
				Nanoscope files (*.spm *.pfc)
				"""
			)
			if fname != "" and fname is not None:
				self.load_files([fname])
		if q.text() == "Load Folder":
			dirname = QtWidgets.QFileDialog.getExistingDirectory(
				self, 'Choose Directory', r'./'
			)
			if dirname != "" and dirname is not None:
				valid_files = self.getFileList(dirname)
				if valid_files != []:
					self.load_files(valid_files)
		if q.text() == "Export Results":
			if self.session.export_dialog is None:
				self.session.export_dialog = ExportDialog(self.session)
			self.add_subwindow(self.session.export_dialog, 'Export Data')
		if q.text() == "Cascade":
			self.mdi.cascadeSubWindows()
		if q.text() == "Tiled":
			self.mdi.tileSubWindows()
		if q.text() == "Remove All Files And Results":
			self.remove_all_files_and_results()
	
	def getFileList(self, directory):
		types = ('*.jpk-force', '*.jpk-force-map', '*.jpk-qi-data', '*.jpk-force.zip', '*.jpk-force-map.zip', '*.jpk-qi-data.zip', '*.spm', '*.pfc')
		dataset_files = []
		for files in types:
			dataset_files.extend(glob.glob(f'{directory}/**/{files}', recursive=True))
		return dataset_files
	
	def load_files(self, filelist):
		self.session.pbar_widget.reset_pbar()
		self.session.pbar_widget.set_label_text('Loading Files...')
		self.session.pbar_widget.set_label_sub_text('')
		self.session.pbar_widget.show()
		self.session.pbar_widget.set_pbar_range(0, len(filelist))
		self.thread = QtCore.QThread()
		self.worker = Worker(loadfiles, self.session, filelist)
		self.worker.moveToThread(self.thread)
		self.thread.started.connect(self.worker.run)
		self.worker.signals.progress.connect(self.reportProgress)
		self.worker.signals.finished.connect(self.oncomplete) # Reset button
		self.thread.start()
	
	def reportProgress(self, n):
		self.session.pbar_widget.set_pbar_value(n)
	
	def oncomplete(self):
		self.thread.terminate()
		self.session.pbar_widget.hide()
		self.session.pbar_widget.reset_pbar()
		self.close_dialog()
		logger.info(f'Loaded {len(self.session.loaded_files)} files.')

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