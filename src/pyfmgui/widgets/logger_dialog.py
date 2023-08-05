import sys

from PyQt5 import QtWidgets

import logging
logger = logging.getLogger()

class QTextEditLogger(logging.Handler):
    def __init__(self, parent):
        super().__init__()
        self.widget = QtWidgets.QPlainTextEdit(parent)
        self.widget.setReadOnly(True)

    def emit(self, record):
        msg = self.format(record)
        self.widget.appendPlainText(msg)


class LoggerDialog(QtWidgets.QDialog, QtWidgets.QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.logTextBox = QTextEditLogger(self)
        # You can format what is printed to text box
        self.logTextBox.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        logger.addHandler(self.logTextBox)
        # You can control the logging level
        logger.setLevel(logging.INFO)

        self._button = QtWidgets.QPushButton(self)
        self._button.setText('Export Logs')

        layout = QtWidgets.QVBoxLayout()
        # Add the new logging box widget to the layout
        layout.addWidget(self.logTextBox.widget)
        layout.addWidget(self._button)
        self.setLayout(layout)

        # Connect signal to slot
        self._button.clicked.connect(self.exportLogs)

    def exportLogs(self):
        name, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save File", '/', '.txt')
        with open(name, 'w') as file:
            text = self.logTextBox.widget.toPlainText()
            file.write(text)    