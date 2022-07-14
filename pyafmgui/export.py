import os
import pandas as pd

result_types = [
    'hertz_results',
    'ting_results', 
    'piezochar_results',
    'vdrag_results',
    'microrheo_results'
]

def unpack_hertz_result(row_dict, hertz_result):
    row_dict['hertz_ind_geometry'] = hertz_result.ind_geom
    row_dict['hertz_tip_parameter'] = hertz_result.tip_parameter
    row_dict['hertz_apply_BEC'] = hertz_result.apply_bec_flag
    row_dict['hertz_BEC_model'] = hertz_result.bec_model
    row_dict['hertz_fit_hline_on_baseline'] = hertz_result.fit_hline_flag
    row_dict['hertz_delta0'] = hertz_result.delta0
    row_dict['hertz_E0'] = hertz_result.E0
    row_dict['hertz_f0'] = hertz_result.f0
    row_dict['hertz_slope'] = hertz_result.slope
    row_dict['hertz_poisson_ratio'] = hertz_result.poisson_ratio
    row_dict['hertz_sample_height'] = hertz_result.sample_height
    row_dict['hertz_MAE'] = hertz_result.MAE
    row_dict['hertz_MSE'] = hertz_result.MSE
    row_dict['hertz_RMSE'] = hertz_result.RMSE
    row_dict['hertz_Rsquared'] = hertz_result.Rsquared
    row_dict['hertz_chisq'] = hertz_result.chisq
    row_dict['hertz_redchi'] = hertz_result.redchi
    return row_dict

def unpack_ting_result(row_dict, ting_result):
    row_dict['ting_ind_geometry'] = ting_result.ind_geom
    row_dict['ting_tip_parameter'] = ting_result.tip_parameter
    row_dict['ting_modelFt'] = ting_result.modelFt
    row_dict['ting_apply_BEC'] = ting_result.apply_bec_flag
    row_dict['ting_BEC_model'] = ting_result.bec_model
    row_dict['ting_fit_hline_on_baseline'] = ting_result.fit_hline_flag
    row_dict['ting_t0'] = ting_result.t0
    row_dict['ting_E0'] = ting_result.E0
    row_dict['ting_tc'] = ting_result.tc
    row_dict['ting_betaE'] = ting_result.betaE
    row_dict['ting_f0'] = ting_result.F0
    row_dict['ting_poisson_ratio'] = ting_result.poisson_ratio
    row_dict['ting_vdrag'] = ting_result.vdrag
    row_dict['ting_smooth_w'] = ting_result.smooth_w
    row_dict['ting_idx_tm'] = ting_result.idx_tm
    row_dict['ting_MAE'] = ting_result.MAE
    row_dict['ting_MSE'] = ting_result.MSE
    row_dict['ting_RMSE'] = ting_result.RMSE
    row_dict['ting_Rsquared'] = ting_result.Rsquared
    row_dict['ting_chisq'] = ting_result.chisq
    row_dict['ting_redchi'] = ting_result.redchi
    return row_dict

def unpack_piezochar_result(row_dict, piezochar_result):
    row_dict['frequency'] = piezochar_result[0]
    row_dict['fi_degrees'] = piezochar_result[1]
    row_dict['amp_quot'] = piezochar_result[2]
    return row_dict

def unpack_vdrag_result(row_dict, vdrag_result):
    row_dict['frequency'] = vdrag_result[0]
    row_dict['Bh'] = vdrag_result[1]
    row_dict['Hd_real'] = vdrag_result[2].real
    row_dict['Hd_imag'] = vdrag_result[2].imag
    row_dict['distances'] = vdrag_result[4]
    return row_dict

def unpack_microrheo_result(row_dict, microrheo_result):
    row_dict['frequency'] = microrheo_result[0]
    row_dict['G_storage'] = microrheo_result[1]
    row_dict['G_loss'] = microrheo_result[2]
    row_dict['losstan'] = row_dict['G_storage'] / row_dict['G_loss']
    return row_dict

def prepare_export_results(session):

    results = {
        'hertz_results': session.hertz_fit_results,
        'ting_results': session.ting_fit_results,
        'piezochar_results': session.piezo_char_results,
        'vdrag_results': session.vdrag_results,
        'microrheo_results': session.microrheo_results
    }

    output = {
        'hertz_results': None,
        'ting_results': None, 
        'piezochar_results': None,
        'vdrag_results': None,
        'microrheo_results': None
    }

    for result_type, result in results.items():
        if result != {}:
            outputdf = pd.DataFrame()
            for file_id, file_result in result.items():
                filemetadata = session.loaded_files[file_id].filemetadata
                file_path = filemetadata['file_path']
                k = filemetadata['spring_const_Nbym']
                defl_sens = filemetadata['defl_sens_nmbyV']
                for curve_result in file_result:
                    curve_indx = curve_result[0]
                    row_dict = {
                        'file_path': file_path, 'file_id': file_id, 
                        'curve_idx': curve_indx, 'kcanti': k, 'defl_sens': defl_sens
                    }
                    if curve_result[1] is None:
                        outputdf = outputdf.append(row_dict, ignore_index=True)
                    elif result_type == 'hertz_results':
                        hertz_result = curve_result[1]
                        row_dict = unpack_hertz_result(row_dict, hertz_result)
                    elif result_type == 'ting_results':
                        curve_indx = curve_result[0]
                        ting_result = curve_result[1][0]
                        hertz_result = curve_result[1][1]
                        row_dict = unpack_hertz_result(row_dict, hertz_result)
                        row_dict = unpack_ting_result(row_dict, ting_result)
                    elif result_type == 'piezochar_results':
                        curve_indx = curve_result[0]
                        piezochar_result = curve_result[1]
                        row_dict = unpack_piezochar_result(row_dict, piezochar_result)
                    elif result_type == 'vdrag_results':
                        curve_indx = curve_result[0]
                        vdrag_result = curve_result[1]
                        row_dict = unpack_vdrag_result(row_dict, vdrag_result)
                    elif result_type == 'microrheo_results':
                        curve_indx = curve_result[0]
                        microrheo_result = curve_result[1]
                        row_dict = unpack_microrheo_result(row_dict, microrheo_result)
                    outputdf = outputdf.append(row_dict, ignore_index=True)
            output[result_type] = outputdf
    return output

def export_results(results, dirname, file_prefix):
    success_flag = False
    for result_type, result_df in results.items():
        if result_df is None:
            continue
        result_df.to_csv(os.path.join(dirname, f'{file_prefix}_{result_type}.csv'), index=False)
        success_flag = True
    return success_flag