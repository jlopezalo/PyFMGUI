import PyQt5
from pyqtgraph.Qt import QtWidgets, QtCore

class ExportDialog(QtWidgets.QDialog):
    def __init__(self, session):
        super().__init__()

        self.session = session
        self.dirname = None

        QBtn = QtWidgets.QDialogButtonBox.StandardButton.Ok|QtWidgets.QDialogButtonBox.StandardButton.Cancel

        self.buttonBox = QtWidgets.QDialogButtonBox(QBtn)
        self.buttonBox.rejected.connect(self.reject)
        self.buttonBox.accepted.connect(self.doexport)

        self.layout = QtWidgets.QVBoxLayout()

        gridlayout = QtWidgets.QGridLayout()
        self.file_prefix_label = QtWidgets.QLabel("File Prefix")
        self.file_prefix_text = QtWidgets.QTextEdit()
        self.file_prefix_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.file_prefix_label.setMaximumWidth(150)
        self.file_prefix_text.setMaximumHeight(40)

        self.save_folder_label = QtWidgets.QLabel("Save Folder")
        self.save_folder_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignRight | QtCore.Qt.AlignmentFlag.AlignVCenter)
        self.save_folder_label.setMaximumWidth(150)
        self.save_folder_text = QtWidgets.QTextEdit()
        self.save_folder_text.setMaximumHeight(40)
        self.save_folder_bttn = QtWidgets.QPushButton()
        self.save_folder_bttn.setText("Browse")
        self.save_folder_bttn.clicked.connect(self.get_save_folder)

        gridlayout.addWidget(self.file_prefix_label, 0, 0, 1, 1)
        gridlayout.addWidget(self.file_prefix_text, 0, 1, 1, 2)
        gridlayout.addWidget(self.save_folder_label, 1, 0, 1, 1)
        gridlayout.addWidget(self.save_folder_text, 1, 1, 1, 2)
        gridlayout.addWidget(self.save_folder_bttn, 2, 2, 1, 1)

        self.layout.addLayout(gridlayout)
        self.layout.addWidget(self.buttonBox)

        self.setLayout(self.layout)

    def get_save_folder(self):
        dirname = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Save Directory')
        if dirname != "" and dirname is not None:
            self.dirname = dirname
            self.save_folder_text.setText(self.dirname)
    
    def doexport(self):
        self.file_prefix = self.file_prefix_text.toPlainText()
        if self.dirname and self.file_prefix:
            self.session.export_results(self.dirname, self.file_prefix)
            self.close()