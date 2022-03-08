from math import fabs
from re import T
from unicodedata import name
import PyQt6
from matplotlib.style import available
import pyqtgraph.parametertree.parameterTypes as pTypes

jpk_file_extensions = ('.jpk-force', '.jpk-force-map', '.jpk-qi-data')
available_geometries = ['paraboloid', 'cone', 'pyramid']

# Default parameters ##############################################

class AnalysisParams(pTypes.GroupParameter):
    def __init__(self, mode, **opts):
        pTypes.GroupParameter.__init__(self, **opts)
        self.mode = mode
        self.addChildren([
            {'name': 'Height Channel', 'type': 'str', 'value': 'measuredHeight', 'readonly':True},
            {'name': 'Spring Constant', 'type': 'float', 'value': None, 'units':'N/m'},
            {'name': 'Deflection Sensitivity', 'type': 'float', 'value': None, 'units':'nm/V'},
            {'name': 'Contact Model', 'type': 'list', 'limits': available_geometries},
            {'name': 'Tip Angle', 'type': 'float', 'value': None, 'units':'°'},
            {'name': 'Tip Radius', 'type': 'float', 'value': None, 'units':'nm'},
            {'name': 'Tip Area', 'type': 'float', 'value': None},
            {'name': 'Curve Segment', 'type': 'list', 'limits':['extend', 'retract']}
        ])

        if self.mode == "microrheo":
            self.addChildren([
                {'name': 'Max Frequency', 'type': 'int', 'value': None, 'units':'Hz'},
                {'name': 'B Coef', 'type': 'float', 'value': None, 'units':'Ns/m'}
            ])

        self.contact_model = self.param('Contact Model')
        self.contact_model.sigValueChanged.connect(self.contact_model_changed)

        self.contact_model_changed()

    def contact_model_changed(self):
        if self.contact_model.value() == 'paraboloid':
            self.param('Tip Angle').show(False)
            self.param('Tip Radius').show(True)
            self.param('Tip Area').show(False)

        elif self.contact_model.value() in ('cone', 'pyramid'):
            self.param('Tip Angle').show(True)
            self.param('Tip Radius').show(False)
            self.param('Tip Area').show(False)

class HertzFitParams(pTypes.GroupParameter):
    def __init__(self, **opts):
        pTypes.GroupParameter.__init__(self, **opts)
        self.addChildren([
            {'name': 'Poisson Ratio', 'type': 'float', 'value': 0.5},
            {'name': 'PoC Window', 'type': 'int', 'value': 50},
            {'name': 'Fit Range Type', 'type': 'list', 'limits': ['indentation', 'force']},
            {'name': 'Min Indentation', 'type': 'float', 'value': 0},
            {'name': 'Max Indentation', 'type': 'float', 'value': 100},
            {'name': 'Min Force', 'type': 'float', 'value': 0},
            {'name': 'Max Force', 'type': 'float', 'value': 100},
            {'name': 'Init E0', 'type': 'int', 'value': 1000, 'units':'Pa'},
            {'name': 'Init d0', 'type': 'float', 'value': 0, 'units':'nm'},
            {'name': 'Init f0', 'type': 'float', 'value': 0, 'units':'nN'},
            {'name': 'Init Slope', 'type': 'float', 'value': 0}
        ])

        self.range_mode = self.param('Fit Range Type')
        self.range_mode.sigValueChanged.connect(self.range_mode_changed)

        self.range_mode_changed()
        
    def range_mode_changed(self):
        if self.range_mode.value() == 'indentation':
            self.param('Min Indentation').show(True)
            self.param('Max Indentation').show(True)
            self.param('Min Force').show(False)
            self.param('Max Force').show(False)

        elif self.range_mode.value() == 'force':
            self.param('Min Indentation').show(False)
            self.param('Max Indentation').show(False)
            self.param('Min Force').show(True)
            self.param('Max Force').show(True)

