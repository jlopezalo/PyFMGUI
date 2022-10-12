# Import logging and get global logger
import logging
logger = logging.getLogger()
# Import for multiprocessing
import concurrent.futures
# Get loadfile function from PyFMReader
from pyafmreader import loadfile
# Get constants
import pyafmgui.const as const

def load_single_file(filepath):
    try:
        file = loadfile(filepath)
        file_id = file.filemetadata['Entry_filename']
        file_type = file.filemetadata['file_type']
        if file.isFV and file_type in const.nanoscope_file_extensions:
            file.getpiezoimg()
        return (file_id, file)
    except Exception as error:
        logger.info(f'Failed to load {filepath} with error: {error}')

def loadfiles(session, filelist, progress_callback, range_callback, step_callback):
    files_to_load = [path for path in filelist if path not in session.loaded_files_paths]
    loaded_files = []
    count = 0
    with concurrent.futures.ProcessPoolExecutor() as executor:
        # loaded_files = executor.map(load_single_file, files_to_load)
        futures = [executor.submit(load_single_file, filepath) for filepath in files_to_load]
        for future in concurrent.futures.as_completed(futures):
            loaded_files.append(future.result())
            count+=1
            progress_callback.emit(count)
    # loaded_files = list(loaded_files)
    # Loop and save files in the session
    for file_id, file in loaded_files:
        session.loaded_files[file_id] = file
