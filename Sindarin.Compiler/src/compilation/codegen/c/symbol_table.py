
from collections import namedtuple
from pattern.collection.basics import Cabinet


class Type(str): pass


class Symbol(namedtuple("Symbol", "name type")):
    pass


class FlatScope(Cabinet):
    
    def __init__(self):
        self.of(Symbol).with_key(lambda s: (s.name, s))
    
    
