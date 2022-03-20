import os
import pandas as pd


class Session:
    def __init__(self):
        self.loaded_files = {}
        self.hert_fit_results = {}
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
        self.piezo_char_data = None
        self.piezo_char_file_path = None
    
    def remove_data_and_results(self):
        self.loaded_files = {}
        self.hert_fit_results = {}
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
        self.piezo_char_data = None
        self.piezo_char_file_path = None
    
    def export_results(self, dirname, file_prefix):
        results = {
            'hertz_results': self.hert_fit_results,
            'ting_results': self.ting_fit_results,
            'piezochar_results': self.piezo_char_results,
            'vdrag_results': self.vdrag_results,
            'microrheo_results': self.microrheo_results
        }

        for result_type, result in results.items():
            if result != {}:
                outputdf = pd.DataFrame()
                for file_id, file_result in result.items():
                    file_metadata = self.loaded_files[file_id].file_metadata
                    for curve_result in file_result:
                        if result_type == 'hertz_results':
                            row_dict = {}
                            curve_indx = curve_result[0]
                            hertz_result = curve_result[1]
                            row_dict.update({'file_id': file_id, 'curve_indx':curve_indx})
                            row_dict.update({'hertz_' + k:v for (k,v) in hertz_result.best_values.items()})
                            row_dict.update({'hertz_redchi': hertz_result.redchi})
                            outputdf = outputdf.append(row_dict, ignore_index=True)
                        elif result_type == 'ting_results':
                            row_dict = {}
                            curve_indx = curve_result[0]
                            hertz_result = curve_result[1]
                            ting_result = curve_result[2]
                            row_dict.update({'file_id': file_id, 'curve_indx':curve_indx})
                            row_dict.update({'hertz_' + k:v for (k,v) in hertz_result.best_values.items()})
                            row_dict.update({'hertz_redchi': hertz_result.redchi})
                            row_dict.update({'ting_' + k:v for (k,v) in ting_result.best_values.items()})
                            row_dict.update({'ting_redchi': ting_result.redchi})
                            outputdf = outputdf.append(row_dict, ignore_index=True)
                        elif result_type == 'piezochar_results':
                            row_df = pd.DataFrame(columns=['file_id', 'curve_indx', 'frequency', 'fi_degrees', 'amp_quot'])
                            curve_indx = curve_result[0]
                            piezochar_result = curve_result[1]
                            row_df['frequency'] = piezochar_result[0]
                            row_df['fi_degrees'] = piezochar_result[1]
                            row_df['amp_quot'] = piezochar_result[2]
                            row_df['file_id'] = file_id
                            row_df['curve_indx'] = curve_indx
                            outputdf = outputdf.append(row_df, ignore_index=True)
                        elif result_type == 'vdrag_results':
                            row_df = pd.DataFrame(columns=['file_id', 'curve_indx', 'distances', 'frequency', 'Bh', 'Hd_real', 'Hd_imag'])
                            curve_indx = curve_result[0]
                            vdrag_result = curve_result[1]
                            row_df['frequency'] = vdrag_result[0]
                            row_df['Bh'] = vdrag_result[1]
                            row_df['Hd_real'] = vdrag_result[2].real
                            row_df['Hd_imag'] = vdrag_result[2].imag
                            row_df['distances'] = vdrag_result[4]
                            row_df['file_id'] = file_id
                            row_df['curve_indx'] = curve_indx
                            outputdf = outputdf.append(row_df, ignore_index=True)
                        elif result_type == 'microrheo_results':
                            row_df = pd.DataFrame(columns=['file_id', 'curve_indx', 'frequency', 'G_storage', 'G_loss', 'losstan'])
                            curve_indx = curve_result[0]
                            microrheo_result = curve_result[1]
                            row_df['frequency'] = microrheo_result[0]
                            row_df['G_storage'] = microrheo_result[1]
                            row_df['G_loss'] = microrheo_result[2]
                            row_df['losstan'] = row_df['G_storage'] / row_df['G_loss']
                            row_df['file_id'] = file_id
                            row_df['curve_indx'] = curve_indx
                            outputdf = outputdf.append(row_df, ignore_index=True)
                outputdf.to_csv(os.path.join(dirname, f'{file_prefix}_{result_type}.csv'), index=False)