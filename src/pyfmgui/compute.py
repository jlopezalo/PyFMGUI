# Import for multiprocessing
import concurrent.futures
import contextlib
from functools import partial
# Import logging and get global logger
import logging
logger = logging.getLogger()
# Import constants
import pyfmgui.const as cts
# Import predefined routines from PyFMRheo
from pyfmrheo.routines.HertzFit import doHertzFit
from pyfmrheo.routines.TingFit import doTingFit
from pyfmrheo.routines.PiezoCharacterization import doPiezoCharacterization
from pyfmrheo.routines.ViscousDragSteps import doViscousDragSteps
from pyfmrheo.routines.MicrorheologyFFT import doMicrorheologyFFT
from pyfmrheo.routines.MicrorheologySine import doMicrorheologySine

def prepare_map_fdc(file, params, curve_idx):
    try:
        # Do fdc preprocessing
        fdc_at_indx = file.getcurve(curve_idx)
        fdc_at_indx.preprocess_force_curve(params['def_sens'], params['height_channel'])
        if file.filemetadata['file_type'] in cts.jpk_file_extensions:
            fdc_at_indx.shift_height()
        return fdc_at_indx
    except Exception as error:
        return (file.filemetadata['Entry_filename'], curve_idx, error)

def analyze_fdc(param_dict, fdc):
    # Create map relating methods to compute routine
    method_routines = {
        "HertzFit":doHertzFit,
        "TingFit":doTingFit,
        "PiezoChar":doPiezoCharacterization,
        "VDrag":doViscousDragSteps,
        "Microrheo":doMicrorheologyFFT,
        "MicrorheoSine":doMicrorheologySine
    }
    # Process FDC with routine
    try:
        routine = method_routines.get(param_dict['method'])
        return (fdc.file_id, fdc.curve_index, routine(fdc, param_dict))
    except Exception as error:
        return (fdc.file_id, fdc.curve_index, error, 'error')

def get_method_to_session_vars(session):
    return {
        "HertzFit":session.hertz_fit_results,
        "TingFit":session.ting_fit_results,
        "PiezoChar":session.piezo_char_results,
        "VDrag":session.vdrag_results,
        "Microrheo":session.microrheo_results,
        "MicrorheoSine":session.microrheo_results
    }

def clear_file_results(session, method, file_id):
    # Create map relating methods to where they should be saved in the session
    method_session_vars = get_method_to_session_vars(session)
    # Get var to save results in session
    session_save_var = method_session_vars.get(method)
    # Check if the method can be found
    if session_save_var is None:
        print(f"Session does not support {method}")
        return
    # Remove results for file
    if file_id in session_save_var:
        session_save_var.pop(file_id)

def save_file_results(session, params, file_results):
    # Create map relating methods to where they should be saved in the session
    method_session_vars = get_method_to_session_vars(session)
    # Get var to save results in session
    session_save_var = method_session_vars.get(params['method'])
    # Check if the method can be found
    if session_save_var is None:
        print(f"Session does not support {params['method']}")
        return
    # For each file save results
    for item in file_results:
        if len(item) > 3:
            file_id, curve_idx, analysis_result, _ = item
        else:
            file_id, curve_idx, analysis_result = item
        if file_id in session_save_var.keys():
            session_save_var[file_id].append((curve_idx, analysis_result))
        else:
            session_save_var[file_id] = [(curve_idx, analysis_result)]

