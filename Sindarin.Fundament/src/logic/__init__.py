"""
Symbolic Logic Package
"""


class Literal(object):
    """
    A literal is either an atomic clause or its negation.
    Positive literal: Literal(p)
    Negative literal: ~Literal(p)
    """
    
    def __init__(self, predicate):
        self.predicate = predicate
        self.neg = False
        
    def __invert__(self):
        n = Literal(self.predicate)
        n.neg = not self.neg
        return n
    
    def __repr__(self):
        if self.neg:
            sign = "~"
        else:
            sign = ""
        return "%s%r" % (sign, self.predicate)
    
    def __hash__(self):
        return hash(self.predicate)
    
    def __eq__(self, other):
        return (self.predicate, self.neg) == (other.predicate, other.neg)
