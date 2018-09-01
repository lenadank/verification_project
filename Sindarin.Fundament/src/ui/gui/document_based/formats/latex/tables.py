
if __name__ == '__main__':
    import sys, os
    sys.path.remove(os.getcwd())

from ui.gui.document_based.formats.latex import LaTeX, latex



class Table(LaTeX):
    
    class Field(object):
        def __init__(self, header):
            self.header = header
            self.justif = "c"
        def justify(self, j):
            self.justif = j
            return self
    
    class Style(object):
        pass
    
    def __init__(self):
        self.columns = []
        self.rows = []
        self.style = self.Style()
        self.style.env = "tabular"
        
    def to_latex(self):
        header = r"\begin{%s}{|%s|}" % (self.style.env, "|".join(c.justif for c in self.columns))
        footer = r"\end{%s}" % (self.style.env)
        head = [c.header for c in self.columns]
        return "\n".join([header] + [r"  \hline " + self._format_row(row) for row in [head] + self.rows] 
                         + [r"  \hline", footer])
            
    def _format_row(self, row):
        return " & ".join(latex(x) for x in row) + " \\\\"
    
    
    
if __name__ == '__main__':
    t = Table()
    t.columns = [Table.Field("a"), Table.Field("b"), Table.Field("a+b")]
    t.rows = [[x,y,x+y] for x in [1,2,3] for y in [3,4]]
    
    print t.to_latex()