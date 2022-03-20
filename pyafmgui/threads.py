import os
import PyQt5
from pyqtgraph.Qt import QtCore

from jpkreader import load_jpk_file

from pyafmrheo.utils.force_curves import *
from pyafmrheo.utils.signal_processing import *
from pyafmrheo.hertz_fit import HertzFit
from pyafmrheo.ting_fit import TingFit
from pyafmrheo.models.rheology import ComputePiezoLag, ComputeBh, ComputeComplexModulus

import pyafmgui.const as ct
from pyafmgui.helpers.curve_utils import *
from pyafmgui.helpers.sineFit_utils import *

class LoadFilesThread(QtCore.QThread):
    _signal_id = QtCore.pyqtSignal(str)
    _signal_file_progress = QtCore.pyqtSignal(int)
    def __init__(self, session, filelist):
        super(LoadFilesThread, self).__init__()
        self.session = session
        self.filelist = filelist

    def run(self):
        for i, filepath in enumerate(self.filelist):
            self._signal_id.emit(filepath)
            _, extension = os.path.splitext(filepath)
            if extension in ct.jpk_file_extensions:
                file = load_jpk_file(filepath)
                self.session.loaded_files[file.file_id] = file
            self._signal_file_progress.emit(i)

class ProcessFilesThread(QtCore.QThread):
    _signal_id = QtCore.pyqtSignal(str)
    _signal_file_progress = QtCore.pyqtSignal(int)
    _signal_curve_progress = QtCore.pyqtSignal(int)
    def __init__(self, session, params, filedict, method, dialog):
        super(ProcessFilesThread, self).__init__()
        self.session = session
        self.params = params
        self.method = method
        self.filedict = filedict
        self.dialog = dialog
    
    def get_params(self):
        analysis_params = self.params.child('Analysis Params')
        self.height_channel = analysis_params.child('Height Channel').value()
        self.def_sens = analysis_params.child('Deflection Sensitivity').value() / 1e9
        self.k = analysis_params.child('Spring Constant').value()
        if self.method in ("PiezoChar", "VDrag", "Microrheo", "MicrorheoSine"):
            self.max_freq = analysis_params.child('Max Frequency').value()
        if self.method in ("PiezoChar", "VDrag"):
            return
        if self.method in ("Microrheo", "MicrorheoSine"):
            self.bcoef = analysis_params.child('B Coef').value()
        self.contact_model = analysis_params.child('Contact Model').value()
        if self.contact_model == "paraboloid":
            self.tip_param = analysis_params.child('Tip Radius').value() / 1e9 
        elif self.contact_model in ("cone", "pyramid"):
            self.tip_param = analysis_params.child('Tip Angle').value()
        self.curve_seg = analysis_params.child('Curve Segment').value()
        if self.method  in ("HertzFit", "Microrheo", "MicrorheoSine"):
            hertz_params = self.params.child('Hertz Fit Params')
            self.poisson = hertz_params.child('Poisson Ratio').value()
            self.poc_win = hertz_params.child('PoC Window').value()
            self.E0 = hertz_params.child('Init E0').value()
            self.d0 = hertz_params.child('Init d0').value() / 1e9 
            self.f0 = hertz_params.child('Init f0').value()
            self.slope = hertz_params.child('Init Slope').value()
            self.fit_range_type = hertz_params.child('Fit Range Type').value()
            self.max_ind = hertz_params.child('Max Indentation').value() / 1e9  
            self.min_ind = hertz_params.child('Min Indentation').value() / 1e9 
            self.max_force = hertz_params.child('Max Force').value() / 1e9 
            self.min_force = hertz_params.child('Min Force').value() / 1e9 
            self.fit_line = hertz_params.child('Fit Line to non contact').value()
        elif self.method == "TingFit":
            ting_params = self.params.child('Ting Fit Params')
            self.poisson = ting_params.child('Poisson Ratio').value()
            self.poc_win = ting_params.child('PoC Window').value()
            self.vdragcorr = ting_params.child('Correct Viscous Drag').value()
            self.polyordr = ting_params.child('Poly. Order').value()
            self.rampspeed = ting_params.child('Ramp Speed').value() / 1e6
            self.t0 = ting_params.child('t0').value()
            self.d0 = ting_params.child('Init d0').value() / 1e9 
            self.slope = ting_params.child('Init Slope').value()
            self.E0 = ting_params.child('Init E0').value()
            self.tc = ting_params.child('Init tc').value()
            self.fluid_exp = ting_params.child('Init Fluid. Exp.').value()
            self.f0 = ting_params.child('Init f0').value()
            self.vdrag = ting_params.child('Viscous Drag').value()
            self.model_type = ting_params.child('Model Type').value()
            self.smoothing_win = ting_params.child('Smoothing Window').value()
            self.contact_offset = ting_params.child('Contact Offset').value() / 1e6
                
    
    def do_hertz_fit(self, file_data, curve_indx):
        curve_data = preprocess_curve(file_data, curve_indx, self.height_channel, self.def_sens)
        if self.curve_seg == 'extend':
            segment_data = curve_data[0][2]
            zheight = segment_data['height']
            deflection = segment_data['deflection']
        else:
            segment_data = curve_data[-1][2]
            zheight = segment_data['height'][::-1]
            deflection = segment_data['deflection'][::-1]
        rov_PoC = get_poc_RoV_method(zheight, deflection, win_size=self.poc_win)
        poc = [rov_PoC[0], 0]
        indentation, force = get_force_vs_indentation_curve(zheight, deflection, poc, self.k)
        force = force - force[0]
        contact_mask = indentation >= 0
        ncont_ind = indentation[~contact_mask]
        cont_ind = indentation[contact_mask]
        ncont_force = force[~contact_mask]
        cont_force = force[contact_mask]
        if self.fit_range_type == 'indentation':
            mask = (cont_ind >= self.min_ind) & (cont_ind <= self.max_ind)
        elif self.fit_range_type == 'force':
            mask = (cont_force >= self.min_force) & (cont_force <= self.max_force)
        cont_ind, cont_force = cont_ind[mask], cont_force[mask]
        indentation = np.r_[ncont_ind, cont_ind]
        force = np.r_[ncont_force, cont_force]
        p0 = [self.d0, self.f0, self.slope, self.E0]
        return HertzFit(indentation, force,  self.contact_model, self.tip_param, p0, self.poisson, self.fit_line)
    
    def do_ting_fit(self, file_data, curve_indx):
        curve_data = preprocess_curve(file_data, curve_indx, self.height_channel, self.def_sens)
        ext_data = curve_data[0][2]
        ext_zheight = ext_data['height']
        ext_deflection = ext_data['deflection']
        ext_time = ext_data['time']
        ret_data = curve_data[-1][2]
        ret_zheight = ret_data['height']
        ret_deflection = ret_data['deflection']
        ret_time = ret_data['time']
        rov_PoC = get_poc_RoV_method(ext_zheight, ext_deflection, win_size=self.poc_win)
        poc = [rov_PoC[0], 0]
        ext_indentation, ext_force = get_force_vs_indentation_curve(ext_zheight, ext_deflection, poc, self.k)
        p0 = [self.d0, self.f0, self.slope, self.E0]
        hertz_result =  HertzFit(ext_indentation, ext_force,  self.contact_model,  self.tip_param, p0,  self.poisson)
        hertz_E = hertz_result.best_values['E0']
        hertz_d0 = hertz_result.best_values['delta0']
        poc[0] += hertz_d0
        ext_indentation, ext_force = get_force_vs_indentation_curve(ext_zheight, ext_deflection, poc, self.k)
        ret_indentation, ret_force = get_force_vs_indentation_curve(ret_zheight, ret_deflection, poc, self.k)
        if self.vdragcorr:
            ext_force, ret_force = correct_viscous_drag(
                ext_indentation, ext_force, ret_indentation, ret_force, poly_order=self.polyordr, speed=self.rampspeed)
        indentation = np.r_[ext_indentation, ret_indentation]
        force = np.r_[ext_force, ret_force]
        t0 = ext_time[-1]
        time = np.r_[ext_time, ret_time + t0]
        fit_mask = indentation > (-1 * self.contact_offset)
        ind_fit = indentation[fit_mask] 
        force_fit = force[fit_mask]
        force_fit = force_fit - force_fit[0]
        time_fit = time[fit_mask]
        time_fit = time_fit - time_fit[0]
        tm = time_fit[np.argmax(force_fit)]
        tc = tm/2

        p0_ting = [self.t0, hertz_E, tc, self.fluid_exp, self.f0]

        ting_result = TingFit(
            force_fit, ind_fit, time_fit, self.contact_model, self.tip_param,
            p0_ting, self.model_type, self.poisson, self.vdrag, self.smoothing_win
        )

        return ting_result, hertz_result
    
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
    
    def clear_file_results(self, file_id):
        if file_id in self.session.hert_fit_results and self.method == "HertzFit":
            self.session.hert_fit_results.pop(file_id)
        elif file_id in self.session.ting_fit_results and self.method == "TingFit":
            self.session.ting_fit_results.pop(file_id)
        elif file_id in self.session.piezo_char_results and self.method == "PiezoChar":
            self.session.piezo_char_results.pop(file_id)
        elif file_id in self.session.vdrag_results and self.method == "VDrag":
            self.session.vdrag_results.pop(file_id)
        elif file_id in self.session.microrheo_results and self.method == "Microrheo":
            self.session.microrheo_results.pop(file_id)

    def run(self):
        self.get_params()
        for i, (file_id, file) in enumerate(self.filedict.items()):
            self.clear_file_results(file_id)
            self._signal_id.emit(file_id)
            ncurves = len(file.data)
            self.dialog.pbar_curves.setRange(0, ncurves-1)
            if not self.params.child('General Options').child('Compute All Curves').value():
                if self.method  == "HertzFit":
                    try:
                        hertz_result = self.do_hertz_fit(file.data, self.session.current_curve_index)
                    except ValueError:
                        hertz_result = None
                    self.session.hert_fit_results[file_id] = [(self.session.current_curve_index, hertz_result)]
                elif self.method == "TingFit":
                    try:
                        ting_result, hertz_result = self.do_ting_fit(file.data, self.session.current_curve_index)
                    except (ValueError, IndexError, TypeError):
                        ting_result, hertz_result = None, None
                    self.session.ting_fit_results[file_id] = [(self.session.current_curve_index, hertz_result, ting_result)]
                elif self.method == "PiezoChar":
                    piezo_char_result = self.do_piezo_char(file.data, self.session.current_curve_index)
                    self.session.piezo_char_results[file_id] = [(self.session.current_curve_index, piezo_char_result)]
                elif self.method == "VDrag":
                    vdrag_result = self.do_vdrag_char(file.data, self.session.current_curve_index)
                    self.session.vdrag_results[file_id] = [(self.session.current_curve_index, vdrag_result)]
                elif self.method == "Microrheo":
                    microrheo_result = self.do_microrheo(file.data, self.session.current_curve_index)
                    self.session.microrheo_results[file_id] = [(self.session.current_curve_index, microrheo_result)]
                elif self.method == "MicrorheoSine":
                    microrheo_result = self.do_microrheo_sine(file.data, self.session.current_curve_index)
                    self.session.microrheo_results[file_id] = [(self.session.current_curve_index, microrheo_result)]
            else:
                for curve_indx in range(ncurves):
                    if self.method  == "HertzFit":
                        try:
                            hertz_result = self.do_hertz_fit(file.data, curve_indx)
                        except ValueError:
                            hertz_result = None
                        if file_id in self.session.hert_fit_results.keys():
                            self.session.hert_fit_results[file_id].extend([(curve_indx, hertz_result)])
                        else:
                            self.session.hert_fit_results[file_id] = [(curve_indx, hertz_result)]
                    elif self.method == "TingFit":
                        try:
                            ting_result, hertz_result = self.do_ting_fit(file.data, curve_indx)
                        except (ValueError, IndexError, TypeError):
                            ting_result, hertz_result = None, None
                        if file_id in self.session.ting_fit_results.keys():
                            self.session.ting_fit_results[file_id].extend([(curve_indx, hertz_result, ting_result)])
                        else:
                            self.session.ting_fit_results[file_id] = [(curve_indx, hertz_result, ting_result)]
                    elif self.method == "PiezoChar":
                        piezo_char_result = self.do_piezo_char(file.data, curve_indx)
                        if file_id in self.session.piezo_char_results.keys():
                            self.session.piezo_char_results[file_id].extend([(curve_indx, piezo_char_result)])
                        else:
                            self.session.piezo_char_results[file_id] = [(curve_indx, piezo_char_result)]
                    elif self.method == "VDrag":
                        vdrag_result = self.do_vdrag_char(file.data, curve_indx)
                        if file_id in self.session.vdrag_results.keys():
                            self.session.vdrag_results[file_id].extend([(curve_indx, vdrag_result)])
                        else:
                            self.session.vdrag_results[file_id] = [(curve_indx, vdrag_result)]
                    elif self.method == "Microrheo":
                        microrheo_result = self.do_microrheo(file.data, curve_indx)
                        if file_id in self.session.microrheo_results.keys():
                            self.session.microrheo_results[file_id].extend([(curve_indx, microrheo_result)])
                        else:
                            self.session.microrheo_results[file_id] = [(curve_indx, microrheo_result)]
                    elif self.method == "MicrorheoSine":
                        microrheo_result = self.do_microrheo_sine(file.data, curve_indx)
                        if file_id in self.session.microrheo_results.keys():
                            self.session.microrheo_results[file_id].extend([(curve_indx, microrheo_result)])
                        else:
                            self.session.microrheo_results[file_id] = [(curve_indx, microrheo_result)]
                    self._signal_curve_progress.emit(curve_indx)
            self._signal_file_progress.emit(i)