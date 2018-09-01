# encoding=utf-8

from pattern.mixins.tuple import TupleMixin
from logic.fol.syntax import Identifier



class PredicateModifier(Identifier):
    
    def __init__(self, predicate_symbol, modifier):
        self.predicate_symbol = predicate_symbol
        self.modifier = modifier
        super(PredicateModifier, self).__init__(unicode(self), 'predicate')
        
    def tuple(self):
        return self.predicate_symbol, self.modifier
    
    def __repr__(self):
        return u"%r%s" % self.tuple()
    
    def __unicode__(self):
        return u"%s%s" % self.tuple()
    
    def __str__(self):
        return u"%s%s" % self.tuple()
    

class SpecificPredicateModifier(PredicateModifier):
    
    SPECIFIC = ""
    
    def __init__(self, predicate_symbol):
        super(SpecificPredicateModifier, self).__init__(predicate_symbol, 
                                                        self.SPECIFIC)


class Star(SpecificPredicateModifier):
    SPECIFIC = u"*"


class Plus(SpecificPredicateModifier):
    SPECIFIC = u"⁺"



if __name__ == '__main__':
    print "%s()" % Star("a")
    print "%s()" % Plus("b")

    print Star("a") == Star("a")
    print Star("a") == Plus("a")
