import PyQt5
from pyqtgraph.Qt import QtGui, QtWidgets, QtCore
import pyqtgraph as pg
from pyqtgraph.parametertree import Parameter, ParameterTree
import numpy as np

import pyafmgui.const as cts
from pyafmgui.compute import compute
from pyafmgui.widgets.get_params import get_params

from pyafmrheo.utils.force_curves import get_poc_RoV_method, correct_viscous_drag, correct_tilt

class TingFitWidget(QtGui.QWidget):
    def __init__(self, session, parent=None):
        super(TingFitWidget, self).__init__(parent)
        self.session = session
        self.current_file = None
        self.tilt_roi = None
        self.file_dict = {}
        self.session.ting_fit_widget = self
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

        self.params = Parameter.create(name='params', children=cts.tingfit_params)

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
        self.session.ting_fit_widget = None
    
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
        params = get_params(self.params, "TingFit")
        compute(self.session, params,  self.filedict, "TingFit")
        QtWidgets.QApplication.processEvents()
        self.updatePlots()

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
            if self.current_file.filemetadata['file_type'] == "jpk-force-map":
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
        self.ting_d0 = 0
        self.fit_data = None
        self.residual = None
        self.ting_tc = None

        current_file_id = self.current_file.filemetadata['Entry_filename']
        current_curve_indx = self.session.current_curve_index

        analysis_params = self.params.child('Analysis Params')
        ting_params = self.params.child('Ting Fit Params')

        height_channel = analysis_params.child('Height Channel').value()
        deflection_sens = analysis_params.child('Deflection Sensitivity').value() / 1e9
        spring_k = analysis_params.child('Spring Constant').value()
        
        poc_win = ting_params.child('PoC Window').value() / 1e9
        vdragcorr = ting_params.child('Correct Viscous Drag').value()
        polyordr = ting_params.child('Poly. Order').value()
        rampspeed = ting_params.child('Ramp Speed').value() / 1e6
        contact_offset = ting_params.child('Contact Offset').value() / 1e6
        t0_scaling = ting_params.child('t0').value()
        pts_downsample = ting_params.child('Downsample Pts.').value()
        correct_tilt_flag = analysis_params.child('Correct Tilt').value()
        tilt_min_offset = analysis_params.child('Min Tilt Offset').value() / 1e9
        tilt_max_offset = analysis_params.child('Max Tilt Offset').value() / 1e9

        force_curve = self.current_file.getcurve(current_curve_indx)
        force_curve.preprocess_force_curve(deflection_sens, height_channel)

        if self.session.current_file.filemetadata['file_type'] in cts.jpk_file_extensions:
            force_curve.shift_height()

        file_ting_result = self.session.ting_fit_results.get(current_file_id, None)

        if file_ting_result:
            for curve_indx, result in file_ting_result:
                if result is None:
                    continue
                else:
                    curve_ting_result, curve_hertz_result = result
                if curve_indx == self.session.current_curve_index:
                    self.ting_E = curve_ting_result.E0
                    self.ting_exp = curve_ting_result.betaE
                    self.ting_tc = curve_ting_result.tc
                    self.ting_redchi = curve_ting_result.redchi
                    self.ting_f0 = curve_ting_result.F0
                    self.hertz_E = curve_hertz_result.E0
                    self.hertz_d0 = curve_hertz_result.delta0
                    self.hertz_redchi = curve_hertz_result.redchi
                    self.fit_data = curve_ting_result

        ext_data = force_curve.extend_segments[0][1]
        ret_data = force_curve.retract_segments[-1][1]

        self.p3.plot(ext_data.zheight, ext_data.vdeflection)
        self.p3.plot(ret_data.zheight, ret_data.vdeflection)

        rov_PoC = get_poc_RoV_method(ext_data.zheight, ext_data.vdeflection, poc_win)
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

        vertical_line = pg.InfiniteLine(pos=0, angle=90, pen='y', movable=False, label='RoV d0', labelOpts={'color':'y', 'position':0.5})
        self.p1.addItem(vertical_line, ignoreBounds=True)
        if self.hertz_d0 != 0:
            d0_vertical_line = pg.InfiniteLine(pos=self.hertz_d0, angle=90, pen='g', movable=False, label='Hertz d0', labelOpts={'color':'g', 'position':0.7})
            self.p1.addItem(d0_vertical_line, ignoreBounds=True)
            poc[0] += self.hertz_d0
        force_curve.get_force_vs_indentation(poc, spring_k)
        if vdragcorr:
            ext_data.force, ret_data.force = correct_viscous_drag(
                ext_data.indentation, ext_data.force, ret_data.indentation, ret_data.force, poly_order=polyordr, speed=rampspeed)
        self.p1.plot(ext_data.indentation, ext_data.force)
        self.p1.plot(ret_data.indentation, ret_data.force)
        
        idx_tc = (np.abs(ext_data.indentation - 0)).argmin()
        t0 = ext_data.time[-1]
        indentation = np.r_[ext_data.indentation, ret_data.indentation]
        time = np.r_[ext_data.time, ret_data.time + t0]
        force = np.r_[ext_data.force, ret_data.force]
        fit_mask = indentation > (-1 * contact_offset)
        tc = time[idx_tc]
        ind_fit = indentation[fit_mask]
        force_fit = force[fit_mask]
        force_fit = force_fit - force_fit[0]
        time_fit = time[fit_mask]
        tc_fit = tc-time_fit[0]
        time_fit = time_fit - time_fit[0] - tc_fit
        
        downfactor= len(time_fit) // pts_downsample
        idxDown = list(range(0, len(time_fit), downfactor))

        self.p2.plot(time_fit[idxDown], force_fit[idxDown])

        self.update_tilt_range()

        if self.fit_data is not None:
            self.p2.plot(
                time_fit[idxDown],
                self.fit_data.eval(
                    time_fit[idxDown], force_fit[idxDown], ind_fit[idxDown], t0=t0_scaling
                ), pen ='g', name='Fit')
            vertical_line_tinc_tc = pg.InfiniteLine(
                pos=self.ting_tc, angle=90, pen='y', movable=False, label='Ting tc', labelOpts={'color':'y', 'position':0.5}
            )
            self.p2.addItem(vertical_line_tinc_tc, ignoreBounds=True)
            style = pg.PlotDataItem(pen=None)
            self.p2legend.addItem(style, f'Hertz E: {self.hertz_E:.2f} Pa')
            self.p2legend.addItem(style, f'Hertz d0: {self.hertz_d0 + poc[0]:.3E} m')
            self.p2legend.addItem(style, f'Hertz Red. Chi: {self.hertz_redchi:.3E}')
            self.p2legend.addItem(style, f'Ting E: {self.ting_E:.2f} Pa')
            self.p2legend.addItem(style, f'Ting Fluid. Exp.: {self.ting_exp:.3f}')
            self.p2legend.addItem(style, f'Ting tc: {self.ting_tc+tc_fit:.2f} s')
            self.p2legend.addItem(style, f'Ting Red. Chi: {self.ting_redchi:.3E}')
            res = self.p4.plot(
                time_fit[idxDown],
                self.fit_data.get_residuals(
                    time_fit[idxDown], force_fit[idxDown], ind_fit[idxDown], t0=t0_scaling
                ), pen=None, symbol='o')
            res.setSymbolSize(5)
        
        self.p1.setLabel('left', 'Force', 'N')
        self.p1.setLabel('bottom', 'Indentation', 'm')
        self.p1.setTitle("Force-Indentation")
        self.p2.setLabel('left', 'Force', 'N')
        self.p2.setLabel('bottom', 'Time', 's')
        self.p2.setTitle("Force-Time Ting Fit")
        self.p3.setLabel('left', 'Deflection', 'm')
        self.p3.setLabel('bottom', 'zHeight', 'm')
        self.p3.addLegend()
        self.p3.setTitle("Deflection-zHeight")
        self.p4.setLabel('left', 'Residuals')
        self.p4.setLabel('bottom', 'Time', 's')
        self.p4.setTitle("Ting Fit Residuals")
        
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