def process_sfc(session, params, filedict, method, progress_callback, range_callback, step_callback):
    # Get curves to process for each file to process
    file_ids = filedict.keys()
    fdc_to_process = []
    step_callback.emit('Step 1/2: Preprocessing')
    for file_id in file_ids:
        # Get fileid
        file = filedict[file_id]
        # Clear
        clear_file_results(session, method, file_id)
        # Get current selected index
        curve_idx = session.current_curve_index
        try:
            # Get force distance curve at index
            fdc_at_indx = file.getcurve(curve_idx)
            # Do fdc preprocessing
            fdc_at_indx.preprocess_force_curve(params['def_sens'], params['height_channel'])
            if session.current_file.filemetadata['file_type'] in cts.jpk_file_extensions:
                fdc_at_indx.shift_height()
            fdc_to_process.append(fdc_at_indx)
        except Exception as error:
            logger.info(f"Failed to preprocess curve {curve_idx} in file {file.filemetadata['Entry_filename']}: {error}")
            continue
    # Process curves
    file_results = []
    count = 0
    range_callback.emit(len(fdc_to_process))
    step_callback.emit('Step 2/2: Computing')
    with concurrent.futures.ProcessPoolExecutor() as executor:
        futures = [executor.submit(analyze_fdc, params, fdc) for fdc in fdc_to_process]
        with contextlib.suppress(concurrent.futures.TimeoutError):
            for future in concurrent.futures.as_completed(futures):
                file_results.append(future.result())
                count+=1
                progress_callback.emit(count)
    # Save results
    save_file_results(session, params, file_results)

def process_maps(session, params, filedict, method, progress_callback, range_callback, step_callback):
    # Process files and curves
    for file_id, file in filedict.items():
        logger.info(f"Processing file: {file_id}")
        # Delete previous results for the file
        clear_file_results(session, method, file_id)
        # Prepare all fdc to process
        fdc_to_process = []
        errors = []
        # Prepare curves
        # Not sure if paralelization helps much, it is mostly limited
        # by file access (opening / closing file)
        raw_fdc_to_process = []
        count = 0
        nb_curves = file.filemetadata['Entry_tot_nb_curve']
        range_callback.emit(nb_curves)
        step_callback.emit('Step 1/2: Preprocessing')
        with concurrent.futures.ProcessPoolExecutor() as executor:
            futures = [executor.submit(prepare_map_fdc, file, params, curveidx) for curveidx in range(nb_curves)]
            with contextlib.suppress(concurrent.futures.TimeoutError):
                for future in concurrent.futures.as_completed(futures):
                    raw_fdc_to_process.append(future.result())
                    count+=1
                    progress_callback.emit(count)
        # Check for errors
        for item in raw_fdc_to_process:
            if type(item) is tuple:
                errors.append(item)
                logger.info(f"Failed to preprocess curve {item[1]} in file {item[0]}: {item[2]}")
            else: fdc_to_process.append(item)
        progress_callback.emit(0)
        # Process curves
        file_results = []
        count = 0
        range_callback.emit(len(fdc_to_process))
        step_callback.emit('Step 2/2: Computing')
        with concurrent.futures.ProcessPoolExecutor() as executor:
            # file_results = executor.map(partial(analyze_fdc, params), fdc_to_process)
            futures = [executor.submit(analyze_fdc, params, fdc) for fdc in fdc_to_process]
            with contextlib.suppress(concurrent.futures.TimeoutError):
                for future in concurrent.futures.as_completed(futures):
                    file_results.append(future.result())
                    count+=1
                    progress_callback.emit(count)
        file_results = list(file_results)
        for file_result in file_results:
            if 'error' in file_result:
                logger.info(f"Failed to process curve {file_result[1]} in file {file_result[0]}: {file_result[2]}")
        # Extend file results with the errors encountered in preprocessing
        file_results.extend(errors)
        # Save results
        save_file_results(session, params, file_results)
        # Reset pbar
        progress_callback.emit(0)

def compute(session, params, filedict, method, progress_callback, range_callback, step_callback):
    # Check if the file is a force map
    fv_flag = any(file.isFV for file in filedict.values())
    # Call the proper method to process the file
    if not params['compute_all_curves'] or not fv_flag:
        process_sfc(session, params, filedict, method, progress_callback, range_callback, step_callback)
    else:
        process_maps(session, params, filedict, method, progress_callback, range_callback, step_callback)
