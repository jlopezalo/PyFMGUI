import os
import numpy as np
import PyQt6
from pyqtgraph.Qt import QtGui, QtWidgets, QtCore
import pyqtgraph as pg
from pyqtgraph.parametertree import Parameter, ParameterTree

import pyafmgui.const as cts
from pyafmgui.helpers.thermal_utils import *

class ThermalTuneWidget(QtGui.QWidget):
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
        self.init_gui()

    def init_gui(self):
        main_layout = QtWidgets.QHBoxLayout()
        self.setLayout(main_layout)

        params_layout = QtWidgets.QVBoxLayout()

        file_select_layout = QtWidgets.QGridLayout()

        air_thermal_label = QtWidgets.QLabel("Air Thermal File")
        air_thermal_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        air_thermal_label.setMaximumWidth(150)
        self.air_thermal_text = QtWidgets.QTextEdit()
        self.air_thermal_text.setMaximumHeight(40)
        air_thermal_browse_bttn = QtWidgets.QPushButton()
        air_thermal_browse_bttn.setText("Browse")
        air_thermal_browse_bttn.clicked.connect(self.load_air_data)

        lq_thermal_label = QtWidgets.QLabel("Liquid Thermal File")
        lq_thermal_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        lq_thermal_label.setMaximumWidth(150)
        self.lq_thermal_text = QtWidgets.QTextEdit()
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

        p = Parameter.create(name='params', children=cts.thermaltune_params)

        self.paramTree = ParameterTree()
        self.paramTree.setParameters(p, showTop=False)

        self.pushButton = QtWidgets.QPushButton("computeButton")
        self.pushButton.setText("Compute")
        self.pushButton.clicked.connect(self.do_thermalfit)

        params_layout.addLayout(file_select_layout)
        params_layout.addWidget(self.paramTree)
        params_layout.addWidget(self.pushButton)

        ## Add 3 plots into the first row (automatic position)
        self.l = pg.GraphicsLayoutWidget()
        self.p1 = pg.PlotItem()
        self.air_roi = pg.LinearRegionItem(brush=None, pen='r')
        self.air_roi.setZValue(10)
        self.air_roi.sigRegionChangeFinished.connect(self.airRegionChanged)
        self.lq_roi = pg.LinearRegionItem(brush=None, pen='b')
        self.lq_roi.setZValue(10)
        self.lq_roi.sigRegionChangeFinished.connect(self.lqRegionChanged)

        ## Put vertical label on left side
        main_layout.addLayout(params_layout, 1)
        main_layout.addWidget(self.l, 3)
    
    def closeEvent(self, evnt):
        self.session.thermal_tune_widget = None
    
    def load_data(self):
        fname, _ = QtWidgets.QFileDialog.getOpenFileName(
        	self, 'Open file', './', "Thermal files (*.tnd)"
        )
        return loadThermal(fname), os.path.basename(fname)  if fname != "" else (None, None)

    def load_air_data(self):
        data, fname = self.load_data()
        if data is None or fname is None:
            return
        self.inair_thermal_ampl, self.inair_thermal_freq, self.inair_params = data
        self.air_thermal_text.setText(fname)
        self.update_plot()

    def load_liquid_data(self):
        data, fname = self.load_data()
        if data is None or fname is None:
            return
        self.inliquid_thermal_ampl, self.inliquid_thermal_freq, self.inliquid_params = data
        self.lq_thermal_text.setText(fname)
        self.update_plot()
    
    def update_plot(self):

        self.l.clear()
        self.p1.clear()

        if self.inair_thermal_freq is not None and self.inair_thermal_ampl is not None:
            air = self.p1.plot(self.inair_thermal_freq, self.inair_thermal_ampl, pen='r', name='Air Data')
            self.p1.addItem(self.air_roi, ignoreBounds=True)
            self.air_roi.setClipItem(air)
            resonancef = self.inair_params['resonancef']
            self.air_roi.setRegion([np.log10(resonancef/2), np.log10(resonancef*2)])
        
        if self.inliquid_thermal_freq is not None and self.inliquid_thermal_ampl is not None:
            lq = self.p1.plot(self.inliquid_thermal_freq, self.inliquid_thermal_ampl, pen='b', name='Liquid Data')
            self.p1.addItem(self.lq_roi, ignoreBounds=True)
            self.lq_roi.setClipItem(lq)
            resonancef = self.inliquid_params['resonancef']
            self.lq_roi.setRegion([np.log10(resonancef/2), np.log10(resonancef*2)])
        
        if self.thermal_fit_air is not None:
            self.p1.plot(self.freq_fit_air, self.thermal_fit_air, pen='w', name='Air SHO Fit')

        
        self.p1.setTitle("Amplitude-Frequency")
        self.p1.setLabel('left', 'Amplitude (pm^2/V)')
        self.p1.setLabel('bottom', 'Frequency', 'Hz')
        self.p1.setLogMode(True, True)
        self.p1.addLegend((30, 30))

        self.l.addItem(self.p1)
    
    def airRegionChanged(self):
        print()
    
    def lqRegionChanged(self):
        print(self.lq_roi.getRegion())
    
    def do_thermalfit(self):
        minfreq, maxfreq = self.air_roi.getRegion()
        minfreq = 10 ** minfreq
        maxfreq = 10 ** maxfreq
        mask = np.logical_and(self.inair_thermal_freq >= minfreq, self.inair_thermal_freq <= maxfreq)
        ampl_fit = self.inair_thermal_ampl[mask]
        freq_fit = self.inair_thermal_freq[mask]
        thermal_fit_result = ThermalFit(freq_fit, ampl_fit)
        self.freq_fit_air = freq_fit
        self.thermal_fit_air = thermal_fit_result.best_fit
        self.update_plot()
