import PyQt5
from pyqtgraph.Qt import QtGui, QtWidgets, QtCore

class CustomDialog(QtWidgets.QDialog):
    def __init__(self, mode):
        super().__init__()

        self.files_counter = 0

        self.pbar_files = QtWidgets.QProgressBar(self)
        self.pbar_files.setValue(0)

        QBtn = QtWidgets.QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QtWidgets.QDialogButtonBox(QBtn)

        self.layout = QtWidgets.QVBoxLayout()
        self.label = QtWidgets.QLabel()
        self.layout.addWidget(self.label)
        self.layout.addWidget(self.pbar_files)

        if mode == "fileload":
            self.setWindowTitle("Loading Files")
        elif mode == "computing":
            self.setWindowTitle("Computing")
            self.curves_counter = 0
            self.pbar_curves = QtWidgets.QProgressBar(self)
            self.pbar_curves.setValue(0)
            self.layout.addWidget(self.pbar_curves)
        
        self.layout.addWidget(self.buttonBox)
        self.setLayout(self.layout)

    def update_files_pb(self):
        """Update by one step."""
        self.pbar_files.setValue(self.files_counter)
        self.files_counter += 1
        QtCore.QCoreApplication.processEvents()
    
    def update_curves_pb(self):
        """Update by one step."""
        self.pbar_curves.setValue(self.curves_counter)
        self.curves_counter += 1
        QtCore.QCoreApplication.processEvents()

    def set_label(self, text):
        """Update the label's text."""
        self.label.setText(text)
        QtCore.QCoreApplication.processEvents()

    def set_files_pb_range(self, range1, range2):
        """Set the minimum and the maximum."""
        self.pbar_files.setRange(range1, range2)
    
    def set_curves_pb_range(self, range1, range2):
        """Set the minimum and the maximum."""
        self.pbar_curves.setRange(range1, range2)

    def reset_files_pb(self):
        """Reset the progressbar to 0."""
        self.files_counter = 0
        self.pbar_files.reset()
        QtCore.QCoreApplication.processEvents()
    
    def reset_curves_pb(self):
        """Reset the progressbar to 0."""
        self.curves_counter = 0
        self.pbar_curves.reset()
        QtCore.QCoreApplication.processEvents()