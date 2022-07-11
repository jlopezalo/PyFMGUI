import numpy as np

from pyafmrheo.utils.force_curves import *
from pyafmrheo.utils.signal_processing import *
from pyafmrheo.models.rheology import ComputePiezoLag, ComputeBh, ComputeComplexModulus

from pyafmgui.helpers.curve_utils import *
from pyafmgui.helpers.sineFit_utils import *

def do_piezo_char(self, file_data, curve_indx):
    curve_data = preprocess_curve(file_data, curve_indx, self.height_channel, self.def_sens)
    results = []
    modulation_segs_data = [seg_data for _, seg_type, seg_data in curve_data if seg_type == 'modulation']
    for seg_data in modulation_segs_data:
        time = seg_data['time']
        zheight = seg_data['height']
        deflection = seg_data['deflection']
        frequency = seg_data['frequency']
        if self.max_freq != 0 and frequency > self.max_freq:
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

def do_vdrag_char(self, file_data, curve_indx):
    fi = 0
    amp_quotient = 1
    curve_data = preprocess_curve(file_data, curve_indx, self.height_channel, self.def_sens)
    distances = get_retract_ramp_sizes(file_data, curve_indx)
    results = []
    modulation_segs_data = [seg_data for _, seg_type, seg_data in curve_data if seg_type == 'modulation']
    for seg_data in modulation_segs_data:
        time = seg_data['time']
        zheight = seg_data['height']
        deflection = seg_data['deflection']
        frequency = seg_data['frequency']
        if self.max_freq != 0 and frequency > self.max_freq:
            continue
        deltat = time[1] - time[0]
        fs = 1 / deltat
        if self.session.piezo_char_data is not None:
            piezoChar =  self.session.piezo_char_data.loc[self.session.piezo_char_data['frequency'] == frequency]
            if len(piezoChar) == 0:
                print(f"The frequency {frequency} was not found in the piezo characterization dataframe")
            else:
                fi = piezoChar['fi_degrees'].item() # In degrees
                amp_quotient = piezoChar['amp_quotient'].item()
        zheight, deflection, _ =\
            detrend_rolling_average(frequency, zheight, deflection, time, 'zheight', 'deflection', [])
        Bh, Hd, gamma2 = ComputeBh(deflection, zheight, [0, 0], self.k, fs, frequency, fi=fi, amp_quotient=amp_quotient)
        results.append((frequency, Bh, Hd, gamma2))
    results = sorted(results, key=lambda x: int(x[0]))
    frequencies_results = [x[0] for x in results]
    Bh_results = [x[1] for x in results]
    Hd_results = np.array([x[2] for x in results])
    gamma2_results = [x[3] for x in results]
    return (frequencies_results, Bh_results, Hd_results, gamma2_results, distances)

