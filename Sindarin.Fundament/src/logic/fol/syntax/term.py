
from logic.fol import Identifier, FolFormula
from pattern.collection.basics import ListWithAdd



class FolTerm(FolFormula):
    
    @classmethod
    def collect_ground(cls, formula):
        l = ListWithAdd()
        cls._collect_ground_into(formula, l)
        return l

    @classmethod
    def _collect_ground_into(cls, formula, container):
        r, s = formula.root, formula.subtrees
        under = all([cls._collect_ground_into(x, container) for x in s])
        if under and isinstance(r, Identifier) and r.kind == 'function':
            if under:
                container.add(formula)
            return True
        else:
            return False