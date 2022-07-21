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
from pyafmgui.compute import compute
from pyafmgui.widgets.get_params import get_params

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
        if self.params.child('General Options').child('Compute All Files').value():
            self.filedict = self.session.loaded_files
        else:
            self.filedict = {self.session.current_file.filemetadata['Entry_filename']:self.session.current_file}
        params = get_params(self.params, "VDrag")
        params['piezo_char_data'] = self.session.piezo_char_data
        compute(self.session, params,  self.filedict, "VDrag")
        self.updatePlots()
    
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
        if self.current_file.isFV:
            self.l2.addItem(self.plotItem)
            self.plotItem.addItem(self.ROI)
            self.plotItem.scene().sigMouseClicked.connect(self.mouseMoved)
            # create transform to center the corner element on the origin, for any assigned image:
            if self.session.current_file.filemetadata['file_type'] in cts.jpk_file_extensions:
                img = self.session.current_file.imagedata.get('Height(measured)', None)
                if img is None:
                    img = self.session.current_file.imagedata.get('Height', None)
                img = np.rot90(np.fliplr(img))
                shape = img.shape
                rows, cols = shape[0], shape[1]
                curve_coords = np.arange(cols*rows).reshape((cols, rows))
                curve_coords = np.rot90(np.fliplr(curve_coords))
            elif self.session.current_file.filemetadata['file_type'] in cts.nanoscope_file_extensions:
                img = self.session.current_file.piezoimg
                shape = img.shape
                rows, cols = shape[0], shape[1]
                curve_coords = np.arange(cols*rows).reshape((cols, rows))
            self.correlogram.setImage(img)
            shape = img.shape
            rows, cols = shape[0], shape[1]
            self.plotItem.setXRange(0, cols)
            self.plotItem.setYRange(0, rows)
            curve_coords = np.arange(cols*rows).reshape((cols, rows))
            if self.session.current_file.filemetadata['file_type'] == "jpk-force-map":
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
        self.combobox.clear()
        self.combobox.addItems(self.session.loaded_files.keys())
        index = self.combobox.findText(self.current_file.filemetadata['Entry_filename'], QtCore.Qt.MatchFlag.MatchContains)
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
        current_file_id = self.current_file.filemetadata['Entry_filename']
        current_file = self.current_file
        current_curve_indx = self.session.current_curve_index
        height_channel = analysis_params.child('Height Channel').value()
        deflection_sens = analysis_params.child('Deflection Sensitivity').value() / 1e9

        force_curve = current_file.getcurve(current_curve_indx)
        force_curve.preprocess_force_curve(deflection_sens, height_channel)

        modulation_segs = force_curve.modulation_segments

        if modulation_segs == []:
            return

        vdrag_result = self.session.vdrag_results.get(current_file_id, None)

        if vdrag_result:
            for curve_indx, curve_vdrag_result in vdrag_result:
                if curve_indx == self.session.current_curve_index:
                    self.Bh = curve_vdrag_result[1]
                    self.Hd = curve_vdrag_result[2]
                    distances = curve_vdrag_result[4]
        
        curve_segments = force_curve.get_segments()
        
        t0 = 0
        n_segments = len(curve_segments)
        for i, (seg_id, segment) in enumerate(curve_segments):
            time = segment.time
            plot_time = time + t0
            if segment.segment_type == 'modulation':
                freq = segment.segment_metadata['frequency']
                deltat = time[1] - time[0]
                nfft = len(segment.vdeflection)
                W = fftfreq(nfft, d=deltat)
                fft_height = fft(segment.zheight, nfft)
                psd_height = fft_height * np.conj(fft_height) / nfft
                fft_deflect = fft(segment.vdeflection, nfft)
                psd_deflect = fft_deflect * np.conj(fft_deflect) / nfft
                L = np.arange(1, np.floor(nfft/2), dtype='int')
                self.p1.plot(plot_time, segment.zheight, pen=(i,n_segments), name=f"{freq} Hz")
                self.p2.plot(plot_time, segment.vdeflection, pen=(i,n_segments), name=f"{freq} Hz")
                self.p3.plot(W[L], psd_height[L].real, pen=(i,n_segments), name=f"{freq} Hz")
                self.p4.plot(W[L], psd_deflect[L].real, pen=(i,n_segments), name=f"{freq} Hz")
            else:
                self.p1.plot(plot_time, segment.zheight, pen=(i,n_segments), name=f"{segment.segment_type} {seg_id}")
                self.p2.plot(plot_time, segment.vdeflection, pen=(i,n_segments), name=f"{segment.segment_type} {seg_id}")
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
        analysis_params.child('Height Channel').setValue(self.current_file.filemetadata['height_channel_key'])
        if self.session.global_k is None:
            analysis_params.child('Spring Constant').setValue(self.current_file.filemetadata['spring_const_Nbym'])
        else:
            analysis_params.child('Spring Constant').setValue(self.session.global_k)
        if self.session.global_involts is None:
            analysis_params.child('Deflection Sensitivity').setValue(self.current_file.filemetadata['defl_sens_nmbyV'])
        else:
            analysis_params.child('Deflection Sensitivity').setValue(self.session.global_involts)
