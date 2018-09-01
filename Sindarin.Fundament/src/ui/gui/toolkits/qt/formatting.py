

from PyQt4.QtGui import QTextCharFormat, QFont, QColor



class PoorMansCss(object):
    
    class InvalidColor(ValueError):
        pass
    
    @classmethod
    def char_format(cls, css):
        f = QTextCharFormat()
        if 'color' in css: f.setForeground(cls.color(css['color']))
        if 'background-color' in css:
            f.setBackground(cls.color(css['background-color']))
        if 'background' in css:
            f.setBackground(cls.color(css['background']))
        if 'font-weight' in css:
            w = css['font-weight']
            if w == 'bold': f.setFontWeight(QFont.Bold)
            if w == 'normal': f.setFontWeight(QFont.Normal)
        return f
        
    @classmethod
    def color(cls, s):
        if s.startswith('#'):
            s = s[1:]
            if len(s) == 3:
                r, g, b = s[0]*2, s[1]*2, s[2]*2
            elif len(s) == 6:
                r, g, b = s[0:2], s[2:4], s[4:6]
            else:
                raise cls.InvalidColor(s)
            r, g, b = int(r,16), int(g,16), int(b,16)
            return QColor(r, g, b)
        else:
            raise cls.InvalidColor(s)
        

