import numpy as np

from pyafmrheo.utils.force_curves import *
from pyafmrheo.utils.signal_processing import *
from pyafmrheo.models.rheology import ComputePiezoLag, ComputeBh, ComputeComplexModulus

from pyafmgui.helpers.sineFit_utils import *
from pyafmgui.routines.hertzfit import do_hertz_fit

def get_retract_ramp_sizes(force_curve):
    x0 = 0
    distances = []
    sorted_ret_segments = sorted(force_curve.retract_segments, key=lambda x: int(x[0]))
    for _, first_ret_seg in sorted_ret_segments[:-1]:
        distance_from_sample = -1 * first_ret_seg.segment_metadata['ramp_size'] + x0 # Negative
        distances.append(distance_from_sample * 1e-9) # in nm
    return distances

def do_piezo_char(fdc, param_dict):
    results = []
    for _, segment in fdc.modulation_segments:
        time = segment.time
        zheight = segment.zheight
        deflection = segment.vdeflection
        frequency = segment.segment_metadata['frequency']
        if param_dict['max_freq'] != 0 and frequency > param_dict['max_freq']:
            continue
        deltat = time[1] - time[0]
        fs = 1 / deltat
        ntra_in, ntra_out, _ =\
            detrend_rolling_average(frequency, zheight, deflection, time, 'zheight', 'deflection', [])
        fi, amp_quotient, gamma2 =\
            ComputePiezoLag(ntra_in, ntra_out, fs, frequency)
        results.append((frequency, fi, amp_quotient, gamma2))
    results = sorted(results, key=lambda x: int(x[0]))
    frequencies_results = [x[0] for x in results]
    fi_results = [x[1] for x in results]
    amp_quotient_results = [x[2] for x in results]
    gamma2_results = [x[3] for x in results]

    return (frequencies_results, fi_results, amp_quotient_results, gamma2_results)

def do_vdrag_char(fdc, param_dict):
    fi = 0
    amp_quotient = 1
    distances = get_retract_ramp_sizes(fdc)
    results = []
    for _, segment in fdc.modulation_segments:
        time = segment.time
        zheight = segment.zheight
        deflection = segment.vdeflection
        frequency = segment.segment_metadata['frequency']
        if param_dict['max_freq'] != 0 and frequency > param_dict['max_freq']:
            continue
        deltat = time[1] - time[0]
        fs = 1 / deltat
        if param_dict['piezo_char_data'] is not None:
            piezoChar =  param_dict['piezo_char_data'].loc[param_dict['piezo_char_data']['frequency'] == frequency]
            if len(piezoChar) == 0:
                print(f"The frequency {frequency} was not found in the piezo characterization dataframe")
            else:
                fi = piezoChar['fi_degrees'].item() # In degrees
                amp_quotient = piezoChar['amp_quotient'].item()
        zheight, deflection, _ =\
            detrend_rolling_average(frequency, zheight, deflection, time, 'zheight', 'deflection', [])
        Bh, Hd, gamma2 = ComputeBh(deflection, zheight, [0, 0], param_dict['k'], fs, frequency, fi=fi, amp_quotient=amp_quotient)
        results.append((frequency, Bh, Hd, gamma2))
    results = sorted(results, key=lambda x: int(x[0]))
    frequencies_results = [x[0] for x in results]
    Bh_results = [x[1] for x in results]
    Hd_results = np.array([x[2] for x in results])
    gamma2_results = [x[3] for x in results]
    return (frequencies_results, Bh_results, Hd_results, gamma2_results, distances)

def do_microrheo(fdc, param_dict):
    fi = 0
    amp_quotient = 1
    if param_dict['curve_seg'] == 'extend':
        segment_data = fdc.extend_segments[0][1]
    else:
        segment_data = fdc.retract_segments[-1][1]
        segment_data.zheight = segment_data.zheight[::-1]
        segment_data.vdeflection = segment_data.vdeflection[::-1]
    rov_PoC = get_poc_RoV_method(
        segment_data.zheight, segment_data.vdeflection, win_size=param_dict['poc_win'])
    poc = [rov_PoC[0], 0]
    hertz_result = do_hertz_fit(fdc, param_dict)
    hertz_d0 = hertz_result.delta0
    poc[0] += hertz_d0
    poc[1] = 0
    segment_data.get_force_vs_indentation(poc, param_dict['k'])
    app_indentation = segment_data.indentation
    wc = app_indentation.max()
    results = []
    poc = [0, 0] # Assume d0 as 0, since we are in contact.
    for _, segment in fdc.modulation_segments:
        time = segment.time
        zheight = segment.zheight
        deflection = segment.vdeflection
        frequency = segment.segment_metadata['frequency']
        if param_dict['max_freq'] != 0 and frequency > param_dict['max_freq']:
            continue
        deltat = time[1] - time[0]
        fs = 1 / deltat
        if param_dict['piezo_char_data'] is not None:
            piezoChar =  param_dict['piezo_char_data'].loc[param_dict['piezo_char_data']['frequency'] == frequency]
            if len(piezoChar) == 0:
                print(f"The frequency {frequency} was not found in the piezo characterization dataframe")
            else:
                fi = piezoChar['fi_degrees'].item() # In degrees
                amp_quotient = piezoChar['amp_quotient'].item()
        zheight, deflection, _ =\
            detrend_rolling_average(frequency, zheight, deflection, time, 'zheight', 'deflection', [])
        G_storage, G_loss, gamma2 =\
            ComputeComplexModulus(
                deflection, zheight, poc, param_dict['k'], fs, frequency, param_dict['contact_model'],
                param_dict['tip_param'], wc, param_dict['poisson'], fi=fi, amp_quotient=amp_quotient, bcoef=param_dict['bcoef']
            )
        results.append((frequency, G_storage, G_loss, gamma2))
    results = sorted(results, key=lambda x: int(x[0]))
    frequencies_results = [x[0] for x in results]
    G_storage_results = [x[1] for x in results]
    G_loss_results = [x[2] for x in results]
    gamma2_results = [x[3] for x in results]
    return (frequencies_results, G_storage_results, G_loss_results, gamma2_results)

