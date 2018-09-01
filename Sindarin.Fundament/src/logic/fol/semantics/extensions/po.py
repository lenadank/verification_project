# encoding=utf-8

from logic.fol import Identifier



class FolNaturalPartialOrder:
    
    lt = Identifier('<', 'predicate', 'lt')
    gt = Identifier('>', 'predicate', 'gt')
    
    le = Identifier(u'≤', 'predicate', 'le')
    ge = Identifier(u'≥', 'predicate', 'ge')

    STANDARD_INTERPRETATION = \
    {lt: lambda x,y: x < y,
     gt: lambda x,y: x > y,
     le: lambda x,y: x <= y,
     ge: lambda x,y: x >= y,
     }