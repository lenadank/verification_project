# encoding=utf-8

from adt.tree import Tree
from pattern.collection.basics import Cabinet, ListWithAdd
from pattern.mixins.attributes import WithMixIn
from adt.tree.transform.apply import ApplyTo



class TreeBlocker(object):
    
    class TaggedYX(tuple, WithMixIn): pass
    
    def __init__(self):
        self.yx_func = lambda (y,x): (y,x)
        self.tok_func = lambda x: x
        
    def with_yx(self, yx_extract_func):
        self.yx_func = lambda tok: self.TaggedYX(yx_extract_func(tok)).with_(tok=tok)
        self.tok_func = lambda x: x.tok
        return self
        
    def __call__(self, tokens):
        yxs = map(self.yx_func, tokens)
        tr = self._lay_out_tuples(yxs)
        return ApplyTo(nodes=lambda l: map(self.tok_func, l) if isinstance(l, list) else l).inplace(tr)
    
    def _lay_out_tuples(self, yxs):
        """
        For every 
        
        @param yxs: list of tuples (row,col)
        """
        
        def parent_of((row, col)):
            """ parent((row,col), (row',col')) <=> (row',col') in heads
               row' < row 
             & col' < col & forall i. row' < i < row & j < col -> (i,j) not in yxs
            """
            row_ = row - 1
            while row_ >= min(heads):
                if row_ in heads:
                    col_ = heads[row_]
                    if col_ < col:
                        return (row_, col_)
                row_ -= 1
            return None
            
        by_row = Cabinet().of(ListWithAdd).with_key(lambda x: x[0], Cabinet.SINGULAR).updated(yxs)
        heads = {row: cols[0][1] for row, cols in by_row.iteritems()}
        
        t = Tree(u'§')
        nodes = {None: t}
        for _, lin in sorted(by_row.iteritems()):
            nodes[lin[0]] = s = Tree(lin)
            nodes[parent_of(lin[0])].subtrees += [s]
        
        return t
        
        
        
if __name__ == '__main__':
    yxs = [(1, 1), (1, 4), (2, 3), (2, 5), (2, 9), (3, 3), (3, 4), (5, 1), (5, 5), (6, 3), (7, 6)]
    b = TreeBlocker()
    print b._lay_out_tuples(yxs)
    