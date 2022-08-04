import keyword
import os
import re
from io import StringIO
from contextlib import redirect_stdout

import PyQt5
from pyqtgraph.Qt import QtGui, QtWidgets, QtCore
import pyqtgraph as pg
import traceback
from pyafmgui.widgets.macro_example import macro_example

QRegularExpression = QtCore.QRegularExpression

QFont = QtGui.QFont
QColor = QtGui.QColor
QTextCharFormat = QtGui.QTextCharFormat
QSyntaxHighlighter = QtGui.QSyntaxHighlighter

def charFormat(color, style='', background=None):
    """
    Return a QTextCharFormat with the given attributes.
    """
    _color = QColor()
    if type(color) is not str:
        _color.setRgb(color[0], color[1], color[2])
    else:
        _color.setNamedColor(color)

    _format = QTextCharFormat()
    _format.setForeground(_color)
    if 'bold' in style:
        _format.setFontWeight(QFont.Weight.Bold)
    if 'italic' in style:
        _format.setFontItalic(True)
    if background is not None:
        _format.setBackground(pg.mkColor(background))

    return _format

class DarkThemeColors:

    Red = "#F44336"
    Pink = "#F48FB1"
    Purple = "#CE93D8"
    DeepPurple = "#B39DDB"
    Indigo = "#9FA8DA"
    Blue = "#90CAF9"
    LightBlue = "#81D4FA"
    Cyan = "#80DEEA"
    Teal = "#80CBC4"
    Green = "#A5D6A7"
    LightGreen = "#C5E1A5"
    Lime = "#E6EE9C"
    Yellow = "#FFF59D"
    Amber = "#FFE082"
    Orange = "#FFCC80"
    DeepOrange = "#FFAB91"
    Brown = "#BCAAA4"
    Grey = "#EEEEEE"
    BlueGrey = "#B0BEC5"

DARK_STYLES = {
    'keyword': charFormat(DarkThemeColors.Blue, 'bold'),
    'operator': charFormat(DarkThemeColors.Red, 'bold'),
    'brace': charFormat(DarkThemeColors.Purple),
    'defclass': charFormat(DarkThemeColors.Indigo, 'bold'),
    'string': charFormat(DarkThemeColors.Amber),
    'string2': charFormat(DarkThemeColors.DeepPurple),
    'comment': charFormat(DarkThemeColors.Green, 'italic'),
    'self': charFormat(DarkThemeColors.Blue, 'bold'),
    'numbers': charFormat(DarkThemeColors.Teal),
}

class PythonHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for the Python language.
    """
    # Python keywords
    keywords = keyword.kwlist

    # Python operators
    operators = [
        r'=',
        # Comparison
        r'==', r'!=', r'<', r'<=', r'>', r'>=',
        # Arithmetic
        r'\+', r"-", r'\*', r'/', r'//', r'%', r'\*\*',
        # In-place
        r'\+=', r'-=', r'\*=', r'/=', r'\%=',
        # Bitwise
        r'\^', r'\|', r'&', r'~', r'>>', r'<<',
    ]

    # Python braces
    braces = [
        r'\{', r'\}', r'\(', r'\)', r'\[', r'\]',
    ]

    def __init__(self, document):
        super().__init__(document)

        # Multi-line strings (expression, flag, style)
        self.tri_single = (QRegularExpression("'''"), 1, 'string2')
        self.tri_double = (QRegularExpression('"""'), 2, 'string2')

        rules = []

        # Keyword, operator, and brace rules
        rules += [(r'\b%s\b' % w, 0, 'keyword')
                  for w in PythonHighlighter.keywords]
        rules += [(o, 0, 'operator')
                  for o in PythonHighlighter.operators]
        rules += [(b, 0, 'brace')
                  for b in PythonHighlighter.braces]

        # All other rules
        rules += [
            # 'self'
            (r'\bself\b', 0, 'self'),

            # 'def' followed by an identifier
            (r'\bdef\b\s*(\w+)', 1, 'defclass'),
            # 'class' followed by an identifier
            (r'\bclass\b\s*(\w+)', 1, 'defclass'),

            # Numeric literals
            (r'\b[+-]?[0-9]+[lL]?\b', 0, 'numbers'),
            (r'\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b', 0, 'numbers'),
            (r'\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b', 0, 'numbers'),

            # Double-quoted string, possibly containing escape sequences
            (r'"[^"\\]*(\\.[^"\\]*)*"', 0, 'string'),
            # Single-quoted string, possibly containing escape sequences
            (r"'[^'\\]*(\\.[^'\\]*)*'", 0, 'string'),

            # From '#' until a newline
            (r'#[^\n]*', 0, 'comment'),
        ]
        self.rules = rules
        self.searchText = None

    def highlightBlock(self, text):
        """Apply syntax highlighting to the given block of text.
        """
        # Do other syntax formatting
        rules = self.rules.copy()
        for expression, nth, format in rules:
            format = DARK_STYLES[format]

            for n, match in enumerate(re.finditer(expression, text)):
                if n < nth:
                    continue
                start = match.start()
                length = match.end() - start
                self.setFormat(start, length, format)

        self.applySearchHighlight(text)
        self.setCurrentBlockState(0)

        # Do multi-line strings
        in_multiline = self.match_multiline(text, *self.tri_single)
        if not in_multiline:
            in_multiline = self.match_multiline(text, *self.tri_double)

    def match_multiline(self, text, delimiter, in_state, style):
        """Do highlighting of multi-line strings. 
        
        =========== ==========================================================
        delimiter   (QRegularExpression) for triple-single-quotes or 
                    triple-double-quotes
        in_state    (int) to represent the corresponding state changes when 
                    inside those strings. Returns True if we're still inside a
                    multi-line string when this function is finished.
        style       (str) representation of the kind of style to use
        =========== ==========================================================
        """
        # If inside triple-single quotes, start at 0
        if self.previousBlockState() == in_state:
            start = 0
            add = 0
        # Otherwise, look for the delimiter on this line
        else:
            match = delimiter.match(text)
            start = match.capturedStart()
            # Move past this match
            add = match.capturedLength()

        # As long as there's a delimiter match on this line...
        while start >= 0:
            # Look for the ending delimiter
            match = delimiter.match(text, start + add)
            end = match.capturedEnd()
            # Ending delimiter on this line?
            if end >= add:
                length = end - start + add + match.capturedLength()
                self.setCurrentBlockState(0)
            # No; multi-line string
            else:
                self.setCurrentBlockState(in_state)
                length = len(text) - start + add
            # Apply formatting
            self.setFormat(start, length, self.styles[style])
            # Highlighting sits on top of this formatting
            # Look for the next match
            match = delimiter.match(text, start + length)
            start = match.capturedStart()

        self.applySearchHighlight(text)

        # Return True if still inside a multi-line string, False otherwise
        if self.currentBlockState() == in_state:
            return True
        else:
            return False

    def applySearchHighlight(self, text):
        if not self.searchText:
            return
        expr = f'(?i){self.searchText}'
        palette: QtGui.QPalette = app.palette()
        color = palette.highlight().color()
        fgndColor = palette.color(palette.ColorGroup.Current,
                                  palette.ColorRole.Text).name()
        style = charFormat(fgndColor, background=color.name())
        for match in re.finditer(expr, text):
            start = match.start()
            length = match.end() - start
            self.setFormat(start, length, style)

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
        # self.splitter.setSizes([250,750])

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