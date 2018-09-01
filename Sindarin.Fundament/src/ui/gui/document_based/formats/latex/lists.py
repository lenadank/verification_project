
from ui.gui.document_based.formats.latex import LaTeX, latex



class UnorderedList(LaTeX):
    
    def __init__(self, items=[]):
        self.items = items or []
        
    def to_latex(self):
        header = r"\begin{itemize}"
        footer = r"\end{itemize}"
        return "\n".join([header] + [self._format_item(item) for item in self.items] + [footer])
    
    def to_table(self):
        from tables import Table
        t = Table()
        t.columns.append(Table.Field("").justify("l"))
        t.rows.extend([x] for x in self.items)
        return t
    
    def _format_item(self, item):
        return r"\item %s" % (latex(item),)
    