class TingFitParams(pTypes.GroupParameter):
    def __init__(self, **opts):
        pTypes.GroupParameter.__init__(self, **opts)
        self.addChildren([
            {'name': 'Poisson Ratio', 'type': 'float', 'value': 0.5},
            {'name': 'PoC Window', 'type': 'int', 'value': 50},
            {'name': 'Model Type', 'type': 'list', 'limits': ['numeric', 'analytical']},
            {'name': 'Init E0', 'type': 'int', 'value': 1000, 'units':'Pa'},
            {'name': 'Init d0', 'type': 'float', 'value': 0, 'units':'nm'},
            {'name': 'Init f0', 'type': 'float', 'value': 0, 'units':'nN'},
            {'name': 'Init Slope', 'type': 'float', 'value': 0},
            {'name': 'dTp', 'type': 'float', 'value': 1, 'units':'s'},
            {'name': 'Init Fluid. Exp.', 'type': 'float', 'value': 0.20},
            {'name': 'Contact Offset', 'type': 'float', 'value': 1, 'units':'um'},
            {'name': 'Smoothing Window', 'type': 'int', 'value': 5, 'units':'points'},
            {'name': 'Relaxation Function', 'type': 'str', 'value': 'Simple Power Law', 'readonly':True},

        ])

        self.model_type = self.param('Model Type')
        self.model_type.sigValueChanged.connect(self.model_type_changed)

        self.model_type_changed()
        
    def model_type_changed(self):
        if self.model_type.value() == 'numeric':
            self.param('Contact Offset').show(True)
            self.param('Relaxation Function').show(True)
            self.param('Smoothing Window').show(True)

        elif self.model_type.value() == 'analytical':
            self.param('Contact Offset').show(False)
            self.param('Relaxation Function').show(False)
            self.param('Smoothing Window').show(False)


general_params = {'name': 'General Options', 'type': 'group', 'children': [
        {'name': 'Compute All Curves', 'type': 'bool', 'value': False},
        {'name': 'Compute All Files', 'type': 'bool', 'value': False}
    ]}

plot_params = {'name': 'Display Options', 'type': 'group', 'children': [
        {'name': 'Curve X axis', 'type': 'list', 'limits': ['height', 'time']},
        {'name': 'Curve Y axis', 'type': 'list', 'limits': ['deflection', 'height']},
        {'name': 'Map Data', 'type': 'list', 'limits': ['piezo height', 'Data Missing Check', 'Slope Check', 'Baseline Noise Check']}
    ]}

rheo_params = {'name': 'Analysis Params', 'type': 'group', 'children': [
        {'name': 'Height Channel', 'type': 'str', 'value': 'measuredHeight', 'readonly':True},
        {'name': 'Spring Constant', 'type': 'float', 'value': None, 'units':'N/m'},
        {'name': 'Deflection Sensitivity', 'type': 'float', 'value': None, 'units':'nm/V'},
        {'name': 'Max Frequency', 'type': 'int', 'value': None, 'units':'Hz'}
    ]}

ambient_params = {'name': 'Ambient Params', 'type': 'group', 'children': [
        {'name': 'Temperature', 'type': 'float', 'value': 25, 'units':'°C'},
        {'name': 'Rel. Humidity', 'type': 'float', 'value': 68, 'units':'%'}
    ]}

cantilever_params = {'name': 'Cantilever Params', 'type': 'group', 'children': [
        {'name': 'Lenght', 'type': 'float', 'value': None, 'units':'um'},
        {'name': 'Width', 'type': 'float', 'value': None, 'units':'um'},
        {'name': 'Width Legs', 'type': 'float', 'value': None, 'units':'um'},
        {'name': 'Nominal K', 'type': 'float', 'value': None, 'units':'N/m'}
    ]}

sader_method_params = {'name': 'Calibration Params', 'type': 'group', 'children': [
        {'name': 'Min Frequency', 'type': 'float', 'value': None, 'units':'kHz'},
        {'name': 'Max Frequency', 'type': 'float', 'value': None, 'units':'kHz'},
        {'name': 'Model', 'type': 'str', 'value': 'SHO', 'readonly':True}
    ]}

data_viewer_params = [plot_params]

hertzfit_params = [general_params, AnalysisParams(mode='hertzfit', name='Analysis Params'), HertzFitParams(name='Hertz Fit Params')]

thermaltune_params = [ambient_params, cantilever_params, sader_method_params]

tingfit_params = [general_params, AnalysisParams(mode='tingfit', name='Analysis Params'), TingFitParams(name='Ting Fit Params')]

piezochar_params = [general_params, rheo_params]

vdrag_params = [general_params, rheo_params]

microrheo_params = [general_params, AnalysisParams(mode='microrheo', name='Analysis Params'), HertzFitParams(name='Hertz Fit Params')]