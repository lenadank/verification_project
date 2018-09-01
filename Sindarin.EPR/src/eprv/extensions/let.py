'''
Provides the special quantifier 'let':
    let y=f(x) in P(y)
    
(this extension is not used at present)
'''

from logic.fol import FolFormula
from logic.fol.syntax import RepresentationForm
from adt.tree.transform import TreeTransform



class LetConstruct(RepresentationForm):
    
    LET = None # forward declaration
    
    def repr(self, (assgn, expr)):
        return '%s %s in (%s)' % (self, assgn, expr)
    
    @classmethod
    def to_quantified(cls, phi, quantifier_context):
        '''
        @param quantifier_context: either FolFormula.FORALL or FolFormula.EXISTS
        '''
        def xform(t):
            r, s = t.root, t.subtrees
            if r == cls.LET:
                _ = FolFormula
                if t.quantifier_context == _.FORALL:
                    return _(_.FORALL, [s[0].subtrees[0], 
                                _(_.IMPLIES, s)])
                elif t.quantifier_context == _.EXISTS:
                    return _(_.EXISTS, [s[0].subtrees[0], 
                                _(_.AND, s)])
                else:
                    raise ValueError, "invalid quantifier context '%s' for '%s'" % (t.quantifier_context, t)
        cls._mark_quantifier_context(phi, quantifier_context)
        return TreeTransform([xform])(phi)

    @classmethod
    def _mark_quantifier_context(cls, phi, quantifier_context):
        phi.quantifier_context = quantifier_context
        if phi.root.kind == 'quantifier': quantifier_context = phi.root
        for x in phi.subtrees:
            cls._mark_quantifier_context(x, quantifier_context)
    
LetConstruct.LET = LetConstruct('let', 'quantifier')


