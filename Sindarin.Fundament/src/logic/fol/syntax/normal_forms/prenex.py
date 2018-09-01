# encoding=utf-8
from logic.fol.syntax.formula import FolFormula
from adt.tree.transform import TreeTransform
from logic.fol.syntax.transform.alpha import AlphaRenaming



class PrenexNormalForm(object):
    """
    Converts a formula to PNF (Prenex Normal Form).
    In PNF, all the quantifiers occur on the left, i.e. at the top level
    or out-most level of the formula, before any connectives.
    """
    
    def __init__(self):
        self.instructions = \
            {FolFormula.NOT: ('invert',),
             FolFormula.AND: ('id', 'id'),
             FolFormula.OR: ('id', 'id'),
             FolFormula.IMPLIES: ('invert', 'id'),
             FolFormula.IFF: ('split',),
             FolFormula.FORALL: ('id', 'id'),
             FolFormula.EXISTS: ('id', 'id'),}
            
        self.quantifiers = [FolFormula.FORALL, FolFormula.EXISTS]
        
    def invert(self, quantifier):
        if quantifier == FolFormula.FORALL:
            return FolFormula.EXISTS
        elif quantifier == FolFormula.EXISTS:
            return FolFormula.FORALL
        else:
            raise ValueError, "not a quantifier: '%s'" % quantifier
        
    def __call__(self, formula):
        q = []
        def pull_out(t, op_prefix=(), q=q):
            """ Extracts quantifiers nested in (sub-)formula t. """
            r, s = t.root, t.subtrees
            if r in self.quantifiers:
                q += [self._apply_ops(op_prefix, type(t)(r, s[:-1]))]
            if r in self.instructions:
                ops = self.instructions[r]
                for x, op in zip(s, ops):
                    pull_out(x, op_prefix + (op,))
        def xform(t):
            r, s = t.root, t.subtrees
            if r in self.quantifiers:
                return s[-1]
        pull_out(formula)
        phi = TreeTransform([xform], recurse=True)(formula)
        for prefix in reversed(q):
            prefix.subtrees += [phi]
            phi = prefix
        return phi
    
    def _apply_ops(self, ops, q):
        for op in ops:
            if op == 'id':
                pass
            elif op == 'invert':
                q = type(q)(self.invert(q.root), q.subtrees)
            else:
                raise KeyError, "invalid quantifier op '%s'" % op
        return q



if __name__ == '__main__':
    from logic.fol.syntax.parser import FolFormulaParser
    L = FolFormulaParser()
    phi = L * "(forall x (forall y (P(x))) | ~ forall y (P(y))) -> forall y (Q(y))"
    phi = L * "forall u (exists a (R(u,a)) & exists a (S(u,a)) -> Q(a))"
    print phi
    psi = PrenexNormalForm()(AlphaRenaming()(phi))
    
    print psi
