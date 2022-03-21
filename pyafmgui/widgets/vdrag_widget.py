import os
from unicodedata import name
import PyQt5
from pyqtgraph.Qt import QtGui, QtWidgets, QtCore
import pyqtgraph as pg
from pyqtgraph.parametertree import Parameter, ParameterTree
import numpy as np
import pandas as pd
from scipy.fft import fft, fftfreq

import pyafmgui.const as cts
from pyafmgui.threads import ProcessFilesThread
from pyafmgui.helpers.curve_utils import *
from pyafmgui.widgets.customdialog import CustomDialog

class VDragWidget(QtGui.QWidget):
    def __init__(self, session, parent=None):
        super(VDragWidget, self).__init__(parent)
        self.session = session
        self.current_file = None
        self.file_dict = {}
        self.session.vdrag_widget = self
        self.init_gui()
        if self.session.loaded_files != {}:
            self.updateCombo()
        if self.session.piezo_char_file_path:
            self.piezochar_text.setText(os.path.basename(self.session.piezo_char_file_path))

    def init_gui(self):
        main_layout = QtWidgets.QHBoxLayout()
        self.setLayout(main_layout)

        params_layout = QtWidgets.QVBoxLayout()

        self.pushButton = QtWidgets.QPushButton("computeButton")
        self.pushButton.setText("Compute")
        self.pushButton.clicked.connect(self.do_hertzfit)

        self.combobox = QtWidgets.QComboBox()
        self.combobox.currentTextChanged.connect(self.file_changed)

        piezochar_select_layout = QtWidgets.QGridLayout()
        self.piezochar_label = QtWidgets.QLabel("Piezo Char File")
        self.piezochar_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.piezochar_label.setMaximumWidth(150)
        self.piezochar_text = QtWidgets.QTextEdit()
        self.piezochar_text.setMaximumHeight(40)
        self.piezochar_bttn = QtWidgets.QPushButton()
        self.piezochar_bttn.setText("Browse")
        self.piezochar_bttn.clicked.connect(self.load_piezo_char)

        piezochar_select_layout.addWidget(self.piezochar_label, 0, 0, 1, 1)
        piezochar_select_layout.addWidget(self.piezochar_text, 0, 1, 1, 2)
        piezochar_select_layout.addWidget(self.piezochar_bttn, 1, 2, 1, 1)

        self.params = Parameter.create(name='params', children=cts.vdrag_params)

        self.paramTree = ParameterTree()
        self.paramTree.setParameters(self.params, showTop=False)

        self.l2 = pg.GraphicsLayoutWidget()

        params_layout.addWidget(self.combobox, 1)
        params_layout.addLayout(piezochar_select_layout, 1)
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
        self.session.vdrag_widget = None
    
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
        self.thread = ProcessFilesThread(self.session, self.params, self.filedict, "VDrag", self.dialog)
        self.thread._signal_id.connect(self.signal_accept2)
        self.thread._signal_file_progress.connect(self.signal_accept)
        self.thread._signal_curve_progress.connect(self.signal_accept3)
        self.dialog.buttonBox.rejected.connect(self.close_dialog)
        self.thread.finished.connect(self.close_dialog)
        self.thread.finished.connect(self.updatePlots)
        self.thread.start()
    
    def load_piezo_char(self):
        fname, _ = QtWidgets.QFileDialog.getOpenFileName(
        	self, 'Open file', './', "Piezo Char Files (*.csv)"
        )
        if fname != "":
            self.session.piezo_char_file_path = fname
            self.piezochar_text.setText(os.path.basename(self.session.piezo_char_file_path))
            piezo_char_data = pd.read_csv(self.session.piezo_char_file_path)
            self.session.piezo_char_data = piezo_char_data.groupby('freqs', as_index=False).median()
            if self.session.microrheo_widget:
                self.session.microrheo_widget.piezochar_text.setText(os.path.basename(self.session.piezo_char_file_path))
        else:
            self.piezochar_text.setText("")

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

        self.Bh = None
        self.Hd = None

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

        vdrag_result = self.session.vdrag_results.get(current_file_id, None)

        if vdrag_result:
            for curve_indx, curve_vdrag_result in vdrag_result:
                if curve_indx == self.session.current_curve_index:
                    self.Bh = curve_vdrag_result[1]
                    self.Hd = curve_vdrag_result[2]
                    distances = curve_vdrag_result[4]
        
        t0 = 0
        n_segments = len(curve_data)
        for i, (seg_id, seg_type, seg_data) in enumerate(curve_data):
            time = seg_data['time']
            plot_time = time + t0
            if seg_type == 'modulation':
                deltat = time[1] - time[0]
                nfft = len(seg_data['deflection'])
                W = fftfreq(nfft, d=deltat)
                fft_height = fft(seg_data['height'], nfft)
                psd_height = fft_height * np.conj(fft_height) / nfft
                fft_deflect = fft(seg_data['deflection'], nfft)
                psd_deflect = fft_deflect * np.conj(fft_deflect) / nfft
                L = np.arange(1, np.floor(nfft/2), dtype='int')
                self.p1.plot(plot_time, seg_data['height'], pen=(i,n_segments), name=f"{seg_data['frequency']} Hz")
                self.p2.plot(plot_time, seg_data['deflection'], pen=(i,n_segments), name=f"{seg_data['frequency']} Hz")
                self.p3.plot(W[L], psd_height[L].real, pen=(i,n_segments), name=f"{seg_data['frequency']} Hz")
                self.p4.plot(W[L], psd_deflect[L].real, pen=(i,n_segments), name=f"{seg_data['frequency']} Hz")
            else:
                self.p1.plot(plot_time, seg_data['height'], pen=(i,n_segments), name=f"{seg_type} {seg_id}")
                self.p2.plot(plot_time, seg_data['deflection'], pen=(i,n_segments), name=f"{seg_type} {seg_id}")
            t0 = plot_time[-1]
        
        if self.Hd is not None:
            self.p5.plot(distances, self.Hd.real, pen='r', symbol='o', symbolBrush='r', name='Hd Real')
            self.p5.plot(distances, self.Hd.imag, pen='b', symbol='o', symbolBrush='b', name='Hd Imag')
        
        if self.Bh is not None:
            self.p6.plot(distances, self.Bh, symbol='o')
        
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

        self.p5.setLabel('left', 'Hd')
        self.p5.setLabel('bottom', 'Distance', 'm')
        self.p5.setTitle("Hd-Distance")
        self.p5.addLegend()

        self.p6.setLabel('left', 'Bh', 'Ns/m')
        self.p6.setLabel('bottom', 'Distance', 'm')
        self.p6.setTitle("Bh-Distances")
        
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