def do_microrheo_sine(fdc, param_dict):
    fi = 0
    amp_quotient = 1
    if param_dict['curve_seg'] == 'extend':
        segment_data = fdc.extend_segments[0][1]
    else:
        segment_data = fdc.retract_segments[-1][1]
        segment_data.zheight = segment_data.zheight[::-1]
        segment_data.vdeflection = segment_data.vdeflection[::-1]
    rov_PoC = get_poc_RoV_method(
        segment_data.zheight, segment_data.vdeflection, win_size=param_dict['poc_win'])
    poc = [rov_PoC[0], 0]
    hertz_result = do_hertz_fit(fdc, param_dict)
    hertz_d0 = hertz_result.delta0
    poc[0] += hertz_d0
    poc[1] = 0
    segment_data.get_force_vs_indentation(poc, param_dict['k'])
    app_indentation = segment_data.indentation
    wc = app_indentation.max()
    results = []
    poc = [0, 0] # Assume d0 as 0, since we are in contact.
    for _, segment in fdc.modulation_segments:
        time = segment.time
        zheight = segment.zheight
        deflection = segment.vdeflection
        frequency = segment.segment_metadata['frequency']
        if param_dict['max_freq'] != 0 and frequency > param_dict['max_freq']:
            continue
        deltat = time[1] - time[0]
        fs = 1 / deltat
        if param_dict['piezo_char_data'] is not None:
            piezoChar =  param_dict['piezo_char_data'].loc[param_dict['piezo_char_data']['frequency'] == frequency]
            if len(piezoChar) == 0:
                print(f"The frequency {frequency} was not found in the piezo characterization dataframe")
            else:
                fi = piezoChar['fi_degrees'].item() # In degrees
                amp_quotient = piezoChar['amp_quotient'].item()
        
        zheight, deflection, time =\
            detrend_rolling_average(frequency, zheight, deflection, time, 'zheight', 'deflection', [])
        
        #d0 = 0
        indentation = zheight - deflection
        
        omega = 2.*np.pi*frequency
        guess_amp_ind = np.std(indentation) * 2.**0.5
        guess_offset_ind = np.mean(indentation)
        guess_amp_defl = np.std(deflection) * 2.**0.5
        guess_offset_defl = np.mean(deflection)

        ind_res = SineFit(indentation, time, p0=[guess_amp_ind, omega, 0., guess_offset_ind])
        defl_res = SineFit(deflection, time, p0=[guess_amp_defl, omega, 0., guess_offset_defl])

        # Amplitude
        A_ind = ind_res.best_values['A']
        A_defl = defl_res.best_values['A']

        # Phase
        Phi_ind = ind_res.best_values['p']
        Phi_defl = defl_res.best_values['p']

        if A_ind < 0:
            A_ind = -A_ind
            Phi_ind += np.pi
        if A_defl < 0:
            A_defl = -A_defl
            Phi_defl += np.pi

        # Delta Phi
        dPhi = Phi_defl - Phi_ind

        G = getGComplex(
            param_dict['contact_model'], param_dict['tip_param'], param_dict['k'], 
            param_dict['poisson'], A_defl, A_ind, wc, dPhi, frequency, param_dict['bcoef']
        )
        
        results.append((frequency, G.real, G.imag, ind_res, defl_res))
    
    results = sorted(results, key=lambda x: int(x[0]))
    frequencies_results = [x[0] for x in results]
    G_storage_results = [x[1] for x in results]
    G_loss_results = [x[2] for x in results]
    ind_sinfit_results = [x[3] for x in results]
    defl_sinfit_results = [x[4] for x in results]
    return (frequencies_results, G_storage_results, G_loss_results, ind_sinfit_results, defl_sinfit_results)