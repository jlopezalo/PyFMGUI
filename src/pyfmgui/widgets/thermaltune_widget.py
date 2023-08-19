import os
import numpy as np
import requests
import xml.etree.ElementTree as etree
import PyQt5
from pyqtgraph.Qt import QtGui, QtWidgets, QtCore
import pyqtgraph as pg
from pyqtgraph.parametertree import Parameter, ParameterTree

from pyfmreader import loadfile
from pyfmrheo.models.calibration import Stark_Chi_force_constant
from pyfmrheo.models.sho import SHOModel

import pyfmgui.const as cts

class ThermalTuneWidget(QtWidgets.QWidget):
    def __init__(self, session, parent=None):
        super(ThermalTuneWidget, self).__init__(parent)
        self.session = session
        self.session.thermal_tune_widget = self
        self.inliquid_thermal_ampl = None
        self.inliquid_thermal_freq = None
        self.inliquid_params = None
        self.inair_thermal_ampl = None
        self.inair_thermal_freq = None
        self.inair_params = None
        self.thermal_fit_air = None
        self.thermal_fit_lq = None
        self.k0 = None
        self.GCI_cant_springConst = None
        self.involsValue = None
        self.invOLS_H = None
        self.sader_canti_list = {}
        self.init_gui()

    def init_gui(self):
        main_layout = QtWidgets.QHBoxLayout()
        self.setLayout(main_layout)

        params_layout = QtWidgets.QVBoxLayout()

        file_select_layout = QtWidgets.QGridLayout()

        air_thermal_label = QtWidgets.QLabel("Air Thermal File")
        air_thermal_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        air_thermal_label.setMaximumWidth(150)
        self.air_thermal_text = QtWidgets.QLineEdit()
        self.air_thermal_text.setMaximumHeight(40)
        air_thermal_browse_bttn = QtWidgets.QPushButton()
        air_thermal_browse_bttn.setText("Browse")
        air_thermal_browse_bttn.clicked.connect(self.load_air_data)

        lq_thermal_label = QtWidgets.QLabel("Liquid Thermal File")
        lq_thermal_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        lq_thermal_label.setMaximumWidth(150)
        self.lq_thermal_text = QtWidgets.QLineEdit()
        self.lq_thermal_text.setMaximumHeight(40)
        lq_thermal_browse_bttn = QtWidgets.QPushButton()
        lq_thermal_browse_bttn.setText("Browse")
        lq_thermal_browse_bttn.clicked.connect(self.load_liquid_data)

        file_select_layout.addWidget(air_thermal_label, 0, 0, 1, 1)
        file_select_layout.addWidget(self.air_thermal_text, 0, 1, 1, 2)
        file_select_layout.addWidget(air_thermal_browse_bttn, 1, 2, 1, 1)
        file_select_layout.addWidget(lq_thermal_label, 2, 0, 1, 1)
        file_select_layout.addWidget(self.lq_thermal_text, 2, 1, 1, 2)
        file_select_layout.addWidget(lq_thermal_browse_bttn, 3, 2, 1, 1)

        login_layout = QtWidgets.QGridLayout()
        user_name_label = QtWidgets.QLabel("SADER Username")
        user_name_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        user_name_label.setMaximumWidth(150)
        self.user_name_text = QtWidgets.QLineEdit()
        self.user_name_text.setMaximumHeight(40)
        user_pwd_label = QtWidgets.QLabel("SADER Password")
        user_pwd_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        user_pwd_label.setMaximumWidth(150)
        self.user_pwd_text = QtWidgets.QLineEdit()
        self.user_pwd_text.setMaximumHeight(40)
        self.user_pwd_text.setEchoMode(QtWidgets.QLineEdit.Password)
        login_bttn = QtWidgets.QPushButton()
        login_bttn.setText("Login")
        login_bttn.clicked.connect(self.sader_login)

        login_layout.addWidget(user_name_label, 0, 0, 1, 1)
        login_layout.addWidget(self.user_name_text, 0, 1, 1, 2)
        login_layout.addWidget(user_pwd_label, 1, 0, 1, 1)
        login_layout.addWidget(self.user_pwd_text, 1, 1, 1, 2)
        login_layout.addWidget(login_bttn, 2, 2, 1, 1)

        self.params = Parameter.create(name='params', children=cts.thermaltune_params)

        self.paramTree = ParameterTree()
        self.paramTree.setParameters(self.params, showTop=False)

        self.pushButton = QtWidgets.QPushButton("computeButton")
        self.pushButton.setText("Compute")
        self.pushButton.clicked.connect(self.do_thermalfit)

        self.l2 = pg.GraphicsLayoutWidget()

        params_layout.addLayout(file_select_layout, 2)
        params_layout.addLayout(login_layout, 2)
        params_layout.addWidget(self.paramTree, 2)
        params_layout.addWidget(self.pushButton, 1)
        params_layout.addWidget(self.l2, 2)

        ## Add 3 plots into the first row (automatic position)
        self.l = pg.GraphicsLayoutWidget()
        self.p1 = pg.PlotItem()
        self.p1legend = self.p1.addLegend()
        self.air_roi = pg.LinearRegionItem(brush=(50,50,200,0), pen='w')
        self.air_roi.setZValue(10)
        self.lq_roi = pg.LinearRegionItem(brush=(50,50,200,0), pen='y')
        self.lq_roi.setZValue(10)

        ## Put vertical label on left side
        main_layout.addLayout(params_layout, 1)
        main_layout.addWidget(self.l, 3)
    
    def closeEvent(self, evnt):
        self.session.thermal_tune_widget = None
    
    def load_data(self):
        fname, _ = QtWidgets.QFileDialog.getOpenFileName(
        	self, 'Open file', './', "Thermal files (*.tnd)"
        )
        return loadfile(fname), os.path.basename(fname) if fname != "" else (None, None)

    def load_air_data(self):
        data, fname = self.load_data()
        if data is None or fname is None:
            return
        self.inair_thermal_ampl, _, self.inair_thermal_freq, _, self.inair_params = data
        self.air_thermal_text.setText(fname)
        resonancef = self.inair_params['parameter.f']
        self.air_roi.setRegion([np.log10(resonancef/2), np.log10(resonancef*2)])
        self.update_plot()

    def load_liquid_data(self):
        data, fname = self.load_data()
        if data is None or fname is None:
            return
        self.inliquid_thermal_ampl, _, self.inliquid_thermal_freq, _, self.inliquid_params = data
        self.lq_thermal_text.setText(fname)
        resonancef = self.inliquid_params['parameter.f']
        self.lq_roi.setRegion([np.log10(resonancef/2), np.log10(resonancef*2)])
        self.update_plot()
    
    def update_plot(self):

        self.l.clear()
        self.p1.clear()
        self.p1legend.clear()

        if self.inair_thermal_freq is not None and self.inair_thermal_ampl is not None:
            air = self.p1.plot(self.inair_thermal_freq, self.inair_thermal_ampl, pen='w', name='Air Data')
            self.p1.addItem(self.air_roi, ignoreBounds=True)
            self.air_roi.setClipItem(air)
        
        if self.inliquid_thermal_freq is not None and self.inliquid_thermal_ampl is not None:
            lq = self.p1.plot(self.inliquid_thermal_freq, self.inliquid_thermal_ampl, pen='y', name='Liquid Data')
            self.p1.addItem(self.lq_roi, ignoreBounds=True)
            self.lq_roi.setClipItem(lq)
        
        if self.thermal_fit_air is not None:
            self.p1.plot(self.freq_fit_air, self.thermal_fit_air, pen={'color':'c', 'width': 3}, name='Air SHO Fit')
            style = pg.PlotDataItem(pen=None)
            self.p1legend.addItem(style, f'K Air: {self.k0_air:.3f} N/m')
            self.p1legend.addItem(style, f'K Air GCI: {self.GCI_cant_springConst_air:.3f} N/m')
            self.p1legend.addItem(style, f'InVOLS Air: { self.involsValue_air * 1e9:.3f} nm/V')
            self.p1legend.addItem(style, f'InVOLS H Air: {self.invOLS_H_air * 1e9:.3f} nm/V')
        
        if self.thermal_fit_lq is not None:
            self.p1.plot(self.freq_fit_lq, self.thermal_fit_lq, pen={'color':'g', 'width': 3}, name='Liquid SHO Fit')
            style = pg.PlotDataItem(pen=None)
            self.p1legend.addItem(style, f'K Liquid: {self.k0_lq:.3f} N/m')
            self.p1legend.addItem(style, f'K Liquid GCI: {self.GCI_cant_springConst_lq:.3f} N/m')
            self.p1legend.addItem(style, f'InVOLS Liquid: { self.involsValue_lq * 1e9:.3f} nm/V')
            self.p1legend.addItem(style, f'InVOLS H Liquid: {self.invOLS_H_lq * 1e9:.3f} nm/V')

        self.p1.setTitle("Amplitude-Frequency")
        self.p1.setLabel('left', 'Amplitude (pm^2/V)')
        self.p1.setLabel('bottom', 'Frequency', 'Hz')
        self.p1.setLogMode(True, True)
        self.p1.addLegend()

        self.l.addItem(self.p1)
    
    def get_params(self):
        amb_params = self.params.child('Ambient Params')
        self.Tc = amb_params.child('Temperature').value()
        self.RH = amb_params.child('Rel. Humidity').value()
        canti_params = self.params.child('Cantilever Params')
        self.cantType = canti_params.child('Canti Shape').value()
        self.cantiWidth = canti_params.child('Width').value() / 1e6
        self.cantiLen = canti_params.child('Lenght').value() / 1e6
        self.cantiWidthLegs = canti_params.child('Width Legs').value() / 1e6
        cal_params = self.params.child('Calibration Params')
        self.selectedCantId = cal_params.child('Cantilever Code').value()
        self.selectedCantCode = self.sader_canti_list.get(self.selectedCantId, "")
    
    def SaderGCI_GetLeverList(self):
        payload = '''<?xml version="1.0" encoding="UTF-8" ?>
        <saderrequest>
        <username>'''+self.session.sader_username+'''</username>
        <password>'''+self.session.sader_password+'''</password>
        <operation>LIST</operation>
        </saderrequest>'''
        headers = {'user-agent': cts.SADER_API_version, 'Content-type': cts.SADER_API_type}
        r = requests.post(cts.SADER_API_url, data=payload, headers=headers)
        doc = etree.fromstring(r.content)
        
        cantilever_ids = doc.findall('./cantilevers/cantilever/id')
        cantilever_labels = doc.findall('./cantilevers/cantilever/label')

        canti_ids = {}

        for a in range(len(cantilever_ids)):
            canti_lbl = cantilever_labels[a].text
            canti_id  = cantilever_ids[a].text.replace('data_','')
            canti_ids[canti_lbl] = canti_id
        
        return canti_ids
    
    def open_msg_box(self, message):
        dlg = QtWidgets.QMessageBox(self)
        dlg.setWindowTitle("Login Status")
        dlg.setText(message)
        dlg.exec()
    
    def sader_login(self):
        self.session.sader_username = self.user_name_text.text()
        self.session.sader_password = self.user_pwd_text.text()
        try:
            self.sader_canti_list = self.SaderGCI_GetLeverList()
            if self.sader_canti_list == {}:
                self.open_msg_box("Could not Login!")
                return
            self.params.child('Calibration Params').child('Cantilever Code').setLimits(list(self.sader_canti_list.keys()))
            self.open_msg_box("Login was successful!")
        except requests.exceptions.RequestException:
            self.open_msg_box("Could not Login!")
    
    def do_thermalfit(self):
        # Change to the routines present in PyFMRheo
        # Air
        self.get_params()
        if self.inair_thermal_ampl is not None and self.inair_thermal_freq is not None:
            minfreq, maxfreq = self.air_roi.getRegion()
            minfreq = 10 ** minfreq
            maxfreq = 10 ** maxfreq
            mask = np.logical_and(self.inair_thermal_freq >= minfreq, self.inair_thermal_freq <= maxfreq)
            ampl_fit = self.inair_thermal_ampl[mask]
            freq_fit = self.inair_thermal_freq[mask]
            sho_model_air = SHOModel()
            sho_model_air.fit(freq_fit, ampl_fit)
            self.freq_fit_air = freq_fit
            self.thermal_fit_air = sho_model_air.eval(self.freq_fit_air)
            A1_air = sho_model_air.A
            fR1_air = sho_model_air.fR
            Q1_air = sho_model_air.Q
            self.k0_air, self.GCI_cant_springConst_air, self.involsValue_air, self.invOLS_H_air =\
                Stark_Chi_force_constant(
                    self.cantiWidth, self.cantiLen, self.cantiWidthLegs,
                    A1_air, fR1_air, Q1_air, self.Tc, self.RH, 'air',
                    self.cantType, username = self.session.sader_username,
                    password = self.session.sader_password, selectedCantCode = self.selectedCantCode
                )
        # Liquid
        if self.inliquid_thermal_ampl is not None and self.inliquid_thermal_freq is not None:
            minfreq, maxfreq = self.lq_roi.getRegion()
            minfreq = 10 ** minfreq
            maxfreq = 10 ** maxfreq
            mask = np.logical_and(self.inliquid_thermal_freq >= minfreq, self.inliquid_thermal_freq <= maxfreq)
            ampl_fit = self.inliquid_thermal_ampl[mask]
            freq_fit = self.inliquid_thermal_freq[mask]
            sho_model_lq = SHOModel()
            sho_model_lq.fit(freq_fit, ampl_fit)
            self.freq_fit_lq = freq_fit
            self.thermal_fit_lq = sho_model_lq.eval(self.freq_fit_lq)
            A1_lq = sho_model_lq.A
            fR1_lq = sho_model_lq.fR
            Q1_lq = sho_model_lq.Q
            self.k0_lq, self.GCI_cant_springConst_lq, self.involsValue_lq, self.invOLS_H_lq =\
                Stark_Chi_force_constant(
                    self.cantiWidth, self.cantiLen, self.cantiWidthLegs,
                    A1_lq, fR1_lq, Q1_lq, self.Tc, self.RH, 'water', 
                    self.cantType, username = self.session.sader_username,
                    password = self.session.sader_password, selectedCantCode = self.selectedCantCode
                )
        self.update_plot()
