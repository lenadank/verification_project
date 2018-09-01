# encoding=utf-8
"""
Standard arithmetics.
"""

import operator    
import collections

from pattern.collection.basics import IdSet
from pattern.quantifier import forall

from adt.tree.walk import RichTreeWalk

from logic.fol import Identifier
from logic.fol.semantics.extensions.sorts import FolSorts, FolManySortSignature
from logic.fol.semantics.extensions.po import FolNaturalPartialOrder
from logic.fol.syntax.formula import FolFormula
from logic.fol.semantics.structure import FolStructure
from logic.fol.semantics.extensions.equality import FolWithEquality
from logic.fol.syntax.theory import FolTheory



class FolIntegerArithmetic(FolNaturalPartialOrder):
    """
    Signature for basic arithmetic.
    """

    add = Identifier('+', 'function')
    sub = Identifier(u'−', 'function')
    mul = Identifier(u'⋅', 'function')
    div = Identifier('/', 'function')
    neg = Identifier('-', 'function')
    
    sorts = FolSorts({add: u"Z×Z→Z", mul: u"Z×Z→Z", sub: u"Z×Z→Z", div: u"Z×Z→Z",
                      neg: u"Z→Z", 
                      FolNaturalPartialOrder.gt: u"Z×Z→",
                      FolNaturalPartialOrder.lt: u"Z×Z→",
                      FolNaturalPartialOrder.ge: u"Z×Z→",
                      FolNaturalPartialOrder.le: u"Z×Z→"})
    
    formal = FolManySortSignature.from_sorts(sorts)

    STANDARD_INTERPRETATION = \
    {add : operator.add, sub: lambda a,b=None: -a if b is None else a-b, 
     u'−': operator.sub,
     mul: operator.mul, u'*': operator.mul,
     div: operator.div # integer division
     }

    FolFormula.INFIXES += [mul, sub]

    class Sugar:
        """FolSymbolic mix-in"""
        def _b(self, root, subs):
            return type(self)(root, [self.promote(x) for x in subs])
        def __add__(self, other):   return self.build(self._.add, [self, other])
        def __radd__(self, other):  return self.build(self._.add, [other, self])
        def __sub__(self, other):   return self.build(self._.sub, [self, other])
        def __rsub__(self, other):  return self.build(self._.sub, [other, self])
        def __mul__(self, other):   return self.build(self._.mul, [self, other])
        def __rmul__(self, other):  return self.build(self._.mul, [other, self])
        def __neg__(self):          return self.build(self._.neg, [self])
        # Naturally should be part of FolWithEquality
        def __eq__(self, other):    return self.build(self._.eq, [self, other])
        # Naturally should be part of FolNaturalPartialOrder
        def __gt__(self, other):    return self.build(self._.gt, [self, other])
        def __lt__(self, other):    return self.build(self._.lt, [self, other])
        def __ge__(self, other):    return self.build(self._.ge, [self, other])
        def __le__(self, other):    return self.build(self._.le, [self, other])



FolIntegerArithmetic.Sugar._ = FolIntegerArithmetic






class NumericalCalculator(object):
    """
    Computes the concrete value of arithmetic expressions by applying the 
    standard interpretation of the operators.
    """
    
    STANDARD_INTERPRETATION = \
    {'+': operator.add, '-': lambda a,b=None: -a if b is None else a-b, 
     u'−': operator.sub,
     '*': operator.mul, u'⋅': operator.mul,
     '/': operator.truediv,
     }
    
    class Interpretation(dict):
        native_types = ()
        def with_native_types(self, native_types):
            self.native_types = native_types
            return self
        def _identifier_type(self, identifier):
            if isinstance(identifier, Identifier):
                return type(identifier.literal)
            else:
                return None
        def __contains__(self, key):
            return type(key) in self.native_types or \
                    self._identifier_type(key) in self.native_types or self.has_key(key)
        def __getitem__(self, key):
            if type(key) in self.native_types:
                return key
            elif self._identifier_type(key) in self.native_types:
                return key.literal
            else:
                return self.get(key)
    
    def __init__(self):
        self.I = (self.Interpretation(self.STANDARD_INTERPRETATION)
                  .with_native_types((int, float)))
    
    def with_native_types(self, native_types):
        self.I = self.I.with_native_types(native_types)
        return self
    
    def __call__(self, term, transient_values=None):
        if transient_values is not None:
            self.I.update(transient_values)
        m = FolStructure(domain=[], interpretation=self.I)
        return m.evaluate(term)

    def unknowns(self, formula):
        return set(n.root for n in formula.nodes if n.root not in self.I)

    def mark(self, formula):
        I = self.I
        class Visitor(RichTreeWalk.Visitor):
            def enter(self, subtree, prune=lambda:None):
                return subtree.root in I
            def join(self, subtree, prefix, infix, postfix):
                union = IdSet(x for n in infix for x in n)
                if prefix and forall([sub in union for sub in subtree.subtrees]):
                    union = IdSet([subtree])
                return union

        return RichTreeWalk(Visitor())(formula)
    
    def replace_all(self, formula):
        return self.replace_all_inplace(formula)
    
    def replace_all_inplace(self, formula):
        if isinstance(formula, collections.MutableSequence):
            for item in formula:
                self.replace_all_inplace(item)
        else:
            for m in self.mark(formula):
                m.root = self(m); m.subtrees = []
        return formula
    
    def algebraic_fragment(self, theory):
        """
        Extracts the portion of a theory which is well-formed with respect to
        the algebra defined by this theory's signature combined with the 
        calculator's native types.
        """
        N = self.I.native_types
        def is_ok(identifier, sorts):
            s = identifier
            if isinstance(s, N) or s in self.I:
                return True
            elif isinstance(s, str):
                return s in sorts.sorts
            elif isinstance(s, Identifier):
                if isinstance(s.literal, N): return True
                return s.kind == 'connective' or s == FolWithEquality.eq or \
                    (s in sorts.sorts or s.literal in sorts.sorts)
            else:
                return False
        def iter_formulas():
            sorts = getattr(theory.signature, 'sorts', FolSorts())
            for formula in theory:
                if forall(formula.nodes, lambda n: is_ok(n.root, sorts)):
                    yield formula
        return FolTheory(iter_formulas()).with_signature(theory.signature)

    def scheme_as_function(self, scheme):
        def scheme_f(*a):
            valuation = dict(zip(scheme.placeholders, a))
            return self(scheme.formula, valuation)
        scheme_f.__name__ = unicode(scheme).encode('utf-8')
        return scheme_f
