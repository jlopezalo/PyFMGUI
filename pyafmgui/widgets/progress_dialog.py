# Import GUI framework
import PyQt5
from pyqtgraph.Qt import QtWidgets

class ProgressDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super(ProgressDialog, self).__init__(parent)
        self.init_gui()

    def init_gui(self):
        vBox = QtWidgets.QVBoxLayout()
        self.textLabel = QtWidgets.QLabel()
        self.pbar = QtWidgets.QProgressBar()
        # self.button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Cancel)

        vBox.addWidget(self.textLabel)
        vBox.addWidget(self.pbar)
        # vBox.addWidget(self.button_box)
        self.setLayout(vBox)
    
    def set_pbar_range(self, min, max):
        self.pbar.setRange(min, max)

    def set_pbar_value(self, val):
        self.pbar.setValue(val)

    def reset_pbar(self):
        self.pbar.setValue(0)

    def set_label_text(self, text):
        self.textLabel.setText(text)
    


