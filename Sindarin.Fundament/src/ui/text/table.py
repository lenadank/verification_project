'''
Created on Feb 9, 2012

@author: corwin
'''
import itertools



class Table(object):
    """
    Formats textual data in a tabular manner, preserving an equal number of
    characters for each row, and an equal number of characters for each cell in
    a column.
    """
    
    class Style():
        colsep = "  |  "
        rowfmt = " |  %s  |"
        has_hline = True
    
    def __init__(self):
        self.header = []
        self.data = []
        self.style = self.Style()
        
    def with_(self, data, header=None):
        if header is not None:
            self.header = header
        self.data.extend(data)
        return self
        
    @property
    def ncolumns(self):
        return max(itertools.chain([0],
                                   (len(row) for row in self.data)))
    
    def column_header(self, column_index):
        if column_index < len(self.header):
            return self.header[column_index]
        else:
            return ''
    
    def column_width(self, column_index):
        return max(itertools.chain([self.cell_width(self.column_header(column_index))],
                                    (self.cell_width(row[column_index]) for row in self.data)))
        
    def cell_width(self, value):
        lines = unicode(value)
        if lines:
            return max(len(l) for l in lines.splitlines())
        else:
            return 0
        
    def _justify(self, value, width):
        if isinstance(value, (int, float)):
            return unicode(value).rjust(width)
        else:
            return unicode(value).ljust(width)
        
    def __str__(self):
        return unicode(self)
        
    def __unicode__(self):
        n = self.ncolumns
        widths = [self.column_width(i) for i in xrange(n)]
        cells = ([self.header] if self.header else []) + self.data
        fmtd_cells = [[self._justify(cell, w) for cell, w in zip(row, widths)]
                      for row in cells]
        s = self.style
        hline = [" +" + "+".join('-' * (w + 4) for w in widths) + "+"] if s.has_hline else []
        return "\n".join(itertools.chain(hline,
                                         (row for row_cells in fmtd_cells 
                                               for row in self._row_fmt(row_cells, widths)),
                                         hline))
        
    def _row_fmt(self, cells, widths):
        t = side_by_side(cells)
        s = self.style
        return [s.rowfmt % s.colsep.join(self._justify(cell, w)
                                         for cell, w in zip(row, widths)) 
                for row in t.data]
    
    
    
def side_by_side(text_blocks, colsep="   "):
    text_lines = [unicode(t).splitlines() for t in text_blocks]
    nrows = 0 if not text_lines else max(len(lines) for lines in text_lines)
    transposed = [[(t[row] if row < len(t) else "") for t in text_lines]
                  for row in xrange(nrows)]
    
    t = Table()
    t.data = transposed
    t.style.colsep = colsep
    t.style.rowfmt = "%s"
    t.style.has_hline = False
    return t
    