# encoding=utf-8

from logic.smt.smtlib.input import SchemeExpression
from pattern.collection.basics import OneToMany
from logic.fol.semantics.structure import FolStructure
from logic.fol.syntax.formula import FolSignature



class YicesOutputFormat(object):
    """
    Parser class for Yices output structure.
    Common usage:
    YicesOutputFormat()(" ... ") --> FolStructure
    """
    
    def __init__(self, signature=None):
        self.signature = signature or FolSignature()
    
    def __call__(self, textual_output):
        return self.data_as_structure(self.data_of_output(textual_output))

    def expressions(self, textual_output):
        return [SchemeExpression.parse(x.strip())
                for x in textual_output.splitlines() if x.startswith("(")]
        
    def semantics(self, expr):
        I = OneToMany().of(dict)
        if expr.root == '=':
            lhs, rhs = expr.subtrees
            value = str(rhs)
            arity = len(lhs.subtrees)
            if arity == 0:            
                I[lhs.root] = value
            elif arity == 1:
                I[lhs.root][lhs.subtrees[0].root] = value
            else:
                I[lhs.root][tuple(s.root for s in lhs.subtrees)] = value

        return I
    
    def join_semantics(self, list_of_semantics):
        I = OneToMany().of(dict)
        for el in list_of_semantics: I.update(el)
        return I
    
    def data_of_output(self, textual_output):
        exprs = self.expressions(textual_output)
        return self.join_semantics(self.semantics(x) for x in exprs)
    
    def value_transform(self, value):
        f = self.value_transform
        if isinstance(value, tuple):
            return tuple(f(x) for x in value)
        elif isinstance(value, dict):
            return dict((f(k), f(v)) for k,v in value.iteritems())
        elif isinstance(value, str) and len(value) and (value[0].isdigit() or value[0] in '+-.'):
            if "/" in value:
                nom, denom = value.split("/")
                return float(nom) / float(denom)
            else:
                if '.' in value:
                    return float(value)
                else:
                    return int(value)
        else:
            return value
            
    def key_transform(self, key):
        for s in self.signature.symbols:
            if s == key or s.mnemonic == key: return s
        return key
    
    def data_as_structure(self, semantics):
        fk, fv = self.key_transform, self.value_transform
        I = dict((fk(k), fv(v)) for k,v in semantics.iteritems())
        return FolStructure(domain=[], interpretation=I)
    

    

if __name__ == '__main__':
    YICES_OUTPUT = """sat

MODEL
(= y 0)
(= z 4330127018922193/5000000000000000)
(= x 4330127018922193/5000000000000000)
--- sin ---
(= (sin 60) 4330127018922193/5000000000000000)
no default
----
"""
    
    y = YicesOutputFormat()
    exprs = y.expressions(YICES_OUTPUT)
    for e in exprs:
        print y.semantics(e)
    print exprs
    print y(YICES_OUTPUT)
    