import numpy as np

from pyafmrheo.utils.force_curves import get_poc_RoV_method, correct_viscous_drag
from pyafmrheo.models.hertz import HertzModel
from pyafmrheo.models.ting import TingModel

def do_ting_fit(fdc, param_dict):
    fdc.preprocess_force_curve(param_dict['def_sens'], param_dict['height_channel'])
    ext_data = fdc.extend_segments[0][1]
    ext_zheight = ext_data.zheight
    ext_deflection = ext_data.vdeflection
    ext_time = ext_data.time
    ret_data = fdc.retract_segments[-1][1]
    ret_time = ret_data.time
    rov_PoC = get_poc_RoV_method(ext_zheight, ext_deflection, win_size=param_dict['poc_win'])
    poc = [rov_PoC[0], 0]
    fdc.get_force_vs_indentation(poc, param_dict['k'])
    ext_indentation = ext_data.indentation
    ext_force = ext_data.force
    
    hertz_model = HertzModel(param_dict['contact_model'], param_dict['tip_param'])
    hertz_model.d0_init = param_dict['d0']
    hertz_model.E0_init = param_dict['E0']
    hertz_model.f0_init = param_dict['f0']
    hertz_model.fit(ext_indentation, ext_force)
    hertz_E = hertz_model.E0
    hertz_d0 = hertz_model.delta0

    poc[0] += hertz_d0
    fdc.get_force_vs_indentation(poc, param_dict['k'])
    ext_indentation = ext_data.indentation
    ext_force = ext_data.force
    ret_indentation = ret_data.indentation
    ret_force = ret_data.force
    if param_dict['vdragcorr']:
        ext_force, ret_force = correct_viscous_drag(
            ext_indentation, ext_force, ret_indentation, ret_force, poly_order=param_dict['polyordr'], speed=param_dict['rampspeed'])
    indentation = np.r_[ext_indentation, ret_indentation]
    force = np.r_[ext_force, ret_force]
    t0 = ext_time[-1]
    time = np.r_[ext_time, ret_time + t0]
    fit_mask = indentation > (-1 * param_dict['contact_offset'])
    ind_fit = indentation[fit_mask] 
    force_fit = force[fit_mask]
    force_fit = force_fit - force_fit[0]
    time_fit = time[fit_mask]
    time_fit = time_fit - time_fit[0]
    tm = time_fit[np.argmax(force_fit)]
    tc = tm/3

    ting_model = TingModel(param_dict['contact_model'], param_dict['tip_param'], param_dict['model_type'])
    ting_model.betaE_init = param_dict['fluid_exp']
    ting_model.E0_init = hertz_E
    ting_model.tc_init = tc
    ting_model.f0_init = param_dict['f0']
    ting_model.vdrag = param_dict['vdrag']
    ting_model.poisson =  param_dict['poisson']

    ting_model.fit(time_fit, force_fit, ind_fit, t0=param_dict['t0'], smooth_w=param_dict['smoothing_win'])

    return ting_model, hertz_model