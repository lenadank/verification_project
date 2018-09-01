
from adt.tree import Tree



class RegExp(Tree):
    
    NODE_CONCAT = "+"
    NODE_REPEAT = "*"
    NODE_CHOOSE = "|"

    class Letter(object):
        def __init__(self, symbol):
            self.symbol = symbol
        def __repr__(self):
            return str(self.symbol)

    def __repr__(self):
        if self.root is self.NODE_CONCAT:
            return u" ".join(`x` for x in self.subtrees)
        elif self.root is self.NODE_REPEAT:
            assert len(self.subtrees) == 1
            return u"(%r)*" % self.subtrees[0]
        elif self.root is self.NODE_CHOOSE:
            return u"(%s)" % u"|".join(`x` for x in self.subtrees)
        else:
            assert len(self.subtrees) == 0
            return `self.root`
        
    def split(self, separator=NODE_CONCAT):
        if self.root == separator:
            return self.subtrees
        else:
            return [self]

    @property
    def parts(self):
        return self.split()



class RegExpAssistant(object):
    
    @classmethod
    def build(cls, t):
        if isinstance(t, tuple):
            root, subtrees = t
            return RegExp(root, [cls.build(x) for x in subtrees])
        elif isinstance(t, list):
            return RegExp(RegExp.NODE_CONCAT, [cls.build(x) for x in t])
        elif isinstance(t, RegExp.Letter):
            return RegExp(t)
        else:
            return RegExp(RegExp.Letter(t))
        
        
        
Letter = RegExp.Letter  # for pickle
