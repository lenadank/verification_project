# encoding=utf-8
from adt.tree.transform import TreeTransform
from adt.tree.transform.apply import TreeNodeRename
from logic.fol.syntax import Identifier
from logic.fol.syntax.transform.alpha import AlphaRenaming
from pattern.collection.basics import OrderedSet, Histogram
from logic.fol.syntax.formula import FolFormula
from logic.fol.semantics.extensions.sorts import FolManySortSignature, FolSorts



class FreshSymbolIntroduction(object):
    
    def __call__(self, phi, ctx=None):
        return TreeTransform([self.xform], dir=TreeTransform.BOTTOM_UP)(phi)
        
    def xform(self, phi):
        if phi.root == 'fresh' and phi.subtrees:
            symbols = phi.subtrees[:-1]
            if any(x.subtrees for x in symbols):
                raise ValueError, "invalid fresh symbols '%s'" % symbols
            symbols = [x.root for x in symbols]
            phi = phi.subtrees[-1]
            newscope = AlphaRenaming.NS()
            return TreeNodeRename({k: Identifier(k.literal, k.kind, k.mnemonic, ns=newscope)
                                   for k in symbols})( phi )
                                   

class RenumberLiterals(object):

    def __init__(self):
        self.histogram = Histogram()
        self.assigned = {}

    def __call__(self, phi):
        """
        Makes sure any two identifiers that are not equal (not __eq__(x,y))
        have distinct literals. Note: performs modification of formulas in-place.
        @param phi a FolFormula instance
          it may also be:
          * an Identifier, in which case the corresponding unique identifier is returned
          * a FolManySortSignature, in which case returns a *new* signature where all
            symbols are translated to unique ones
        """
        if isinstance(phi, FolFormula):
            symset = OrderedSet(node.root for node in phi.nodes if node.root.ns is not None)
            symdict = {sym: self.gen_uniq(sym) for sym in symset}
            return TreeNodeRename(symdict).inplace(phi)
        elif isinstance(phi, Identifier):
            sym = phi
            return self.gen_uniq(sym) if sym.ns is not None else sym
        elif isinstance(phi, FolManySortSignature):
            renamed_sorts = FolSorts({self(k): v 
                                      for k,v in phi.sorts.sorts.iteritems()})
            return FolManySortSignature.from_sorts(renamed_sorts)            
        else:
            raise TypeError, "expected identifier, formula, or signature; found '%s'" % (type(phi).__name__)
    
    def asnew(self, phi):
        phi = type(phi).reconstruct(phi)
        return self(phi)

    def gen_uniq(self, sym):
        hist = self.histogram
        
        g = self.assigned.get(sym)
        if g is not None: return g
        literal = sym.literal
        hist[literal] = i = hist[literal] + 1
        ssc = '$%s' % i
        #ssc = self.num_sscript(i)
        self.assigned[sym] = g = Identifier(literal + ssc, sym.kind)
        return g
    
    @classmethod
    def num_sscript(cls, n):
        tab = {ord(k): ord(v) for k,v in zip("0123456789", u"₀₁₂₃₄₅₆₇₈₉")}
        return unicode(n).translate(tab)
    
        
        
        
if __name__ == '__main__':
    from logic.fol.syntax.parser import FolFormulaParser
    L = FolFormulaParser()
    
    phi = L * "fresh(c, P(c) -> Q(c)) & ~fresh(c, P(c) -> Q(c))"
    
    xform = FreshSymbolIntroduction()
    print FreshSymbolIntroduction.renumber_literals(xform(phi))
    