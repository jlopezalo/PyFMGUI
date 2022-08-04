import pyqtgraph.parametertree.parameterTypes as pTypes
from .canti_list import canti_list

jpk_file_extensions = ('.jpk-force', '.jpk-force-map', '.jpk-qi-data')
nanoscope_file_extensions = ('.spm', '.pfc')
available_geometries = ['paraboloid', 'cone', 'pyramid']

# SADER API params ################################################
SADER_API_version = 'Python API/0.20'
SADER_API_type = 'text/xml'
SADER_API_url = 'https://sadermethod.org/api/1.1/api.php'

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
            {'name': 'Tip Angle', 'type': 'float', 'value': 35, 'units':'°'},
            {'name': 'Tip Radius', 'type': 'float', 'value': 75, 'units':'nm'},
            {'name': 'Tip Area', 'type': 'float', 'value': None},
            {'name': 'Curve Segment', 'type': 'list', 'limits':['extend', 'retract']},
            {'name': 'Correct Tilt', 'type': 'bool', 'value':False}
        ])

        if self.mode == "microrheo":
            self.addChildren([
                {'name': 'Method', 'type': 'list', 'limits':['FFT', 'Sine Fit']},
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
            {'name': 'PoC Window', 'type': 'int', 'value': 350, 'units':'nm'},
            {'name': 'Fit Range Type', 'type': 'list', 'limits': ['full', 'indentation', 'force']},
            {'name': 'Min Indentation', 'type': 'float', 'value': None, 'units':'nm'},
            {'name': 'Max Indentation', 'type': 'float', 'value': None, 'units':'nm'},
            {'name': 'Min Force', 'type': 'float', 'value': None, 'units':'nN'},
            {'name': 'Max Force', 'type': 'float', 'value': None, 'units':'nN'},
            {'name': 'Auto Init E0', 'type': 'bool', 'value':True},
            {'name': 'Init E0', 'type': 'int', 'value': 1000, 'units':'Pa'},
            {'name': 'Init d0', 'type': 'float', 'value': 0, 'units':'nm'},
            {'name': 'Init f0', 'type': 'float', 'value': 0, 'units':'nN'},
            {'name': 'Fit Line to non contact', 'type': 'bool', 'value':False},
            {'name': 'Init Slope', 'type': 'float', 'value': 0}
        ])

        self.range_mode = self.param('Fit Range Type')
        self.range_mode.sigValueChanged.connect(self.range_mode_changed)

        self.fit_line = self.param('Fit Line to non contact')
        self.fit_line.sigValueChanged.connect(self.fit_line_changed)

        self.range_mode_changed()
        self.fit_line_changed()
        
    def range_mode_changed(self):
        if self.range_mode.value() == 'full':
            self.param('Min Indentation').show(False)
            self.param('Max Indentation').show(False)
            self.param('Min Force').show(False)
            self.param('Max Force').show(False)

        elif self.range_mode.value() == 'indentation':
            self.param('Min Indentation').show(True)
            self.param('Max Indentation').show(True)
            self.param('Min Force').show(False)
            self.param('Max Force').show(False)

        elif self.range_mode.value() == 'force':
            self.param('Min Indentation').show(False)
            self.param('Max Indentation').show(False)
            self.param('Min Force').show(True)
            self.param('Max Force').show(True)
    
    def fit_line_changed(self):
        if self.fit_line.value():
            self.param('Init Slope').show(True)
        else:
            self.param('Init Slope').show(False)

