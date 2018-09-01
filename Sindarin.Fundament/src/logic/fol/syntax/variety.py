# encoding=utf-8
from adt.tree.walk import RichTreeWalk
from logic.fol.syntax.formula import FolFormula, FolSignature
from logic.fol.syntax import Identifier
from logic.fol.syntax.theory import FolTheory
from logic.fol.semantics.extensions.sorts import FolManySortSignature, FolSorts
from logic.fol.semantics.structure import FolStructure



class FolRegister(object):
    
    UNDEF = Identifier("?", 'predicate')
    
    def __init__(self, subset_of_symbols):
        self.symbols = subset_of_symbols
        
    def blur(self, phi):
        reg = self
        s = self.symbols
        class FormulaWalk(RichTreeWalk.Visitor):
            def enter(self, subtree, prune=lambda:None):
                r = subtree.root
                if isinstance(r, Identifier) and \
                     r.kind in ['function', 'predicate'] and r not in reg.symbols:
                    prune()
                    return reg.UNDEF
                else:
                    return r
            def join(self, node, prefix, infix, postfix):
                known = [a for a in infix if a.root != reg.UNDEF]
                if len(known) ==  len(infix):
                    return type(node)(prefix, known)
                elif prefix == FolFormula.AND and len(known) == 1:
                        return known[0]
                else:
                    return type(node)(reg.UNDEF)

            def done(self, root, final):
                return final
            
        
        if isinstance(phi, FolFormula):
            return RichTreeWalk(FormulaWalk())(phi)
        elif isinstance(phi, FolTheory):
            sig = self.blur(phi.signature)
            t = (y for y in (self.blur(x) for x in phi) if y.root != self.UNDEF)
            return FolTheory(t).with_signature(sig)
        elif isinstance(phi, FolManySortSignature):
            return FolManySortSignature([(f,a) for f,a in phi.funcs if f in s],
                                        [(p,a) for p,a in phi.preds if p in s],
                                        self.blur(phi.sorts))
        elif isinstance(phi, FolSignature):
            return FolSignature([(f,a) for f,a in phi.funcs if f in s],
                                [(p,a) for p,a in phi.preds if p in s])
        elif isinstance(phi, FolSorts):
            return FolSorts(self.blur(phi.sorts))
        elif isinstance(phi, FolStructure):
            return FolStructure(domain=phi.domain, 
                                interpretation=self.blur(phi.interpretation))
        elif isinstance(phi, dict):
            return dict((sym, v) for sym,v in phi.iteritems()
                        if sym in self.symbols)
        else:
            raise TypeError, phi
        
        
        
if __name__ == '__main__':
    from logic.fol import FolSymbolic
    p = lambda x: Identifier(x, 'predicate')
    f = lambda x: Identifier(x, 'function')
    L = FolSymbolic.Language().with_(a=p('a'), b=f('b'), c=f('c'), d=f('d'))
    phi = L * "(a(b,c,d) | a(b,c,c)) & a(b,b,c)"
    print phi
    print FolRegister(set([p('a'), f('b'), f('c')])).blur(phi)