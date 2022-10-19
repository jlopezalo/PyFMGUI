# This file contains code from the PyQTGraph github repository
# https://github.com/pyqtgraph/pyqtgraph/blob/master/pyqtgraph/examples/ExampleApp.py

from io import StringIO
from contextlib import redirect_stdout
import PyQt5
from pyqtgraph.Qt import QtGui, QtWidgets
import traceback
from pyafmgui.widgets.python_highlighter import PythonHighlighter
from pyafmgui.widgets.macro_example import macro_example

# Libraries to be used in the macros
# we import them here just to make sure
# they are frozen by PyInstaller.
import numpy
import pandas
import matplotlib

class MacroWidget(QtGui.QWidget):
    def __init__(self, session):
        QtGui.QWidget.__init__(self)
        self.session = session
        self.session.macro_widget = self
        self.layout = QtWidgets.QVBoxLayout()
        self.layout_2 = QtWidgets.QHBoxLayout()
        self.layout_3 = QtWidgets.QHBoxLayout()
        self.setWindowTitle("PyQtGraph Examples")
        self.filename = QtWidgets.QLineEdit()
        self.codeBtn = QtWidgets.QPushButton('Run Code')
        self.loadBtn = QtWidgets.QPushButton('Load Code')
        self.codeView =  QtWidgets.QPlainTextEdit()
        self.outputView =  QtWidgets.QPlainTextEdit()
        self.outputView.setReadOnly(True)
        self.codeView.setFocus()
        self.hl = PythonHighlighter(self.codeView.document())
        self.layout_2.addWidget(self.filename)
        self.layout_2.addWidget(self.loadBtn)
        self.layout_2.addWidget(self.codeBtn)
        self.layout_3.addWidget(self.codeView)
        self.layout_3.addWidget(self.outputView)

        self.layout.addLayout(self.layout_2)
        self.layout.addLayout(self.layout_3)

        self.setLayout(self.layout)

        self.resize(1000,500)
        self.show()

        self.oldText = self.codeView.toPlainText()
        self.loadBtn.clicked.connect(self.loadCodeFile)
        self.codeView.textChanged.connect(self.onTextChange)
        self.codeBtn.clicked.connect(self.runCode)

        self.loadCode()

        self.outputView.setPlainText('> When you print the output will be shown here...')
    
    def loadCodeFile(self):
        fname, _ = QtWidgets.QFileDialog.getOpenFileName(
        	self, 'Open file', './', "Python Files (*.py)"
        )
        return self.loadCode(fname)
    
    def loadCode(self, file_path=None):
        if file_path is None:
            code = macro_example
            self.codeView.setPlainText(code)
            self.filename.setText('macro_example')
        else:
            code = ""
            with open(file_path, 'r') as file:
                for line in file.readlines():
                    code += line
            self.codeView.setPlainText(code)
            self.filename.setText(file_path)

    def onTextChange(self):
        """
        textChanged fires when the highlighter is reassigned the same document.
        Prevent this from showing "run edited code" by checking for actual
        content change
        """
        newText = self.codeView.toPlainText()
        if newText != self.oldText:
            self.oldText = newText

    def runCode(self):
        buffer = StringIO()
        with redirect_stdout(buffer):
            try:
                exec(self.codeView.toPlainText(), {"pyafmsession":self.session})
            except Exception:
                traceback.print_exc(file=buffer)
        output = buffer.getvalue()
        self.outputView.setPlainText(f'> {output}')