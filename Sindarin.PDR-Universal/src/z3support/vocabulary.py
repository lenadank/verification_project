'''
Created on Oct 7, 2013

@author: corwin
'''

from z3 import *  # @UnusedWildImport
from z3support import get_id
from pattern.mixins.promote import SimplisticPromoteMixIn
from z3 import is_func_decl



class Z3Alphabet(list):
    
    def dup(self, suffix):
        return type(self)(self._dup_symbol(symbol, suffix) for symbol in self)
        
    @classmethod
    def _dup_symbol(cls, symbol, suffix):
        if is_func_decl(symbol):
            args = [symbol.domain(i) for i in xrange(symbol.arity())]
            name = symbol.name()
            return Function(name + suffix, *(args + [symbol.range()]))
        elif is_const(symbol):
            name = symbol.decl().name()
            return Const(name + suffix, symbol.sort())



class Z3Renaming(object):
    
    def __init__(self, from_alphabet, to_alphabet):
        self.from_alphabet = from_alphabet
        self.to_alphabet = to_alphabet
        self.d = {get_id(f): t for f,t in zip(self.from_alphabet, self.to_alphabet)}
        
    def __call__(self, term):
        if is_func_decl(term):
            term_prime = self.d.get(get_id(term), term)
            #print self.d
            #print term, "--->", term_prime
            return term_prime
        if is_quantifier(term):
            vars0 = [ Const(term.var_name(i), term.var_sort(i)) for i in xrange(term.num_vars())]    
            vars0.reverse()
            b = substitute_vars(term.body(), *vars0)
            body = self(b)
            if term.is_forall():
                return ForAll(vars0, body)
            else:  # assume 'exists'
                return Exists(vars0, body)
        else:
            chs = [self(ch) for ch in term.children()]
            if len(chs) == 0:
                return self.d.get(get_id(term), term)
            else:
                if is_and(term):
                    return And(chs)
                elif is_or(term):
                    return Or(chs)
                else:
                    r = term.decl()
                    try:
                        r = self.d[get_id(r)]
                    except KeyError: pass
                    return r(chs)
            return term
                       
        
        
class Z3TwoVocabulary(list, SimplisticPromoteMixIn):
    """
    Hosts a list of tuples of the form [(a0,a), (b0,b), ...]
    """
    
    @property
    def past(self):
        return Z3Alphabet(x0 for x0,_ in self)
    
    @property
    def present(self):
        return Z3Alphabet(x for _,x in self)
    
    def rename_past_tense(self, term):
        return Z3Renaming(self.present, self.past)(term)



if __name__ == '__main__':
    a = Int("a")
    f = Function('f', IntSort(), IntSort())
    
    sigma = Z3Alphabet([a, f])
    sigma0 = sigma.dup('0')
    
    phi = f(a)
    print phi
    
    print Z3Renaming(sigma, sigma0)(phi)