class TingFitParams(pTypes.GroupParameter):
    def __init__(self, **opts):
        pTypes.GroupParameter.__init__(self, **opts)
        self.addChildren([
            {'name': 'Poisson Ratio', 'type': 'float', 'value': 0.5},
            {'name': 'PoC Window', 'type': 'int', 'value': 350, 'units':'nm'},
            {'name': 'Correct Viscous Drag', 'type': 'bool', 'value':False},
            {'name': 'Poly. Order', 'type': 'int', 'value':2},
            {'name': 'Ramp Speed', 'type': 'float', 'value':0, 'units': 'um/s'},
            {'name': 'Model Type', 'type': 'list', 'limits': ['analytical', 'numerical']},
            {'name': 'Estimate V0t & V0r', 'type': 'bool', 'value': False},
            {'name': 't0', 'type': 'int', 'value': 1, 'units':'s'},
            {'name': 'Init d0', 'type': 'float', 'value': 0, 'units':'nm'},
            {'name': 'Init Slope', 'type': 'float', 'value': 0},
            {'name': 'Auto Init E0', 'type': 'bool', 'value':True},
            {'name': 'Init E0', 'type': 'int', 'value': 1000, 'units':'Pa'},
            {'name': 'Init tc', 'type': 'float', 'value': 0, 'units':'s'},
            {'name': 'Init f0', 'type': 'float', 'value': 0, 'units':'nN'},
            {'name': 'Viscous Drag', 'type': 'float', 'value': 0, 'units':'pN/nm·s'},
            {'name': 'Init Fluid. Exp.', 'type': 'float', 'value': 0.20},
            {'name': 'Contact Offset', 'type': 'float', 'value': 1, 'units':'um'},
            {'name': 'Smoothing Window', 'type': 'int', 'value': 5, 'units':'points'}

        ])

        self.model_type = self.param('Model Type')
        self.model_type.sigValueChanged.connect(self.model_type_changed)

        self.vdrag_corr = self.param('Correct Viscous Drag')
        self.vdrag_corr.sigValueChanged.connect(self.vdrag_changed)

        self.model_type_changed()
        self.vdrag_changed()
        
    def model_type_changed(self):
        if self.model_type.value() == 'numerical':
            self.param('Smoothing Window').show(True)

        elif self.model_type.value() == 'analytical':
            self.param('Smoothing Window').show(False)
    
    def vdrag_changed(self):
        if self.vdrag_corr.value():
            self.param('Poly. Order').show(True)
            self.param('Ramp Speed').show(True)
        else:
            self.param('Poly. Order').show(False)
            self.param('Ramp Speed').show(False)

class CantileverParams(pTypes.GroupParameter):
    def __init__(self, **opts):
        pTypes.GroupParameter.__init__(self, **opts)
        self.addChildren([
            {'name': 'Canti Id', 'type': 'list', 'limits': list(canti_list.keys())},
            {'name': 'Canti Shape', 'type': 'list', 'limits': ['Rectangular', 'V Shape']},
            {'name': 'Lenght', 'type': 'float', 'value': 0, 'units':'um'},
            {'name': 'Width', 'type': 'float', 'value': 0, 'units':'um'},
            {'name': 'Width Legs', 'type': 'float', 'value': 0, 'units':'um'}
        ])

        self.cani_id = self.param('Canti Id')
        self.cani_id.sigValueChanged.connect(self.canti_id_changed)

        self.canti_id_changed()
        
    def canti_id_changed(self):
        canti_data = canti_list.get(self.cani_id.value())
        self.param('Canti Shape').setValue(canti_data['cantType'])
        self.param('Lenght').setValue(canti_data['CantileverLength'])
        self.param('Width').setValue(canti_data['CantileverWidth'])
        self.param('Width Legs').setValue(canti_data['CantileverWidthLegs'])


general_params = {'name': 'General Options', 'type': 'group', 'children': [
        {'name': 'Compute All Curves', 'type': 'bool', 'value': False},
        {'name': 'Compute All Files', 'type': 'bool', 'value': False}
    ]}

# plot_params = {'name': 'Display Options', 'type': 'group', 'children': [
#         {'name': 'Curve X axis', 'type': 'list', 'limits': ['zheight', 'time']},
#         {'name': 'Curve Y axis', 'type': 'list', 'limits': ['vdeflection', 'zheight']},
#         {'name': 'Map Data', 'type': 'list', 'limits': ['piezo height', 'Data Missing Check', 'Slope Check', 'Baseline Noise Check']}
#     ]}

plot_params = {'name': 'Display Options', 'type': 'group', 'children': [
        {'name': 'Curve X axis', 'type': 'list', 'limits': ['zheight', 'time']},
        {'name': 'Curve Y axis', 'type': 'list', 'limits': ['vdeflection', 'zheight']}
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

sader_method_params = {'name': 'Calibration Params', 'type': 'group', 'children': [
        {'name': 'Model', 'type': 'str', 'value': 'SHO', 'readonly':True},
        {'name': 'Cantilever Code', 'type': 'list', 'limits': []}
    ]}

data_viewer_params = [plot_params]

hertzfit_params = [general_params, AnalysisParams(mode='hertzfit', name='Analysis Params'), HertzFitParams(name='Hertz Fit Params')]

thermaltune_params = [ambient_params, CantileverParams(name='Cantilever Params'), sader_method_params]

tingfit_params = [general_params, AnalysisParams(mode='tingfit', name='Analysis Params'), TingFitParams(name='Ting Fit Params')]

piezochar_params = [general_params, rheo_params]

vdrag_params = [general_params, rheo_params]

microrheo_params = [general_params, AnalysisParams(mode='microrheo', name='Analysis Params'), HertzFitParams(name='Hertz Fit Params')]