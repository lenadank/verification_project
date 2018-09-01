
from PyQt4.QtCore import Qt, SIGNAL
from PyQt4.QtGui import QShortcut, QKeySequence, QAction, QMainWindow



class Shortcuts(list):
    
    def for_(self, widget):
        self.widget = widget
        return self

    def __getitem__(self, arg):
        s = Shortcut(self.widget, arg)
        self.append(s)
        return s
    
    
class Shortcut(object):

    def __init__(self, widget, *shortcut):
        self.qshortcut = QShortcut(QKeySequence(*shortcut), widget)
        if isinstance(widget, QMainWindow):
            self.qshortcut.setContext(Qt.ApplicationShortcut)
        else:
            self.qshortcut.setContext(Qt.WidgetShortcut)

    def __rshift__(self, functor):
        s = self.qshortcut
        s.connect(s, SIGNAL("activated()"), functor)


class Action(QAction):

    def __rshift__(self, func):
        self.connect(self, SIGNAL("triggered()"), func)

    def __getitem__(self, shortcut):
        self.setShortcut(QKeySequence(shortcut))
        return self