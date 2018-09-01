
from PyQt4.QtCore import QObject, SIGNAL

class QtSync(QObject):
    
    def __init__(self, func):
        super(QtSync, self).__init__()
        self.connect(self, SIGNAL("invoked(PyQt_PyObject)"), 
                     lambda (a, kw): func(*a, **kw))
    
    def __call__(self, *a, **kw):
        self.emit(SIGNAL("invoked(PyQt_PyObject)"), (a,kw))


def qtsync(func):
    q = QtSync(func)
    def refunc(*a, **kw):
        q(*a, **kw)
    return refunc
