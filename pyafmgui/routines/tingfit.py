import numpy as np

from pyafmrheo.utils.force_curves import get_poc_RoV_method, correct_viscous_drag
from pyafmrheo.models.hertz import HertzModel
from pyafmrheo.models.ting import TingModel

def do_ting_fit(fdc, param_dict):
    # Get data from the first extend segments and last retract segment
    ext_data = fdc.extend_segments[0][1]
    ret_data = fdc.retract_segments[-1][1]

    # Find PoC on the extend segment via RoV method
    ext_zheight = ext_data.zheight
    ext_deflection = ext_data.vdeflection
    rov_PoC = get_poc_RoV_method(ext_zheight, ext_deflection, win_size=param_dict['poc_win'])
    poc = [rov_PoC[0], 0]

    # Compute force and indentation
    fdc.get_force_vs_indentation(poc, param_dict['k'])

    # Do HertzFit
    ext_indentation = ext_data.indentation
    ext_force = ext_data.force
    hertz_model = HertzModel(param_dict['contact_model'], param_dict['tip_param'])
    hertz_model.d0_init = param_dict['d0']
    if not param_dict['auto_init_E0']:
        hertz_model.E0_init = param_dict['E0']
    hertz_model.f0_init = param_dict['f0']
    hertz_model.fit(ext_indentation, ext_force)
    hertz_E = hertz_model.E0
    hertz_d0 = hertz_model.delta0

    # Shift PoC using d0 obtained in HertzFit
    poc[0] += hertz_d0

    # Compute force and indentation with new PoC
    fdc.get_force_vs_indentation(poc, param_dict['k'])

    # Get force, indentation and time from the extend and retract segments
    ext_indentation = ext_data.indentation
    ext_force = ext_data.force
    ext_time = ext_data.time
    ret_indentation = ret_data.indentation
    ret_force = ret_data.force
    ret_time = ret_data.time
    
    # Check time offset
    t_offset = np.abs(ext_data.zheight[-1] - ret_data.zheight[0]) / (ext_data.velocity * -1e-9)
    dt = np.abs(ext_data.time[1] - ext_data.time[0])
    if t_offset > 2*dt:
        ret_time = ret_time + t_offset

    # Correct for viscous drag by fitting a line on the
    # extend and retract base liness.
    if param_dict['vdragcorr']:
        ext_force, ret_force = correct_viscous_drag(
            ext_indentation, ext_force, ret_indentation, ret_force, poly_order=param_dict['polyordr'], speed=param_dict['rampspeed'])
    
    # Fortmat data for TingFit
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

    # Get index of tm, tm and the intial guess of tc
    idx_tm = np.argmax(force_fit)
    tm = time_fit[idx_tm]
    tc = tm/2

    if not param_dict['compute_v_flag']:
        v0t = ext_data.velocity * -1e-9
        v0r = ret_data.velocity * -1e-9
    else:
        v0t, v0r = None, None

    # Perform TingFit
    ting_model = TingModel(param_dict['contact_model'], param_dict['tip_param'], param_dict['model_type'])
    ting_model.betaE_init = param_dict['fluid_exp']
    ting_model.E0_init = hertz_E
    ting_model.tc_init = tc
    ting_model.f0_init = param_dict['f0']
    ting_model.vdrag = param_dict['vdrag']
    ting_model.poisson =  param_dict['poisson']
    ting_model.fit(
        time_fit, force_fit, ind_fit, t0=param_dict['t0'], idx_tm=idx_tm,
        smooth_w=param_dict['smoothing_win'], v0t=v0t, v0r=v0r
    )

    # Return the results of the TingFit and HertzFit
    return ting_model, hertz_model