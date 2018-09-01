# encoding=utf-8
from logic.fol.syntax import Identifier
from logic.fol.syntax.formula import FolSignature



class FolWithEquality:
    
    class Signature:
        eq = Identifier('=', 'predicate')
        neq = Identifier(u'≠', 'predicate')
        
        formal = FolSignature([], [(eq, 2), (neq, 2)])
    
    eq = Signature.eq
    neq = Signature.neq
    
    STANDARD_INTERPRETATION = \
    {eq: lambda x,y: x==y,
     neq: lambda x,y: x!=y}
