def get_params(params, method):
    param_dict = {}
    param_dict['compute_all_curves'] = params.child('General Options').child('Compute All Curves').value()
    param_dict['method'] = method
    analysis_params = params.child('Analysis Params')
    param_dict['height_channel'] = analysis_params.child('Height Channel').value()
    param_dict['def_sens'] = analysis_params.child('Deflection Sensitivity').value() / 1e9
    param_dict['k'] = analysis_params.child('Spring Constant').value()
    if method in ("PiezoChar", "VDrag", "Microrheo", "MicrorheoSine"):
        param_dict['max_freq'] = analysis_params.child('Max Frequency').value()
    if method in ("PiezoChar", "VDrag"):
        return param_dict
    if method in ("Microrheo", "MicrorheoSine"):
        param_dict['bcoef'] = analysis_params.child('B Coef').value()
    param_dict['contact_model'] = analysis_params.child('Contact Model').value()
    if param_dict['contact_model'] == "paraboloid":
        param_dict['tip_param'] = analysis_params.child('Tip Radius').value() / 1e9 # nm
    elif param_dict['contact_model'] in ("cone", "pyramid"):
        param_dict['tip_param'] = analysis_params.child('Tip Angle').value()
    param_dict['curve_seg'] = analysis_params.child('Curve Segment').value()
    if method  in ("HertzFit", "Microrheo", "MicrorheoSine"):
        hertz_params = params.child('Hertz Fit Params')
        param_dict['poisson'] = hertz_params.child('Poisson Ratio').value()
        # param_dict['poc_win'] = hertz_params.child('PoC Window').value() / 1e9 #nm
        param_dict['poc_win'] = hertz_params.child('PoC Window').value()
        param_dict['auto_init_E0'] = hertz_params.child('Auto Init E0').value()
        param_dict['E0'] = hertz_params.child('Init E0').value()
        param_dict['d0'] = hertz_params.child('Init d0').value() / 1e9 #nm
        param_dict['f0'] = hertz_params.child('Init f0').value() / 1e9 #nN
        param_dict['slope'] = hertz_params.child('Init Slope').value()
        param_dict['fit_range_type'] = hertz_params.child('Fit Range Type').value()
        param_dict['max_ind'] = hertz_params.child('Max Indentation').value() / 1e9 #nm
        param_dict['min_ind'] = hertz_params.child('Min Indentation').value() / 1e9 #nm
        param_dict['max_force'] = hertz_params.child('Max Force').value() / 1e9 #nN
        param_dict['min_force'] = hertz_params.child('Min Force').value() / 1e9 #nN
        param_dict['fit_line'] = hertz_params.child('Fit Line to non contact').value()
    elif method == "TingFit":
        ting_params = params.child('Ting Fit Params')
        param_dict['poisson'] = ting_params.child('Poisson Ratio').value()
        # param_dict['poc_win'] = ting_params.child('PoC Window').value() / 1e9 #nm
        param_dict['poc_win'] = ting_params.child('PoC Window').value()
        param_dict['vdragcorr'] = ting_params.child('Correct Viscous Drag').value()
        param_dict['polyordr'] = ting_params.child('Poly. Order').value()
        param_dict['rampspeed'] = ting_params.child('Ramp Speed').value() / 1e6 #um/s
        param_dict['compute_v_flag'] = ting_params.child('Estimate V0t & V0r').value()
        param_dict['t0'] = ting_params.child('t0').value()
        param_dict['d0'] = ting_params.child('Init d0').value() / 1e9 
        param_dict['slope'] = ting_params.child('Init Slope').value()
        param_dict['auto_init_E0'] = ting_params.child('Auto Init E0').value()
        param_dict['E0'] = ting_params.child('Init E0').value()
        param_dict['tc'] = ting_params.child('Init tc').value()
        param_dict['fluid_exp'] = ting_params.child('Init Fluid. Exp.').value()
        param_dict['f0'] = ting_params.child('Init f0').value() / 1e9 #nN
        param_dict['vdrag'] = ting_params.child('Viscous Drag').value() / 1e3 #N/m·s
        param_dict['model_type'] = ting_params.child('Model Type').value()
        param_dict['smoothing_win'] = ting_params.child('Smoothing Window').value()
        param_dict['contact_offset'] = ting_params.child('Contact Offset').value() / 1e6 #um
    
    return param_dict