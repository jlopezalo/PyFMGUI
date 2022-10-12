import PyQt5
from pyqtgraph.Qt import QtGui, QtWidgets, QtCore
import pyqtgraph as pg
from pyqtgraph.parametertree import Parameter, ParameterTree
import numpy as np
import logging
logger = logging.getLogger()

import pyafmgui.const as cts
from pyafmgui.threading import Worker
from pyafmgui.compute import compute
from pyafmgui.widgets.get_params import get_params

from pyafmrheo.utils.force_curves import get_poc_RoV_method, correct_tilt

class HertzFitWidget(QtGui.QWidget):
    def __init__(self, session, parent=None):
        super(HertzFitWidget, self).__init__(parent)
        self.session = session
        self.current_file = None
        self.min_val_line = None
        self.max_val_line = None
        self.tilt_roi = None
        self.file_dict = {}
        self.session.hertz_fit_widget = self
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

        self.params = Parameter.create(name='params', children=cts.hertzfit_params)

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
        self.p2legend = self.p2.addLegend()
        self.p3 = pg.PlotItem()
        self.p4 = pg.PlotItem()

        ## Put vertical label on left side
        main_layout.addLayout(params_layout, 1)
        main_layout.addWidget(self.l, 3)
    
    def closeEvent(self, evnt):
        self.session.hertz_fit_widget = None
    
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
        params = get_params(self.params, "HertzFit")
        logger.info('Started ElasticityFit...')
        logger.info(f'Processing {len(filedict)} files')
        logger.info(f'Analysis parameters used: {params}')
        self.session.pbar_widget.reset_pbar()
        self.session.pbar_widget.set_label_text('Computing ElasticityFit...')
        self.session.pbar_widget.show()
        # Create thread to run compute
        self.thread = QtCore.QThread()
        # Create worker to run compute
        self.worker = Worker(compute, self.session, params, filedict, "HertzFit")
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
        logger.info('ElasticityFit completed!')

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
            if self.current_file.filemetadata['file_type'] == "jpk-force-map":
                curve_coords = np.asarray([row[::(-1)**i] for i, row in enumerate(curve_coords)])
            self.session.map_coords = curve_coords
        self.session.current_curve_index = 0
        self.ROI.setPos(0, 0)
        self.updatePlots()
    
    def file_changed(self, file_id):
        if file_id != '':
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
        self.p2legend.clear()
        self.p3.clear()
        self.p4.clear()

        self.hertz_E = None
        self.hertz_d0 = 0
        self.fit_data = None
        self.residual = None

        current_file_id = self.current_file.filemetadata['Entry_filename']
        current_curve_indx = self.session.current_curve_index
        
        analysis_params = self.params.child('Analysis Params')
        height_channel = analysis_params.child('Height Channel').value()
        deflection_sens = analysis_params.child('Deflection Sensitivity').value() / 1e9
        spring_k = analysis_params.child('Spring Constant').value()
        curve_seg = analysis_params.child('Curve Segment').value()
        correct_tilt_flag = analysis_params.child('Correct Tilt').value()
        tilt_min_offset = analysis_params.child('Min Tilt Offset').value() / 1e9
        tilt_max_offset = analysis_params.child('Max Tilt Offset').value() / 1e9
        
        hertz_params = self.params.child('Hertz Fit Params')
        poc_win = hertz_params.child('PoC Window').value() / 1e9

        force_curve = self.current_file.getcurve(current_curve_indx)
        force_curve.preprocess_force_curve(deflection_sens, height_channel)

        if self.session.current_file.filemetadata['file_type'] in cts.jpk_file_extensions:
            force_curve.shift_height()

        file_hertz_result = self.session.hertz_fit_results.get(current_file_id, None)

        # print(file_hertz_result)
        # print(current_file_id)

        if file_hertz_result is not None:
            for curve_indx, curve_hertz_result in file_hertz_result:
                try:
                    if curve_hertz_result is None:
                        continue
                    if curve_indx == self.session.current_curve_index:
                        self.hertz_E = curve_hertz_result.E0
                        self.hertz_d0 = curve_hertz_result.delta0
                        self.hertz_f0 = curve_hertz_result.f0
                        self.hertz_redchi = curve_hertz_result.redchi
                        self.fit_data = curve_hertz_result
                except Exception:
                    continue

        ext_data = force_curve.extend_segments[0][1]
        ret_data = force_curve.retract_segments[-1][1]

        self.p3.plot(ext_data.zheight, ext_data.vdeflection)
        self.p3.plot(ret_data.zheight, ret_data.vdeflection)

        if curve_seg == 'extend':
            zheight  = ext_data.zheight
            vdeflect = ext_data.vdeflection
            
        else:
            zheight  = ret_data.zheight[::-1]
            vdeflect = ret_data.vdeflection[::-1]
        
        rov_PoC = get_poc_RoV_method(zheight, vdeflect, poc_win)
        poc = [rov_PoC[0], 0]

        # Perform tilt correction
        if correct_tilt_flag:
            height = np.r_[ext_data.zheight, ret_data.zheight]
            deflection = np.r_[ext_data.vdeflection, ret_data.vdeflection]
            idx = len(ext_data.zheight)
            corr_defl = correct_tilt(
                height, deflection, poc[0],
                tilt_max_offset, tilt_min_offset
            )
            ext_data.vdeflection = corr_defl[:idx]
            ret_data.vdeflection = corr_defl[idx:]

        force_curve.get_force_vs_indentation(poc, spring_k)

        if curve_seg == 'extend':
            self.indentation  = ext_data.indentation
            self.force = ext_data.force
            self.force = self.force - self.force[0]
            
        else:
            self.indentation  = ret_data.indentation
            self.force = ret_data.force
            self.force = self.force - self.force[-1]

        self.p1.plot(self.indentation, self.force)
        vertical_line = pg.InfiniteLine(pos=0, angle=90, pen='y', movable=False, label='RoV d0', labelOpts={'color':'y', 'position':0.5})
        self.p1.addItem(vertical_line, ignoreBounds=True)
        if self.hertz_d0 != 0:
            d0_vertical_line = pg.InfiniteLine(pos=self.hertz_d0, angle=90, pen='g', movable=False, label='Hertz d0', labelOpts={'color':'g', 'position':0.7})
            self.p1.addItem(d0_vertical_line, ignoreBounds=True)

        self.p2.plot(self.indentation - self.hertz_d0, self.force)

        self.update_fit_range()
        self.update_tilt_range()
 
        if self.fit_data is not None:
            x = self.indentation
            y = self.fit_data.eval(x)
            self.p2.plot(x - self.hertz_d0, y, pen ='g', name='Fit')
            style = pg.PlotDataItem(pen=None)
            self.p2legend.addItem(style, f'Hertz E: {self.hertz_E:.2f} Pa')
            self.p2legend.addItem(style, f'Hertz d0: {self.hertz_d0 + poc[0]:.3E} m')
            self.p2legend.addItem(style, f'Red. Chi: {self.hertz_redchi:.3E}')
            res = self.p4.plot(x - self.hertz_d0, self.fit_data.get_residuals(x, self.force), pen=None, symbol='o')
            res.setSymbolSize(5)
        
        self.p1.setLabel('left', 'Force', 'N')
        self.p1.setLabel('bottom', 'Indentation', 'm')
        self.p1.setTitle("Force-Indentation")
        self.p1.addLegend()
        self.p2.setLabel('left', 'Force', 'N')
        self.p2.setLabel('bottom', 'Indentation', 'm')
        self.p2.setTitle("Force-Indentation Hertz Fit")
        self.p3.setLabel('left', 'Deflection', 'm')
        self.p3.setLabel('bottom', 'zHeight', 'm')
        self.p3.setTitle('Deflection-zHeight')
        self.p4.setLabel('left', 'Residuals')
        self.p4.setLabel('bottom', 'Indentation', 'm')
        self.p4.setTitle("Hertz Fit Residuals")

        self.l.addItem(self.p1)
        self.l.addItem(self.p2)
        self.l.nextRow()
        self.l.addItem(self.p3)
        self.l.addItem(self.p4)
    
    def update_tilt_range(self):
        dataItems = self.p1.listDataItems()
        analysis_params = self.params.child('Analysis Params')
        correct_tilt = analysis_params.child('Correct Tilt').value()
        tilt_min_offset = analysis_params.child('Min Tilt Offset').value() / 1e9
        tilt_max_offset = analysis_params.child('Max Tilt Offset').value() / 1e9
        if self.tilt_roi is not None:
            self.p1.removeItem(self.tilt_roi)
        if correct_tilt:
            self.tilt_roi = pg.LinearRegionItem(brush=(50,50,200,0), pen='w', movable=False)
            self.tilt_roi.setZValue(10)
            self.tilt_roi.setClipItem(dataItems[0])
            self.p1.removeItem(self.tilt_roi)
            self.p1.addItem(self.tilt_roi, ignoreBounds=True)
            self.tilt_roi.setRegion([-1 * tilt_min_offset, -1 * tilt_max_offset])
        else:
            self.tilt_roi = None

    def update_fit_range(self):
        hertz_params = self.params.child('Hertz Fit Params')
        fit_range_type = hertz_params.child('Fit Range Type').value()
        if fit_range_type == 'full':
            angle=90
            min_val = 0.0
            max_val = np.max(self.indentation - self.hertz_d0)
            hertz_params.child('Min Indentation').setValue(min_val * 1e9)
            hertz_params.child('Max Indentation').setValue(max_val * 1e9)
        elif fit_range_type == 'indentation':
            angle=90
            min_val = hertz_params.child('Min Indentation').value() / 1e9
            max_val = hertz_params.child('Max Indentation').value() / 1e9
            if max_val  == 0.0:
                max_val = np.max(self.indentation - self.hertz_d0)
                hertz_params.child('Max Indentation').setValue(max_val * 1e9)
        elif fit_range_type == 'force':
            angle=0
            min_val = hertz_params.child('Min Force').value() / 1e9
            max_val = hertz_params.child('Max Force').value() / 1e9
            if max_val  == 0.0:
                max_val = np.max(self.force)
                hertz_params.child('Max Force').setValue(max_val * 1e9)
        if self.min_val_line and self.max_val_line:
            self.p2.removeItem(self.min_val_line)
            self.p2.removeItem(self.max_val_line)
        self.min_val_line = pg.InfiniteLine(pos=min_val, angle=angle, pen='y', movable=False, label='Min', labelOpts={'color':'y', 'position':0.7})
        self.max_val_line = pg.InfiniteLine(pos=max_val, angle=angle, pen='y', movable=False, label='Max', labelOpts={'color':'y', 'position':0.7})
        self.p2.addItem(self.min_val_line, ignoreBounds=True)
        self.p2.addItem(self.max_val_line, ignoreBounds=True)

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
        
        analysis_params.child('Correct Tilt').sigValueChanged.connect(self.updatePlots)
        analysis_params.child('Min Tilt Offset').sigValueChanged.connect(self.updatePlots)
        analysis_params.child('Max Tilt Offset').sigValueChanged.connect(self.updatePlots)
        
        hertz_params = self.params.child('Hertz Fit Params')
        hertz_params.child('Fit Range Type').sigValueChanged.connect(self.update_fit_range)
        hertz_params.child('Max Indentation').sigValueChanged.connect(self.update_fit_range)
        hertz_params.child('Min Indentation').sigValueChanged.connect(self.update_fit_range)
        hertz_params.child('Max Force').sigValueChanged.connect(self.update_fit_range)
        hertz_params.child('Min Force').sigValueChanged.connect(self.update_fit_range)