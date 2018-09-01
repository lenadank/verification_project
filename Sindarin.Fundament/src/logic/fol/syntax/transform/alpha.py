# encoding=utf-8
from pattern.collection.basics import DictionaryWithAdd
from pattern.mixins.attributes import WithMixIn

from logic.fol import FolFormula, Identifier



class AlphaRenaming(WithMixIn):
    
    class NS(object): pass
    
    def __init__(self):
        self.binders = [FolFormula.FORALL, FolFormula.EXISTS]

    def __call__(self, t, bound_vars=DictionaryWithAdd()):
        r = t.root
        if r in self.binders:
            v = [n.root for n in t.subtrees[:-1]]
            bound_vars = bound_vars + {x: self._mkuniq(x) for x in v}
        else:
            t.root = bound_vars.get(r, r)
        for x in t.subtrees: self(x, bound_vars)
        return t
    
    def _mkuniq(self, identifier):
        return Identifier(identifier.literal, identifier.kind,
                          ns=self.NS())




if __name__ == '__main__':
    from logic.fol.syntax.parser import FolFormulaParser
    L = FolFormulaParser()
    phi = L * "P(Q(x)) -> R(x)"
    phi.subtrees[1] = phi
    AlphaRenaming()(phi)
    