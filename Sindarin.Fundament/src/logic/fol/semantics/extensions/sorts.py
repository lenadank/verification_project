# encoding=utf-8

import copy

from adt.tree import Tree
from adt.tree.build import TreeAssistant

from logic.fol import Identifier
from logic.fol.syntax.formula import FolSignature, FolFormula
from collections import namedtuple



class FolSorts(object):
    
    FUNC_SEP = u"→"
    PARAM_SEP = u"×"
    
    ANY_SORT = ['?']
    
    class FunctionType(namedtuple('FunctionType', "from_ to_")):
        """
        from_: (tuple) types of positional arguments, without names
        to_: (scalar) return type
        """
        def __repr__(self):
            return FolSorts.FUNC_SEP.join((FolSorts.PARAM_SEP.join(map(unicode, self.from_)), unicode(self.to_)))
        def __eq__(self, other):
            if isinstance(other, type(self)):
                # coerce to tuples before comparing
                return tuple(self.from_) == tuple(other.from_) and self.to_ == other.to_
            else:
                return super(FolSorts.FunctionType, self).__eq__(other)
        @classmethod
        def parse(cls, text):
            if isinstance(text, tuple): return cls(*text)
            try:
                from_,to_ = text.split(FolSorts.FUNC_SEP)
            except ValueError:
                raise ValueError, "invalid sort: %r" % text
            if from_:
                from_ = tuple(from_.split(FolSorts.PARAM_SEP))
            else:
                from_ = ()
            return cls(from_, to_)
    
    
    def __init__(self, sorts={}):
        self.sorts = {}
        self.update(sorts)
    
    def __repr__(self):
        return "  ".join("%s: %s" % (k, "/".join(repr(ft) for ft in v)) for k,v in self.sorts.iteritems())
    
    def __getitem__(self, symbol):
        return self.sorts[symbol]
    
    def __setitem__(self, symbol, sort_expr):
        self.sorts[symbol] = self._parse(sort_expr)
        
    def __contains__(self, symbol):
        return symbol in self.sorts
    
    def __or__(self, other_sorts):
        c = copy.copy(self)
        c.sorts.update(other_sorts.sorts)
        return c
    
    def update(self, more_sorts):
        if isinstance(more_sorts, FolSorts):
            more_sorts = more_sorts.sorts
        for k,v in more_sorts.iteritems():
            if isinstance(k, FolFormula) and not k.subtrees:
                k = k.root
            self.sorts[k] = self._parse(v) 
        
    def iterdefs(self):
        """Iterates over pairs of (symbol, (from,to))"""
        return ((x,sr) for x,v in self.sorts.iteritems() for sr in v)
    
    def set(self): #@ReservedAssignment
        return set(x
                   for v in self.sorts.itervalues()
                   for from_,to_ in v
                   for l in (from_,[to_])
                   for x in l if x != "")
    
    def fragment(self, symbols):
        c = type(self)()
        for s in symbols:
            try:
                c.sorts[s] = self.sorts[s]
            except KeyError:
                pass # untyped symbols will be untyped in result too
        return c
    
    def as_tree(self):
        ta = TreeAssistant.build
        t = Tree("")
        for x, (from_,to_) in self.iterdefs():
            d = ta((x, 
                    [(self.FUNC_SEP, 
                      [(self.PARAM_SEP, list(from_)),
                       to_])]))
            t.subtrees.append(d)
        return t
        
    def check(self, formula):
        r = formula.root
        s = [self.check(sub) for sub in formula.subtrees]
        if [x for x in s if x == "undefined"]: return "undefined"
        if r == '=':      # equality is special. TODO generalize
            if len(s) == 2 and s[0] == s[1]:
                return ''
            else:
                return 'undefined'
        elif r in self.sorts:
            for from_,to_ in self.sorts[r]:
                if tuple(s) == from_:
                    return to_
            else:
                return "undefined"
        else:
            return "any"
        
    def is_well_formed(self, formula):
        return self.check(formula) != "undefined"
        
    def _parse(self, text):
        if not (isinstance(text, list) or isinstance(text, tuple)) or isinstance(text, self.FunctionType):
            text = [text]
        return [self.FunctionType.parse(t) for t in text]
            
    def _parse_tree(self, tree):
        symbol = tree.root
        s = {symbol: []}
        for subtree in tree.subtrees:
            if subtree.root != self.FUNC_SEP:
                raise ValueError, ("in sort expression tree: "
                                   "expected '%s', found '%s'"
                                    % (self.FUNC_SEP, subtree.root))
            if len(subtree.subtrees) != 2:
                raise ValueError, ("in sort expression tree: "
                                   "'%s' should have 2 children, but has %d"
                                    % (self.FUNC_SEP, len(subtree.subtrees)))
            if subtree.subtrees[0].root != self.PARAM_SEP:
                raise ValueError, ("in sort expression tree: "
                                   "expected '%s', found '%s'"
                                    % (self.PARAM_SEP, subtree.subtrees[0].root))
            from_, to_ = (tuple(s.root for s in subtree.subtrees[0].subtrees),
                          subtree.subtrees[1].root)
            s[symbol].append((from_, to_))
        return type(self)(s)
    
    def ary(self, key, arity):
        return [ft for ft in self.sorts.get(key, [])
                if len(ft.from_) == arity]
    
    def returns(self, key, return_type):
        return [ft for ft in self.sorts.get(key, [])
                if ft.to_ == return_type]
        
    def is_const(self, key, of_sort=ANY_SORT):
        """ Convenience: returns nullary sort(s) associated with symbol."""
        return [x.to_ for x in self.ary(key, 0) if self._is_subtype(x.to_, of_sort)]

    def _is_subtype(self, a, b):
        if b is self.ANY_SORT: 
            return True
        elif isinstance(b, (tuple, list)):
            return a in b
        else:
            return a == b
    
    def __nonzero__(self):
        return len(self.sorts) > 0




