
from PyQt4.QtGui import QApplication, QTextEdit, QTextCursor, \
    QImageReader, QImage, QTextCharFormat, QBrush, QColor
from ui.gui.toolkits.qt.settings import MainWindowWithPersistentDocks



class FormattedText(unicode):
    def __init__(self, s='', css={}):
        super(FormattedText, self).__init__(s)
        self.css = css.copy()


class RichTextApp(QApplication):

    def __init__(self, *a):
        super(RichTextApp, self).__init__(*a)
        self.win = MainWindowWithPersistentDocks()
        self.win.setting_ids = ("IMDEA", "FOL.Synopsis")
        self.win.setWindowTitle("FOL Synopsis")

        self.text = QTextEdit(self.win)
        #self.put_some_text_in()

        self.win.setCentralWidget(self.text)
        #self.win.statusBar().show()
        
        self.win.load()
        
    def put_some_text_in(self):
        c = QTextCursor(self.text.document())
        c.insertText("sat")
        c.insertBlock()
        c.insertImage(self.load_an_image(), 'image')
        c.insertBlock()
        c.insertText("unsat")
        # Move back to head of document
        self.text.setTextCursor(QTextCursor(self.text.document()))
        
    def load_an_image(self):
        return QImageReader("/tmp/plot.svg").read()
        return QImageReader("/tmp/strawberry.gif").read()
        
    def css_like(self, d={}):
        qtcf = QTextCharFormat()
        for k,v in d.iteritems():
            if k == 'color':
                qtcf.setForeground(QBrush(QColor(v)))
        return qtcf
        
    def put_text_block(self, text):
        c = self.text.textCursor()

        if isinstance(text, FormattedText):
            c.setCharFormat(self.css_like(text.css))
            
        c.insertText(text)
        c.insertBlock()
        
    def put_image(self, image_data):
        c = self.text.textCursor()
        
        c.insertImage(self.load_image(image_data))#, 'image')
        c.insertBlock()
        
    def load_image(self, image_data):
        q = QImage(); q.loadFromData(image_data)
        return q
        
    def __call__(self):
        self.win.show()
        self.win.raise_()
        self.exec_()



if __name__ == '__main__':
    RichTextApp([])()
