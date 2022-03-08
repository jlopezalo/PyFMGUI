import PyQt5
from pyqtgraph.Qt import QtGui, QtWidgets

class CustomDialog(QtWidgets.QDialog):
    def __init__(self, mode):
        super().__init__()

        self.pbar_files = QtWidgets.QProgressBar(self)
        self.pbar_files.setValue(0)

        QBtn = QtWidgets.QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QtWidgets.QDialogButtonBox(QBtn)
        self.buttonBox.rejected.connect(self.reject)

        self.layout = QtWidgets.QVBoxLayout()
        self.message = QtWidgets.QLabel()
        self.layout.addWidget(self.message)
        self.layout.addWidget(self.pbar_files)

        if mode == "fileload":
            self.setWindowTitle("Loading Files")
        elif mode == "computing":
            self.setWindowTitle("Computing")
            self.pbar_curves = QtWidgets.QProgressBar(self)
            self.pbar_curves.setValue(0)
            self.layout.addWidget(self.pbar_curves)
        
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)
