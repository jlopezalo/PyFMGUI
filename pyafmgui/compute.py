import PyQt5
import pyqtgraph.multiprocess as mp

import platform, multiprocessing

import pyafmgui.const as cts
from pyafmrheo.routines.HertzFit import doHertzFit
from pyafmrheo.routines.TingFit import doTingFit
from pyafmrheo.routines.PiezoCharacterization import doPiezoCharacterization
from pyafmrheo.routines.ViscousDragSteps import doViscousDragSteps
from pyafmrheo.routines.MicrorheologyFFT import doMicrorheologyFFT
from pyafmrheo.routines.MicrorheologySine import doMicrorheologySine
import traceback

def analyze_fdc(session, param_dict, fdc):
    # Do fdc preprocessing
    fdc.preprocess_force_curve(param_dict['def_sens'], param_dict['height_channel'])
    if session.current_file.filemetadata['file_type'] in cts.jpk_file_extensions:
        fdc.shift_height()
    if param_dict['method']  == "HertzFit": return doHertzFit(fdc, param_dict)
    elif param_dict['method'] == "TingFit": return doTingFit(fdc, param_dict)
    elif param_dict['method'] == "PiezoChar": return doPiezoCharacterization(fdc, param_dict)
    elif param_dict['method'] == "VDrag": return doViscousDragSteps(fdc, param_dict)
    elif param_dict['method'] == "Microrheo": return doMicrorheologyFFT(fdc, param_dict)
    elif param_dict['method'] == "MicrorheoSine": return doMicrorheologySine(fdc, param_dict)

def clear_file_results(session, method, file_id):
    if file_id in session.hertz_fit_results and method == "HertzFit":
        session.hertz_fit_results.pop(file_id)
    elif file_id in session.ting_fit_results and method == "TingFit":
        session.ting_fit_results.pop(file_id)
    elif file_id in session.piezo_char_results and method == "PiezoChar":
        session.piezo_char_results.pop(file_id)
    elif file_id in session.vdrag_results and method == "VDrag":
        session.vdrag_results.pop(file_id)
    elif file_id in session.microrheo_results and method in ["Microrheo", "MicrorheoSine"]:
        session.microrheo_results.pop(file_id)

def process_sfc(session, params, filedict, method):
    file_ids = filedict.keys()
    file_results = []
    with mp.Parallelize(tasks=file_ids, results=file_results, progressDialog='Processing Single Curves') as tasker:
        for file_id in tasker:
            try:
                # Get fileid
                file = filedict[file_id]
                # Clear
                clear_file_results(session, method, file_id)
                # Get current selected index
                curve_idx = session.current_curve_index
                # Get force distance curve at index
                fdc = file.getcurve(curve_idx)
                tasker.results.append((file_id, curve_idx, analyze_fdc(session, params, fdc)))
            except Exception:
                traceback.print_exc()
                tasker.results.append((file_id, curve_idx, None))
    for result in file_results:
        # Save results in the current session
        if params['method']  == "HertzFit":
            session.hertz_fit_results[result[0]] = [(result[1], result[2])]
        elif params['method']  == "TingFit":
            session.ting_fit_results[result[0]] = [(result[1], result[2])]
        elif params['method']  == "PiezoChar":
            session.piezo_char_results[result[0]] = [(result[1], result[2])]
        elif params['method']  == "VDrag":
            session.vdrag_results[result[0]] = [(result[1], result[2])]
        elif params['method'] in ["Microrheo", "MicrorheoSine"]:
            session.microrheo_results[result[0]] = [(result[1], result[2])]

def process_maps(session, params, filedict, method):
    # Process files and curves
    for file_id, file in filedict.items():
        # Delete previous results for the file
        clear_file_results(session, method, file_id)
        # Declare list to save file results
        file_results = []    
        # Get the total number of curves to process
        nb_curves = file.filemetadata['Entry_tot_nb_curve']
        # Define all curve indices
        curve_indices = list(range(nb_curves))
        # Process all curves in paralel
        with mp.Parallelize(tasks=curve_indices, results=file_results, progressDialog=f'Processing File: {file_id}') as tasker:
            for idx in tasker:
                try:
                    fdc = file.getcurve(idx)
                    tasker.results.append((idx, analyze_fdc(session, params, fdc)))
                except Exception:
                    traceback.print_exc()
                    tasker.results.append((idx, None))
        # Save results in the current session
        if params['method']  == "HertzFit":
            session.hertz_fit_results[file_id] = file_results
        elif params['method']  == "TingFit":
            session.ting_fit_results[file_id] = file_results
        elif params['method']  == "PiezoChar":
            session.piezo_char_results[file_id] = file_results
        elif params['method']  == "VDrag":
            session.vdrag_results[file_id] = file_results
        elif params['method'] in ["Microrheo", "MicrorheoSine"]:
            session.microrheo_results[file_id] = file_results

def compute(session, params, filedict, method):
    fv_flag = any(file.isFV for file in filedict.values())
    #if platform.system() == "Darwin":
    #    try:
    #        multiprocessing.set_start_method('spawn')
    #    except RuntimeError:
    #        pass
    if not params['compute_all_curves'] or not fv_flag:
        process_sfc(session, params, filedict, method)
    else:
        process_maps(session, params, filedict, method)
    