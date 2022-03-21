from doctest import FAIL_FAST
import PyQt5
from pyqtgraph.Qt import QtGui, QtWidgets, QtCore
import pyqtgraph as pg
from pyqtgraph.parametertree import Parameter, ParameterTree
from scipy.fft import fft, fftfreq
import numpy as np

import pyafmgui.const as cts
from pyafmgui.threads import ProcessFilesThread
from pyafmgui.helpers.curve_utils import *
from pyafmgui.widgets.customdialog import CustomDialog

class PiezoCharWidget(QtGui.QWidget):
    def __init__(self, session, parent=None):
        super(PiezoCharWidget, self).__init__(parent)
        self.session = session
        self.current_file = None
        self.file_dict = {}
        self.session.piezo_char_widget = self
        self.init_gui()
        if self.session.loaded_files != {}:
            self.updateCombo()

    def init_gui(self):
        main_layout = QtWidgets.QHBoxLayout()
        self.setLayout(main_layout)

        params_layout = QtWidgets.QVBoxLayout()

        self.pushButton = QtWidgets.QPushButton("computeButton")
        self.pushButton.setText("Compute")
        self.pushButton.clicked.connect(self.do_hertzfit)

        self.combobox = QtWidgets.QComboBox()
        self.combobox.currentTextChanged.connect(self.file_changed)

        self.params = Parameter.create(name='params', children=cts.piezochar_params)

        self.paramTree = ParameterTree()
        self.paramTree.setParameters(self.params, showTop=False)

        self.l2 = pg.GraphicsLayoutWidget()

        params_layout.addWidget(self.combobox, 1)
        params_layout.addWidget(self.paramTree, 3)
        params_layout.addWidget(self.pushButton, 1)
        params_layout.addWidget(self.l2, 2)

        self.l = pg.GraphicsLayoutWidget()
        
        ## Add 3 plots into the first row (automatic position)
        self.plotItem = pg.PlotItem(lockAspect=True)
        vb = self.plotItem.getViewBox()
        vb.setAspectLocked(lock=True, ratio=1)

        self.ROI = pg.ROI([0,0], [1,1], movable=False, rotatable=False, resizable=False, removable=False, aspectLocked=True)
        self.ROI.setPen("r", linewidht=2)
        self.ROI.setZValue(10)

        self.correlogram = pg.ImageItem(lockAspect=True)
        self.plotItem.addItem(self.correlogram)    # display correlogram
        
        self.p1 = pg.PlotItem()
        self.p2 = pg.PlotItem()
        self.p3 = pg.PlotItem()
        self.p4 = pg.PlotItem()
        self.p5 = pg.PlotItem()
        self.p6 = pg.PlotItem()
        self.p7 = pg.PlotItem()

        ## Put vertical label on left side
        main_layout.addLayout(params_layout, 1)
        main_layout.addWidget(self.l, 3)
    
    def closeEvent(self, evnt):
        self.session.piezo_char_widget = None
    
    def clear(self):
        self.combobox.clear()
        self.l.clear()
        self.l2.clear()

    def do_hertzfit(self):
        if not self.current_file:
            return
        self.dialog = CustomDialog("computing")
        self.dialog.show()
        if self.params.child('General Options').child('Compute All Files').value():
            self.filedict = self.session.loaded_files
        else:
            self.filedict = {self.session.current_file.file_id:self.session.current_file}
        self.dialog.pbar_files.setRange(0, len(self.filedict)-1)
        self.thread = ProcessFilesThread(self.session, self.params, self.filedict, "PiezoChar", self.dialog)
        self.thread._signal_id.connect(self.signal_accept2)
        self.thread._signal_file_progress.connect(self.signal_accept)
        self.thread._signal_curve_progress.connect(self.signal_accept3)
        self.dialog.buttonBox.rejected.connect(self.close_dialog)
        self.thread.finished.connect(self.close_dialog)
        self.thread.finished.connect(self.updatePlots)
        self.thread.start()

    def update(self):
        self.current_file = self.session.current_file
        self.updateParams()
        self.l2.clear()
        if self.current_file.file_type in ("jpk-force-map", "jpk-qi-data"):
            self.l2.addItem(self.plotItem)
            self.plotItem.addItem(self.ROI)
            self.plotItem.scene().sigMouseClicked.connect(self.mouseMoved)
            self.correlogram.setImage(self.current_file.piezo_image)
            rows, cols = self.session.current_file.piezo_image.shape
            self.plotItem.setXRange(0, cols)
            self.plotItem.setYRange(0, rows)
            curve_coords = np.arange(cols*rows).reshape((cols, rows))
            if self.session.current_file.file_type == "jpk-force-map":
                curve_coords = np.asarray([row[::(-1)**i] for i, row in enumerate(curve_coords)])
            self.session.map_coords = curve_coords
        self.session.current_curve_index = 0
        self.ROI.setPos(0, 0)
        self.updatePlots()
    
    def file_changed(self, file_id):
        self.session.current_file = self.session.loaded_files[file_id]
        self.session.current_curve_index = 0
        self.update()
    
    def updateCombo(self):
        self.combobox.addItems(self.session.loaded_files.keys())
        index = self.combobox.findText(self.current_file.file_id, QtCore.Qt.MatchFlag.MatchContains)
        if index >= 0:
            self.combobox.setCurrentIndex(index)
        self.update()
    
    def mouseMoved(self,event):
        vb = self.plotItem.vb
        scene_coords = event.scenePos()
        if self.correlogram.sceneBoundingRect().contains(scene_coords):
            items = vb.mapSceneToView(event.scenePos())
            pixels = vb.mapFromViewToItem(self.correlogram, items)
            x, y = int(pixels.x()), int(pixels.y())
            self.ROI.setPos(x, y)
            self.session.current_curve_index = self.session.map_coords[x,y]
            self.updatePlots()
            if self.session.data_viewer_widget is not None:
                self.session.data_viewer_widget.ROI.setPos(x, y)
                self.session.data_viewer_widget.updateCurve()
    
    def manual_override(self):
        pass

    def updatePlots(self):

        if not self.current_file:
            return

        self.l.clear()
        self.p1.clear()
        self.p2.clear()
        self.p3.clear()
        self.p4.clear()
        self.p5.clear()
        self.p6.clear()

        self.freqs = None
        self.fi = None
        self.amp_quot = None
        self.gamma2 = None

        analysis_params = self.params.child('Analysis Params')
        current_file_id = self.current_file.file_id
        current_file_data = self.current_file.data
        current_curve_indx = self.session.current_curve_index
        height_channel = analysis_params.child('Height Channel').value()
        deflection_sens = analysis_params.child('Deflection Sensitivity').value() / 1e9

        curve_data = preprocess_curve(current_file_data, current_curve_indx, height_channel, deflection_sens)

        modulation_segs_data = [seg_data for _, seg_type, seg_data in curve_data if seg_type == 'modulation']

        if modulation_segs_data == []:
            return

        piezo_char_result = self.session.piezo_char_results.get(current_file_id, None)

        if piezo_char_result:
            for curve_indx, curve_piezo_char_result in piezo_char_result:
                if curve_indx == self.session.current_curve_index:
                    self.freqs = curve_piezo_char_result[0]
                    self.fi = curve_piezo_char_result[1]
                    self.amp_quot = curve_piezo_char_result[2]

        t0 = 0
        n_segments = len(modulation_segs_data)
        for i, seg_data in enumerate(modulation_segs_data):
            time = seg_data['time']
            deltat = time[1] - time[0]
            nfft = len(seg_data['deflection'])
            W = fftfreq(nfft, d=deltat)
            fft_height = fft(seg_data['height'], nfft)
            psd_height = fft_height * np.conj(fft_height) / nfft
            fft_deflect = fft(seg_data['deflection'], nfft)
            psd_deflect = fft_deflect * np.conj(fft_deflect) / nfft
            L = np.arange(1, np.floor(nfft/2), dtype='int')
            plot_time = time + t0
            self.p1.plot(plot_time, seg_data['height'], pen=(i,n_segments), name=f"{seg_data['frequency']} Hz")
            self.p2.plot(plot_time, seg_data['deflection'], pen=(i,n_segments), name=f"{seg_data['frequency']} Hz")
            self.p3.plot(W[L], psd_height[L].real, pen=(i,n_segments), name=f"{seg_data['frequency']} Hz")
            self.p4.plot(W[L], psd_deflect[L].real, pen=(i,n_segments), name=f"{seg_data['frequency']} Hz")
            t0 = plot_time[-1]
         
        if self.fi is not None:
            self.p5.plot(self.freqs, self.fi, symbol='o')
        
        if self.amp_quot is not None:
            self.p6.plot(self.freqs, self.amp_quot, symbol='o')
        
        self.p1.setLabel('left', 'zHeight', 'm')
        self.p1.setLabel('bottom', 'Time', 's')
        self.p1.setTitle("zHeight-Time")
        self.p1.addLegend()

        self.p2.setLabel('left', 'Deflection', 'm')
        self.p2.setLabel('bottom', 'Time', 's')
        self.p2.setTitle("Deflection-Time")
        self.p2.addLegend()
        
        self.p3.setLabel('left', 'zHeight PSD')
        self.p3.setLabel('bottom', 'Freq', 'Hz')
        self.p3.setTitle("FFT")
        self.p3.setLogMode(True, False)
        self.p3.addLegend()

        self.p4.setLabel('left', 'Deflection PSD')
        self.p4.setLabel('bottom', 'Freq', 'Hz')
        self.p4.setTitle("FFT")
        self.p4.setLogMode(True, False)
        self.p4.addLegend()

        self.p5.setLabel('left', 'Fi', '°')
        self.p5.setLabel('bottom', 'Frequency', 'Hz')
        self.p5.setTitle("Fi-Frequency")
        self.p5.setLogMode(True, False)

        self.p6.setLabel('left', 'Amp Quotient')
        self.p6.setLabel('bottom', 'Frequency', 'Hz')
        self.p6.setTitle("Amp Quotient-Frequency")
        self.p6.setLogMode(True, False)
        
        self.l.addItem(self.p1)
        self.l.addItem(self.p2)
        self.l.nextRow()
        self.l.addItem(self.p3)
        self.l.addItem(self.p4)
        self.l.nextRow()
        self.l.addItem(self.p5)
        self.l.addItem(self.p6)
        


    def updateParams(self):
        # Updates params related to the current file
        analysis_params = self.params.child('Analysis Params')
        analysis_params.child('Height Channel').setValue(self.current_file.file_metadata['height_channel_key'])
        if self.session.global_k is None:
            analysis_params.child('Spring Constant').setValue(self.current_file.file_metadata['original_spring_constant'])
        else:
            analysis_params.child('Spring Constant').setValue(self.session.global_k)
        if self.session.global_involts is None:
            analysis_params.child('Deflection Sensitivity').setValue(self.current_file.file_metadata['original_deflection_sensitivity'])
        else:
            analysis_params.child('Deflection Sensitivity').setValue(self.session.global_involts)
    
    def close_dialog(self):
        if self.thread.isRunning():
            self.thread.exit()
        self.dialog.close()
    
    def signal_accept(self, msg):
        self.dialog.pbar_files.setValue(int(msg))
        
    def signal_accept2(self, msg):
        self.dialog.message.setText(msg)
    
    def signal_accept3(self, msg):
        self.dialog.pbar_curves.setValue(int(msg))
