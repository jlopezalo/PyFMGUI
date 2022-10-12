class Session:
    def __init__(self):
        self.loaded_files_paths = []
        self.loaded_files = {}
        self.hertz_fit_results = {}
        self.thermal_tune_results = {}
        self.ting_fit_results = {}
        self.piezo_char_results = {}
        self.vdrag_results = {}
        self.microrheo_results = {}
        self.current_file=None
        self.map_coords = None
        self.current_curve_index=None
        self.global_k = None
        self.global_involts = None
        self.data_viewer_widget = None
        self.thermal_tune_widget = None
        self.hertz_fit_widget = None
        self.ting_fit_widget = None
        self.piezo_char_widget = None
        self.vdrag_widget = None
        self.microrheo_widget = None
        self.macro_widget = None
        self.logger_wiget = None
        self.export_dialog = None
        self.pbar_widget = None
        self.piezo_char_data = None
        self.piezo_char_file_path = None
        self.sader_username = ""
        self.sader_password = ""
        self.prepared_results = {
        'hertz_results': None,
        'ting_results': None, 
        'piezochar_results': None,
        'vdrag_results': None,
        'microrheo_results': None
        }
    
    def remove_results(self):
        self.loaded_files_paths = []
        self.loaded_files = {}
        self.hertz_fit_results = {}
        self.thermal_tune_results = {}
        self.ting_fit_results = {}
        self.piezo_char_results = {}
        self.vdrag_results = {}
        self.microrheo_results = {}
    
    def remove_data_and_results(self):
        self.remove_results()
        self.current_file=None
        self.map_coords = None
        self.current_curve_index=None
        self.global_k = None
        self.global_involts = None
        self.piezo_char_data = None
        self.piezo_char_file_path = None