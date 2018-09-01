
from PyQt4.QtCore import QSettings, QByteArray
from PyQt4.QtGui import QMainWindow, QDockWidget



class MainWindowWithPersistentDocks(QMainWindow):
    
    SETTING_IDS = None
    
    class DockWidget(QDockWidget):    
        still_shown = False
        def closeEvent(self, event):
            # so that floating dock widgets' settings are saved
            if self.isFloating() and not event.spontaneous(): 
                self.still_shown = True
            else:
                self.still_shown = False
    
    def __init__(self, *a, **kw):
        super(MainWindowWithPersistentDocks, self).__init__(*a, **kw)
        self.floaters = []
        self.stateful_widgets = []
        self.setting_ids = self.SETTING_IDS

    def _qsettings(self):
        return QSettings(*self.setting_ids)
    
    def closeEvent(self, event):
        if self.setting_ids is not None:
            for d in self.floaters:
                if d.still_shown: d.show()
            settings = self._qsettings()
            settings.setValue("geometry", self.saveGeometry())
            settings.setValue("windowState", self.saveState(version=0))
            for widget in self.stateful_widgets:
                settings.setValue("state/"+widget.objectName(), widget.saveState())
            super(MainWindowWithPersistentDocks, self).closeEvent(event)
        
    def load(self):
        def ba(o):
            # To cope with different QString API levels
            if o is None: return QByteArray()
            if isinstance(o, QByteArray): return o
            return o.toByteArray()
        if self.setting_ids is not None:
            settings = self._qsettings()
            self.restoreGeometry(ba(settings.value("geometry")))
            self.restoreState(ba(settings.value("windowState")), version=0)
            for widget in self.stateful_widgets:
                widget.restoreState(settings.value("state/"+widget.objectName()).toByteArray())
