'''
Handling bound variables is especially tricky because they are supposed to
stay immune to syntactic substitutions occurring "from the outside".
Also, alpha-renaming should take place when substituting sub-formulas to make
sure a previously-free variable does not accidentally become bound as a result.

(This should perhaps be moved into logic.fol.syntax)
'''
from adt.tree.transform import TreeTransform

from logic.fol import Identifier
from logic.fol.syntax.transform.delta import DeltaReduction
from logic.fol.syntax.transform.alpha import AlphaRenaming



class Protection(object):
    
    def __init__(self):
        self.opaque = ['valid']  # identifiers whose sub-formulas should always remain immune to substitutions
        
    @property
    def protect(self):
        return TreeTransform([self._xform_protect])
    
    @property
    def unprotect(self):
        return TreeTransform([self._xform_unprotect])
    
    def _xform_protect(self, t):
        r = t.root
        if r in self.opaque:
            return type(t)(Identifier(self, 'opaque', ns=[t]))
    def _xform_unprotect(self, t):
        r = t.root
        if r == self:
            return r.ns[0]
        



class ProtectedDeltaReduction(DeltaReduction):
    
    class SeqCompose(object):
        def __init__(self, *funcs):
            self.funcs = funcs
        def __call__(self, x):
            for f in self.funcs: x = f(x)
            return x
    
    def __init__(self):
        super(ProtectedDeltaReduction, self).__init__()
        p = Protection()
        a = AlphaRenaming()
        self.tuning.global_.before = self.SeqCompose(p.protect, a)
        self.tuning.global_.after = p.unprotect
        self.tuning.local_.before = a
        #self.tuning.global_.before = a

