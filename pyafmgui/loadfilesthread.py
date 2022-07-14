import PyQt5
from pyqtgraph.Qt import QtCore

from pyafmreader import loadfile

class LoadFilesThread(QtCore.QThread):
    _signal_id = QtCore.pyqtSignal(str)
    _signal_file_progress = QtCore.pyqtSignal(int)
    def __init__(self, session, filelist):
        super(LoadFilesThread, self).__init__()
        self.session = session
        self.filelist = filelist

    def run(self):
        for i, filepath in enumerate(self.filelist):
            if filepath in self.session.loaded_files_paths:
                continue
            self.session.loaded_files_paths.append(filepath)
            self._signal_id.emit(filepath)
            file = loadfile(filepath)
            file_id = file.filemetadata['Entry_filename']
            print(file_id)
            print(file.filemetadata)
            if file.isFV:
                file.getpiezoimg()
            self.session.loaded_files[file_id] = file
            self._signal_file_progress.emit(i)
