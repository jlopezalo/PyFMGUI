import PyQt5
from pyqtgraph.Qt import QtWidgets, QtCore, QtGui
from pyqtgraph import TableWidget

import numpy as np

from pyafmgui.export import result_types, prepare_export_results, export_results

class ExportDialog(QtGui.QWidget):
    def __init__(self, session):
        super().__init__()

        self.session = session
        self.dirname = None
        self.results = None

        self.exportButton = QtWidgets.QPushButton()
        self.exportButton.setText('Export All Results')
        self.updateButton = QtWidgets.QPushButton()
        self.updateButton.setText('Update Table')
        
        self.exportButton.clicked.connect(self.doexport)
        self.updateButton.clicked.connect(self.update_table)

        self.table_preview = TableWidget(editable=False, sortable=True)

        self.results_cb = QtWidgets.QComboBox()
        self.results_cb.addItems(result_types)
        self.results_cb.currentIndexChanged.connect(self.update_table)

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

        self.layout_2 = QtWidgets.QHBoxLayout()
        self.layout_2.addWidget(self.updateButton)
        self.layout_2.addWidget(self.exportButton)

        gridlayout.addWidget(self.file_prefix_label, 0, 0, 1, 1)
        gridlayout.addWidget(self.file_prefix_text, 0, 1, 1, 2)
        gridlayout.addWidget(self.save_folder_label, 1, 0, 1, 1)
        gridlayout.addWidget(self.save_folder_text, 1, 1, 1, 2)
        gridlayout.addWidget(self.save_folder_bttn, 2, 2, 1, 1)
        gridlayout.addWidget(self.results_cb, 3, 0, 1, 2)
        gridlayout.addLayout(self.layout_2, 3, 2, 1, 1)

        self.layout.addLayout(gridlayout)
        self.layout.addWidget(self.table_preview)

        self.setLayout(self.layout)

        self.update_table()

    def get_save_folder(self):
        dirname = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Save Directory')
        if dirname != "" and dirname is not None:
            self.dirname = dirname
            self.save_folder_text.setText(self.dirname)
        
    def update_table(self):
        result_key = self.results_cb.currentText()
        self.results = prepare_export_results(self.session)
        if self.results[result_key] is None:
            self.table_preview.clear()
        else:
            self.table_preview.setData(self.results[result_key].to_dict('records'))
    
    def open_msg_box(self, message):
        dlg = QtWidgets.QMessageBox(self)
        dlg.setWindowTitle("Export Status")
        dlg.setText(message)
        dlg.exec()
    
    def doexport(self):
        self.file_prefix = self.file_prefix_text.toPlainText()
        if self.dirname and self.file_prefix:
            success_flag = export_results(self.results, self.dirname, self.file_prefix)
            if success_flag:
                self.open_msg_box("Export was successful!")
            else:
                self.open_msg_box("No results were found to export!")
        elif self.dirname is None:
            self.open_msg_box("Please provide a directory!")
        elif self.file_prefix == "":
            self.open_msg_box("Please provide a file prefix!")