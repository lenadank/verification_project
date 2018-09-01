
class Tree(object):
    
    def __init__(self, root, subtrees=None):
        self.root = root
        if subtrees is None:
            self.subtrees = []
        else:
            self.subtrees = subtrees
        
    def __eq__(self, other):
        if not isinstance(other, Tree): return NotImplemented
        return type(self) == type(other) and \
               (self.root, self.subtrees) == (other.root, other.subtrees)    
    
    def __ne__(self, other):
        return not (self == other)
    
    def __hash__(self):
        return hash((self.root, tuple(self.subtrees)))
    
    def __repr__(self):
        if self.subtrees:
            subreprs = ", ".join(`x` for x in self.subtrees)
            return "%r{%s}" % (self.root, subreprs)
        else:
            return `self.root`
    
    def clone(self):
        return self.reconstruct(self)
    
    @classmethod
    def reconstruct(cls, t):
        return cls(t.root, [cls.reconstruct(s) for s in t.subtrees])
        
    @property
    def nodes(self):
        return list(PreorderWalk(self))
    
    @property
    def leaves(self):
        return [n for n in PreorderWalk(self) if not n.subtrees]
    
    @property
    def terminals(self):
        """ @return a list of the values located at the leaf nodes. """
        return [n.root for n in self.leaves]

    @property
    def depth(self):
        """ Computes length of longest branch (iterative version). """
        stack = [(0, self)]
        max_depth = 0
        while stack:
            depth, top = stack[0]
            max_depth = max(depth, max_depth)
            stack[:1] = [(depth+1,x) for x in top.subtrees]
        return max_depth


# @deprecated: clients should use adt.tree.walk.RichTreeWalk instead
from walk import PreorderWalk, RichTreeWalk as Walk
Visitor = Walk.Visitor