def do_microrheo(self, file_data, curve_indx):
    fi = 0
    amp_quotient = 1
    curve_data = preprocess_curve(file_data, curve_indx, self.height_channel, self.def_sens)
    app_data = curve_data[0][2]
    app_zheight = app_data['height']
    app_deflection = app_data['deflection']
    rov_PoC = get_poc_RoV_method(app_zheight, app_deflection, win_size=self.poc_win)
    poc = [rov_PoC[0], 0]
    app_indentation, app_force = get_force_vs_indentation_curve(app_zheight, app_deflection, poc, self.k)
    p0 = [self.d0, self.f0, self.slope, self.E0]
    hertz_result = HertzFit(app_indentation, app_force,  self.contact_model,  self.tip_param, p0,  self.poisson)
    hertz_d0 = hertz_result.best_values['delta0']
    poc[0] += hertz_d0
    poc[1] = 0
    app_indentation, app_force = get_force_vs_indentation_curve(app_zheight, app_deflection, poc, self.k)
    wc = app_indentation.max()
    results = []
    modulation_segs_data = [seg_data for _, seg_type, seg_data in curve_data if seg_type == 'modulation']
    poc = [0, 0] # Assume d0 as 0, since we are in contact.
    for seg_data in modulation_segs_data:
        time = seg_data['time']
        zheight = seg_data['height']
        deflection = seg_data['deflection']
        frequency = seg_data['frequency']
        if self.max_freq != 0 and frequency > self.max_freq:
            continue
        deltat = time[1] - time[0]
        fs = 1 / deltat
        if self.session.piezo_char_data is not None:
            piezoChar =  self.session.piezo_char_data.loc[self.session.piezo_char_data['frequency'] == frequency]
            if len(piezoChar) == 0:
                print(f"The frequency {frequency} was not found in the piezo characterization dataframe")
            else:
                fi = piezoChar['fi_degrees'].item() # In degrees
                amp_quotient = piezoChar['amp_quotient'].item()
        zheight, deflection, _ =\
            detrend_rolling_average(frequency, zheight, deflection, time, 'zheight', 'deflection', [])
        G_storage, G_loss, gamma2 =\
            ComputeComplexModulus(
                deflection, zheight, poc, self.k, fs, frequency, self.contact_model,
                self.tip_param, wc, self.poisson, fi=fi, amp_quotient=amp_quotient, bcoef=self.bcoef
            )
        results.append((frequency, G_storage, G_loss, gamma2))
    results = sorted(results, key=lambda x: int(x[0]))
    frequencies_results = [x[0] for x in results]
    G_storage_results = [x[1] for x in results]
    G_loss_results = [x[2] for x in results]
    gamma2_results = [x[3] for x in results]
    return (frequencies_results, G_storage_results, G_loss_results, gamma2_results)

def do_microrheo_sine(self, file_data, curve_indx):
    curve_data = preprocess_curve(file_data, curve_indx, self.height_channel, self.def_sens)
    app_data = curve_data[0][2]
    app_zheight = app_data['height']
    app_deflection = app_data['deflection']
    rov_PoC = get_poc_RoV_method(app_zheight, app_deflection, win_size=self.poc_win)
    poc = [rov_PoC[0], 0]
    app_indentation, app_force = get_force_vs_indentation_curve(app_zheight, app_deflection, poc, self.k)
    p0 = [self.d0, self.f0, self.slope, self.E0]
    hertz_result = HertzFit(app_indentation, app_force,  self.contact_model,  self.tip_param, p0,  self.poisson)
    hertz_d0 = hertz_result.best_values['delta0']
    poc[0] += hertz_d0
    poc[1] = 0
    app_indentation, app_force = get_force_vs_indentation_curve(app_zheight, app_deflection, poc, self.k)
    wc = app_indentation.max()
    results = []
    modulation_segs_data = [seg_data for _, seg_type, seg_data in curve_data if seg_type == 'modulation']
    for seg_data in modulation_segs_data:
        time = seg_data['time']
        zheight = seg_data['height']
        deflection = seg_data['deflection']
        frequency = seg_data['frequency']
        if self.max_freq != 0 and frequency > self.max_freq:
            continue
        if self.session.piezo_char_data is not None:
            piezoChar =  self.session.piezo_char_data.loc[self.session.piezo_char_data['frequency'] == frequency]
            if len(piezoChar) == 0:
                print(f"The frequency {frequency} was not found in the piezo characterization dataframe")
            else:
                fi = piezoChar['fi_degrees'].item() # In degrees
                amp_quotient = piezoChar['amp_quotient'].item()
                # Implement correction for amplitude and phi
        
        zheight, deflection, time =\
            detrend_rolling_average(frequency, zheight, deflection, time, 'zheight', 'deflection', [])
        
        indentation, _ = get_force_vs_indentation_curve(zheight, deflection, [0,0], self.k)
        
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
            self.contact_model, self.tip_param, self.k, self.poisson, A_defl, A_ind, wc, dPhi, frequency, self.bcoef
            )
        
        results.append((frequency, G.real, G.imag, ind_res, defl_res))
    
    results = sorted(results, key=lambda x: int(x[0]))
    frequencies_results = [x[0] for x in results]
    G_storage_results = [x[1] for x in results]
    G_loss_results = [x[2] for x in results]
    ind_sinfit_results = [x[3] for x in results]
    defl_sinfit_results = [x[4] for x in results]
    return (frequencies_results, G_storage_results, G_loss_results, ind_sinfit_results, defl_sinfit_results)