class FolManySortSignature(FolSignature):
    
    def __init__(self, funcs=[], preds=[], sorts=FolSorts()):
        super(FolManySortSignature, self).__init__(funcs, preds)
        self.sorts = sorts or FolSorts()
        
    @classmethod
    def promote(cls, obj):
        if isinstance(obj, cls):
            return obj
        elif isinstance(obj, FolSignature):
            return cls(obj.funcs, obj.preds)
        else:
            raise TypeError, "can't promote '%s' to '%s'" % (type(obj).__name__, cls.__name__)
    
    def __repr__(self):
        return "%s f%r p%r %r" % (type(self).__name__, self.funcs, self.preds, self.sorts)
        
    def itersymbols(self):
        for symbol in super(FolManySortSignature, self).itersymbols():
            yield symbol
        for symbol in self.sorts.sorts.iterkeys():
            if isinstance(symbol, Identifier) and symbol.kind not in ['function', 'predicate']:
                yield symbol
        
    def used_fragment(self, theory):
        narrow = super(FolManySortSignature, self).used_fragment(theory)
        variables = set([s for phi in theory for s in self._symbols(phi) 
                         if isinstance(s, Identifier) and s.kind == 'variable'])
        symbols = narrow.symbols | variables
        narrow.sorts = FolSorts({k : v for k, v in self.sorts.sorts.iteritems() if k in symbols})
        return narrow
    
    def sort_of(self, symbol, arity=None):
        try:
            return self.sorts[symbol]
        except KeyError:
            if symbol.kind == 'function':
                if arity is None:
                    arities = (a for (f,a) in self.funcs if f==symbol)
                else:
                    arities = (arity,)
                return [ (("V",)*a, "V") for a in arities]
            elif symbol.kind == "predicate":
                if arity is None:
                    arities = (a for (p,a) in self.preds if p==symbol)
                else:
                    arities = (arity,)
                return [ (("V",)*a, "") for a in arities]
            elif symbol.kind == "variable":
                return [ ((), "V") ]
            else:
                raise ValueError, "'%s' has invalid kind '%s'" % (symbol, symbol.kind)

    def __ior__(self, other):
        self.update(other)
        return self

    def __or__(self, other):
        C = FolManySortSignature
        if isinstance(other, C):
            return C(set(self.funcs) | set(other.funcs),
                     set(self.preds) | set(other.preds),
                     self.sorts | other.sorts)
        else:
            return C(set(self.funcs) | set(other.funcs),
                     set(self.preds) | set(other.preds),
                     copy.deepcopy(self.sorts))
            
    def __ror__(self, other):
        return self | other
    
    def __sub__(self, other):
        C = FolManySortSignature
        return C(set(self.funcs) - set(other.funcs),
                 set(self.preds) - set(other.preds),
                 copy.deepcopy(self.sorts))

    def __rsub__(self, other):
        C = FolManySortSignature
        return C(set(other.funcs) - set(self.funcs),
                 set(other.preds) - set(self.preds),
                 copy.deepcopy(self.sorts))
    
    def update(self, other):
        super(FolManySortSignature, self).update(other)
        if isinstance(other, FolManySortSignature):
            self.sorts.update(other.sorts)
        
    @classmethod
    def from_sorts(cls, sorts):
        for s,(_,to) in sorts.iterdefs():
            assert isinstance(s, Identifier)
            if s.kind == '?':
                s.kind = 'function' if to else 'predicate'
        funcs = [(f,len(from_)) for f,(from_,_) in sorts.iterdefs() if f.kind == 'function']
        preds = [(p,len(from_)) for p,(from_,_) in sorts.iterdefs() if p.kind == 'predicate']
        return cls(funcs, preds, sorts)
