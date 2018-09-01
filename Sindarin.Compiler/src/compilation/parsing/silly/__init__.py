
import re

from adt.tree import Tree
from collections import OrderedDict



class SillyLexer(object):
    
    TEXT = 1
    TOKEN = 2
    
    def __init__(self, token_regexp):
        self.token_re = re.compile(token_regexp)
        
    def __call__(self, input_text):
        t = self.token_re
        tokens = t.findall(input_text)
        fillers = t.split(input_text)
        
        for text, token in zip(fillers, tokens + [None]):
            if text:
                yield (self.TEXT, text)
            if token is not None:
                yield (self.TOKEN, token)



class SillyBlocker(object):
    
    def __init__(self, open_token, close_token):
        self.topen = open_token
        self.tclose = close_token
        
    def __call__(self, token_stream):
        bal = 0
        topen, tclose = self.topen, self.tclose
        bag = []
        for t in token_stream:
            if t == topen:
                bal += 1
            elif t == tclose:
                bal -= 1
            bag += [t]
            if bal == 0: 
                yield Tree(t, list(self(bag[1:-1])))
                bag = []
                
        if bal != 0:
            raise SyntaxError, "unbalanced '%s' and '%s'" % (self.topen, self.tclose)


