import PyQt5
from pyqtgraph.Qt import QtWidgets, QtCore, QtGui
from pyqtgraph import TableWidget

from pyafmgui.threading import Worker
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
        self.updateButton.clicked.connect(self.get_results)

        self.table_preview = TableWidget(editable=False, sortable=True)

        self.results_cb = QtWidgets.QComboBox()
        self.results_cb.addItems(result_types)
        self.results_cb.currentIndexChanged.connect(self.get_results)

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

        self.get_results()

    def get_save_folder(self):
        dirname = QtWidgets.QFileDialog.getExistingDirectory(self, 'Select Save Directory')
        if dirname != "" and dirname is not None:
            self.dirname = dirname
            self.save_folder_text.setText(self.dirname)
    
    def closeEvent(self, evnt):
        self.session.export_dialog = None
    
    def get_results(self):
        self.session.pbar_widget.reset_pbar()
        self.session.pbar_widget.set_label_text('Preparing Results for export...')
        self.session.pbar_widget.set_label_sub_text('')
        self.session.pbar_widget.show()
        self.thread = QtCore.QThread()
        self.worker = Worker(prepare_export_results, self.session)
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.signals.progress.connect(self.reportProgress)
        self.worker.signals.finished.connect(self.oncomplete) # Reset button
        self.worker.signals.range.connect(self.setPbarRange)
        self.thread.start()
    
    def setPbarRange(self, n):
        self.session.pbar_widget.set_pbar_range(0, n)

    def reportProgress(self, n):
        self.session.pbar_widget.set_pbar_value(n)
    
    def oncomplete(self):
        self.thread.terminate()
        self.session.pbar_widget.hide()
        self.session.pbar_widget.reset_pbar()
        self.update_table()
        
    def update_table(self):
        result_key = self.results_cb.currentText()
        self.results = self.session.prepared_results
        if self.results[result_key] is None:
            self.table_preview.clear()
        else:
            res = self.results[result_key].to_dict('records')
            if len(res) < 50:
                self.table_preview.setData(self.results[result_key].to_dict('records'))
            else:
                self.table_preview.setData(self.results[result_key].head(50).to_dict('records'))
                self.open_msg_box(f"Showing only first 50 out of {len(res)} results.")
    
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