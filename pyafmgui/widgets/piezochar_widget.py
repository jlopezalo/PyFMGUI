from doctest import FAIL_FAST
import PyQt5
from pyqtgraph.Qt import QtGui, QtWidgets, QtCore
import pyqtgraph as pg
from pyqtgraph.parametertree import Parameter, ParameterTree
from scipy.fft import fft, fftfreq
import numpy as np
import logging
logger = logging.getLogger()

import pyafmgui.const as cts
from pyafmgui.threading import Worker
from pyafmgui.compute import compute
from pyafmgui.widgets.get_params import get_params

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
        if self.params.child('General Options').child('Compute All Files').value():
            filedict = self.session.loaded_files
        else:
            filedict = {self.session.current_file.filemetadata['Entry_filename']:self.session.current_file}
        params = get_params(self.params, 'PiezoChar')
        logger.info('Started PiezoCharacterization...')
        logger.info(f'Processing {len(filedict)} files')
        logger.info(f'Analysis parameters used: {params}')
        self.session.pbar_widget.reset_pbar()
        self.session.pbar_widget.set_label_text('Computing PiezoCharacterization...')
        self.session.pbar_widget.show()
        self.session.pbar_widget.set_pbar_range(0, len(filedict))
        # Create thread to run compute
        self.thread = QtCore.QThread()
        # Create worker to run compute
        self.worker = Worker(compute, self.session, params, filedict, "PiezoChar")
        # Move worker to thread
        self.worker.moveToThread(self.thread)
        # When thread starts run worker
        self.thread.started.connect(self.worker.run)
        self.worker.signals.progress.connect(self.reportProgress)
        self.worker.signals.range.connect(self.setPbarRange)
        self.worker.signals.step.connect(self.changestep)
        self.worker.signals.finished.connect(self.oncomplete) # Reset button
        # Start thread
        self.thread.start()
        # Final resets
        self.pushButton.setEnabled(False) # Prevent user from starting another
        # Update the gui
        self.updatePlots()
    
    def changestep(self, step):
        self.session.pbar_widget.set_label_sub_text(step)
    
    def reportProgress(self, n):
        self.session.pbar_widget.set_pbar_value(n)

    def setPbarRange(self, n):
        self.session.pbar_widget.set_pbar_range(0, n)
    
    def oncomplete(self):
        self.thread.terminate()
        self.session.pbar_widget.hide()
        self.session.pbar_widget.reset_pbar()
        self.pushButton.setEnabled(True)
        self.updatePlots()
        logger.info('PiezoCharacterization completed!')
    
    def open_msg_box(self, message):
        dlg = QtWidgets.QMessageBox(self)
        dlg.setWindowTitle("Export Status")
        dlg.setText(message)
        dlg.exec()

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

        self.freqs = None
        self.fi = None
        self.amp_quot = None
        self.gamma2 = None

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
            self.open_msg_box(f'No modulation segments found in file:\n {current_file_id}')
            return

        piezo_char_result = self.session.piezo_char_results.get(current_file_id, None)

        if piezo_char_result:
            for curve_indx, curve_piezo_char_result in piezo_char_result:
                try:
                    if curve_piezo_char_result is None:
                        continue
                    if curve_indx == self.session.current_curve_index:
                        self.freqs = curve_piezo_char_result[0]
                        self.fi = curve_piezo_char_result[1]
                        self.amp_quot = curve_piezo_char_result[2]
                except Exception:
                    continue
        t0 = 0
        n_segments = len(modulation_segs)
        for i, (_, segment) in enumerate(modulation_segs):
            time = segment.time
            freq = segment.segment_metadata['frequency']
            deltat = time[1] - time[0]
            nfft = len(segment.vdeflection)
            W = fftfreq(nfft, d=deltat)
            fft_height = fft(segment.zheight, nfft)
            psd_height = fft_height * np.conj(fft_height) / nfft
            fft_deflect = fft(segment.vdeflection, nfft)
            psd_deflect = fft_deflect * np.conj(fft_deflect) / nfft
            L = np.arange(1, np.floor(nfft/2), dtype='int')
            plot_time = time + t0
            self.p1.plot(plot_time, segment.zheight, pen=(i,n_segments), name=f"{freq} Hz")
            self.p2.plot(plot_time, segment.vdeflection, pen=(i,n_segments), name=f"{freq} Hz")
            self.p3.plot(W[L], psd_height[L].real, pen=(i,n_segments), name=f"{freq} Hz")
            self.p4.plot(W[L], psd_deflect[L].real, pen=(i,n_segments), name=f"{freq} Hz")
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
        analysis_params.child('Height Channel').setValue(self.current_file.filemetadata['height_channel_key'])
        if self.session.global_k is None:
            analysis_params.child('Spring Constant').setValue(self.current_file.filemetadata['spring_const_Nbym'])
        else:
            analysis_params.child('Spring Constant').setValue(self.session.global_k)
        if self.session.global_involts is None:
            analysis_params.child('Deflection Sensitivity').setValue(self.current_file.filemetadata['defl_sens_nmbyV'])
        else:
            analysis_params.child('Deflection Sensitivity').setValue(self.session.global_involts)
