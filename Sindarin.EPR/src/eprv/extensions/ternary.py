#encoding=utf-8
'''
Support for terms with the ternary operator "C ? x : y"
(alternative notation: "ite(C, x, y)")
in terms of FO formulas.
Such formulas can always be rewritten as regular FO formulas.
E.g.
   P(C ? f(x) : z)   --->   ite(C, P(f(x)), P(z))
   
where ite is just the "if-then-else" connective defined using the primitive
connectives as
   ite(C, P, Q)  --->   C & P | ~C & Q
'''

from logic.fol import Identifier, FolFormula
from pattern.collection.basics import ListWithAdd
from adt.tree.transform import TreeTransform
from eprv.synopsis.declare import TypeInference



class TernaryOperator(object):
    
    class Signature:
        ter_op = Identifier('?:', 'macro')
        ite = Identifier('ite', 'connective')
        
    
    def __call__(self, phi, ctx=None):
        occurrences = ListWithAdd()
        self._collect_ternies(phi, occurrences)
        def xform(phi):
            _ = FolFormula
            for (atom, ter) in occurrences:
                if phi is atom:
                    if len(ter.subtrees) != 3:
                        raise ValueError, "invalid ternary expression: '%s'" % ter
                    cond, then_, else_ = ter.subtrees
                    phi = _(self.Signature.ite, [cond, 
                                                 self._choose(atom, ter, then_),
                                                 self._choose(atom, ter, else_)])
                    return self(phi)
        if occurrences:
            return TreeTransform([xform])(phi)
        else:
            return phi
    
    def _choose(self, atom, point_of_choice, choice):
        def xform(phi):
            if phi is point_of_choice: return choice
        return TreeTransform([xform])(atom)
    
    def _collect_ternies(self, phi, collection, containing_atom=None):
        r, s = phi.root, phi.subtrees
        if r.kind == 'predicate':
            containing_atom = phi
        elif r == self.Signature.ter_op and containing_atom:
            collection.add((containing_atom, phi))
        for x in s:
            self._collect_ternies(x, collection, containing_atom)
            
    def inspect_formula(self, phi, ctx=None):
        return self._rewrite(phi, self(phi))
        
    def _rewrite(self, phi, psi):
        phi.root, phi.subtrees = psi.root, psi.subtrees
        return phi



if __name__ == '__main__':
    from logic.fol.syntax.parser import FolFormulaParser
    L = FolFormulaParser()
    ti = TypeInference()
    samples = [ti(L * "P([?:](B, f(x), g(z)))"),
               ti(L * "P([?:](B, f([?:](C, x, y)), g(z)))"),
               ti(L * "forall u ( R([?:](B(u), x, y), [?:](C(u), y, z)) ) "),
               ti(L * "forall u ( P([?:](B(u), x, y)) & Q([?:](C(u), y, z)) ) "),
               ti(L * "P([?:](L([?:](E, a, b)), z, y))"),
               ti(L * "forall u ( P([?:](B(u), x, f([?:](L([?:](E, a, b)), z, y)))) & Q([?:](C(u), y, z)) ) ")]
    
    for sample in samples:
        print sample
        
        toe = TernaryOperator()
        print "--->  ", toe(sample)
        print