import pyqtgraph.multiprocess as mp
import platform, multiprocessing
import traceback

from pyafmreader import loadfile
from .const import nanoscope_file_extensions

def loadfiles(session, filelist):
    if platform.system() == "Darwin":
        try:
            multiprocessing.set_start_method('spawn')
        except RuntimeError:
            pass
    loaded_files = []
    with mp.Parallelize(tasks=filelist, results=loaded_files, progressDialog='Loading Files') as tasker:
        for filepath in tasker:
            try:
                if filepath in session.loaded_files_paths:
                    continue
                file = loadfile(filepath)
                file_id = file.filemetadata['Entry_filename']
                file_type = file.filemetadata['file_type']
                if file.isFV and file_type in nanoscope_file_extensions:
                    file.getpiezoimg()
                tasker.results.append((file_id, file))
            except Exception:
                traceback.print_exc()
    
    for file_id, file in loaded_files:
        session.loaded_files[file_id] = file
