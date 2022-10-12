# Import for multiprocessing
import concurrent.futures
from functools import partial
# Import logging and get global logger
import logging
logger = logging.getLogger()
# Import constants
import pyafmgui.const as cts
# Import predefined routines from PyFMRheo
from pyafmrheo.routines.HertzFit import doHertzFit
from pyafmrheo.routines.TingFit import doTingFit
from pyafmrheo.routines.PiezoCharacterization import doPiezoCharacterization
from pyafmrheo.routines.ViscousDragSteps import doViscousDragSteps
from pyafmrheo.routines.MicrorheologyFFT import doMicrorheologyFFT
from pyafmrheo.routines.MicrorheologySine import doMicrorheologySine

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
        logger.info(f"Failed to process curve {fdc.curve_index} in file {fdc.file_id}: {error}")
        return (fdc.file_id, fdc.curve_index, error)

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
    for file_id, curve_idx, analysis_result in file_results:
        if file_id in session_save_var.keys():
            session_save_var[file_id].append((curve_idx, analysis_result))
        else:
            session_save_var[file_id] = [(curve_idx, analysis_result)]

def process_sfc(session, params, filedict, method, progress_callback):
    # Get curves to process for each file to process
    file_ids = filedict.keys()
    fdc_to_process = []
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
    with concurrent.futures.ProcessPoolExecutor() as executor:
        # file_results = executor.map(partial(analyze_fdc, params), fdc_to_process)
        futures = [executor.submit(analyze_fdc, params, fdc) for fdc in fdc_to_process]
        for future in concurrent.futures.as_completed(futures):
            file_results.append(future.result())
            count+=1
            progress_callback.emit(count)
    # file_results = list(file_results)
    # Save results
    save_file_results(session, params, file_results)

def process_maps(session, params, filedict, method, progress_callback):
    # Process files and curves
    count = 0
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
        with concurrent.futures.ProcessPoolExecutor() as executor:
            raw_fdc_to_process = executor.map(partial(prepare_map_fdc, file, params), range(file.filemetadata['Entry_tot_nb_curve']))
        # Check for errors
        raw_fdc_to_process = list(raw_fdc_to_process)
        for item in raw_fdc_to_process:
            if type(item) is tuple:
                errors.append(item)
                logger.info(f"Failed to preprocess curve {item[1]} in file {item[0]}: {item[2]}")
            else: fdc_to_process.append(item)
        # Process curves
        with concurrent.futures.ProcessPoolExecutor() as executor:
            file_results = executor.map(partial(analyze_fdc, params), fdc_to_process)
        file_results = list(file_results)
        # Extend file results with the errors encountered in preprocessing
        file_results.extend(errors)
        # Save results
        save_file_results(session, params, file_results)
        # Report progress to main thread
        count+=1
        progress_callback.emit(count)

def compute(session, params, filedict, method, progress_callback):
    # Check if the file is a force map
    fv_flag = any(file.isFV for file in filedict.values())
    # Call the proper method to process the file
    if not params['compute_all_curves'] or not fv_flag:
        process_sfc(session, params, filedict, method, progress_callback)
    else:
        process_maps(session, params, filedict, method, progress_callback)
