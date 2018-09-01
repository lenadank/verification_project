# encoding=utf-8

from adt.tree.walk import PreorderWalk
from logic.fol.syntax.formula import FolSignature
from logic.fotc.syntax import PredicateModifier



class FotcSignature(FolSignature):
    
    def _symbols(self, phi):
        for x in PreorderWalk(phi):
            yield x.root
            if isinstance(x.root, PredicateModifier):
                yield x.root.predicate_symbol

