
from logic.fol.syntax.formula import FolFormula, FolSignature



class FolTheory(list):

    def __init__(self, *a, **kw):
        super(FolTheory, self).__init__(*a, **kw)
        self.signature = FolSignature()

    def with_signature(self, signature):
        self.signature = signature
        return self

    def extend(self, another):
        super(FolTheory, self).extend(another)
        if hasattr(another, 'signature'):
            self.signature |= another.signature

    def __iadd__(self, other):
        self.extend(other)
        return self

    def __add__(self, other):
        t = type(self)()
        t.extend(self)
        t.extend(other)
        return t

    def __str__(self):
        return "\n".join(" - %s" % x for x in self)
    
    @property
    def vocabulary(self):
        """
        Extract the actually used fragment of the signature.
        """
        return self.signature.used_fragment(self)

    def split(self, connective=FolFormula.AND):
        return FolTheory(part for formula in self 
                                for part in formula.split(connective))\
                    .with_signature(self.signature)

    def join(self, connective=FolFormula.AND, default_value=None):
        return FolFormula.join(connective, self, default_value)
    
    def conjunction(self):
        return self.join(default_value=True)
