# encoding=utf-8

import sys
from adt.tree import Tree
from adt.tree.paths import Path



class KMatrix(object):
    """
    A k-matrix is a matrix organized in rows where every row is represented
    as a k-tuple. The number of columns is, therefore, equal to k.
    """
    
    class Projection(object):
        
        def __init__(self, matrix, container):
            self.m = matrix
            self.container = container
    
        def column(self, index):
            return self.container(t[index] for t in self.m.rows)
        
        def columns(self, indices):
            return self.container(tuple(t[i] for i in indices)
                                  for t in self.m.rows)
        
        def all_columns(self):
            return [self.column(i) for i in xrange(self.m.k)]
        
        def all_pairs(self):
            return [self.columns(indices) for indices in self.all_pair_indices()]
        
        def all_pairs_indexed(self):
            return [(indices, self.columns(indices)) 
                    for indices in self.all_pair_indices()]
            
        def all_pair_indices(self):
            return [(i, j)
                    for i in xrange(self.m.k) for j in xrange(self.m.k) if i != j]

    def __init__(self, ktuples, k=0):
        self.rows = ktuples
        if len(ktuples) > 0:
            self.k = max(len(x) for x in ktuples)
            if k != 0 and self.k != k:
                raise ValueError, "found %d-tuples in matrix with k=%d" % (self.k, k)
        else:
            self.k = k
    
    def project(self, container=set):
        return self.Projection(self, container)



class HierarchicalTable(object):
    """
    Hierarchy of data elements. Hierarchical rows are represented as subtrees;
    each node contains a datum for a single column.
    """ 

    class Row(object):
        def __init__(self, key, title):
            self.key = key
            self.title = title
        def __repr__(self):
            return `self.key`
        
    class Policy(object):
        def added(self, ht, where):
            pass
        
    class DisplayPolicy(Policy):
        pass
    
    class IndexingPolicy(Policy):
        def find(self, ht, where, value):
            raise NotImplementedError

    class NoDisplayPolicy(DisplayPolicy):
        pass

    class WhenFilledDisplayPolicy(DisplayPolicy):
        def __init__(self, width):
            self.width = width
        def added(self, ht, where):
            datum = where.end.root
            if isinstance(datum, ht.Row) and datum.title is not None:
                w = len(where)
            else:
                w = len(where) - 1
            if w >= self.width:
                ht.display(where, ht.pending)
                ht.pending = []
            else:
                ht.pend(where)
    
    class NoIndexingPolicy(IndexingPolicy):
        def find(self, ht, whence, datum):
            for sub in whence.end.subtrees:
                if sub.root == datum:
                    return whence + [sub]
            return None
            
    class DictIndexingPolicy(IndexingPolicy):
        def added(self, ht, where):
            if len(where) >= 2:
                datum = where.end.root
                parent = where[-2]()
                if not hasattr(parent, '_ht_index'):
                    parent._ht_index = {}
                parent._ht_index[datum] = where[-1]
        def find(self, ht, whence, datum):
            node = whence.end
            if hasattr(node, '_ht_index'):
                n = node._ht_index.get(datum, None)
                if n is None:
                    return None
                else:
                    return whence + [n()]
            else:
                return None 
    
    def __init__(self, data=None):
        """
        @param data: data tree
        """
        if data is None:
            data = Tree(type(self).__name__) # value at root is quite meaningless
        self.data = data
        self.pending = []
        self.display_policy = self.DisplayPolicy()
        self.indexing_policy = self.NoIndexingPolicy()
        self.column_fmt = u"%-30s"
        self.column_sep = u" "
        self.width = 0

    def rootset(self):
        return Path([self.data])
    
    def add_entry(self, datum, whence=None):
        if whence is None: whence = self.rootset()
        sub = Tree(datum)
        whence.end.subtrees.append(sub)
        n = whence + [sub]
        self.display_policy.added(self, n)
        self.indexing_policy.added(self, n)
        return n
    
    def add_path(self, data_path, whence=None):
        if whence is None: whence = self.rootset()
        for datum in data_path:
            n = self.find_entry(datum, whence)
            if n is None:
                n = self.add_entry(datum, whence)
            whence = n
        return whence
    
    def updated(self, data_paths, whence=None):
        for data_path in data_paths:
            self.add_path(data_path, whence)
        return self
    
    def find_entry(self, datum, whence=None):
        return self.indexing_policy.find(self, whence, datum)
        
    def __iter__(self):
        return self.iterrows()
        
    def __len__(self):
        # @@@ not quite the most efficient way to achieve this...
        i = 0
        for _ in self: i += 1
        return i
        
    def iterrows(self, whence=None):
        if whence is None: whence = self.rootset()
        if whence.end is self.data:
            r = ()
        else:
            r = (whence.end.root, )
        if whence.end.subtrees:
            for sub in whence.end.subtrees:
                for subrow in self.iterrows(whence + [sub]):
                    yield r + subrow
        elif len(whence) >= self.width + 1:
            yield r
        
    def pend(self, where):
        self.pending.append(where)
    
    def display(self, whence=None, pending=[], out=sys.stdout):
        if whence is None: whence = self.rootset()
        if not whence.end.subtrees:
            if len(whence) > 1:
                lin = self._lin(whence)
                for pend in reversed(pending):
                    if whence.startswith(pend):
                        if len(pend) > 1:
                            plin = self._lin(pend)
                            lin[:len(plin)] = plin
                print >>out, self._fmt(lin)
        else:
            p = pending + [whence]
            for sub in whence.end.subtrees:
                self.display(whence + [sub], p, out=out)
                p = []
            
    def _lin(self, path):
        indent = [''] * (len(path)-2)
        datum = path.end.root
        if isinstance(datum, self.Row):
            if datum.title is None:
                suf = [datum.key]
            else:
                suf = [datum.key, datum.title]
        else:
            suf = [datum]
        return indent + suf

    def _fmt(self, linear_data):
        col = self.column_fmt
        sep = self.column_sep
        return sep.join(col % (x,) for x in linear_data)




if __name__ == "__main__":
    ht = HierarchicalTable()
    ht.display_policy = ht.WhenFilledDisplayPolicy(3)
    ht.indexing_policy = ht.DictIndexingPolicy()
    ht.column_fmt = "%-15s"
    ht.add_entry("world", ht.add_entry("hello"))
    ht.add_path(("hello", "world", "*"))
    ht.add_entry("mondo", ht.add_entry(u"ciao"))
    ht.add_path(("ciao", "mondo", "*"))
    ht.add_path(("ciao", "bambina", ''))
    print "~" * 40
    ht.display(ht.rootset())

    print ht.data
    print sorted(set(ht))
