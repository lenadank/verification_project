# encoding=utf-8

import copy
import new
from collections import Callable, Sequence, Mapping

from adt.tree import Tree
from adt.tree.walk import PreorderWalk
from pattern.meta import oop
from pattern.meta.overloading import CovertOps
from pattern.mixins import promote

from logic.fol.syntax import Identifier, RepresentationForm
import collections
    


class FolFormula(Tree):

    Identifier = Identifier
    
    AND =     Identifier(u"∧", 'connective')
    OR =      Identifier(u"∨", 'connective')
    NOT =     Identifier(u"¬", 'connective')
    IMPLIES = Identifier(u"➝", 'connective')
    IFF =     Identifier(u"↔", 'connective')
    FORALL =  Identifier(u"∀", 'quantifier')
    EXISTS =  Identifier(u"∃", 'quantifier')
    
    TRUE =    Identifier(True, 'predicate')
    FALSE =   Identifier(False, 'predicate')
    
    INFIXES = [IMPLIES, IFF, AND, OR,
               "=", "<", "<=", ">", ">=", "!=", u"≠", u"≤", u"≥", u"∈", u"∉",
               "+", "-", "*", "/", "^"]
    
    LEFT = "LEFT"
    RIGHT = "RIGHT"
    ASSOC = "ASSOC"
    
    PREC = {AND: (1, ASSOC),
            OR: (2, ASSOC),
            IMPLIES: (3, RIGHT), IFF: (3, RIGHT)}

    def __unicode__(self):
        if self.root in [self.FORALL, self.EXISTS] and len(self.subtrees) == 2:
            return u"%s%r (%r)" % ((self.root,) + tuple(self.subtrees))
        elif self.root in self.INFIXES and len(self.subtrees) == 2:
            p = lambda x,pos,r=self.root: self._parenthesize(r, x, pos)
            return u"%s %s %s" % (p(self.subtrees[0],self.LEFT), self.root, p(self.subtrees[1],self.RIGHT))
        elif isinstance(self.root, RepresentationForm):
            return self.root.repr(self.subtrees)
        elif isinstance(self.root, Identifier):
            if len(self.subtrees) == 0:
                return unicode(self.root)
            else:
                subreprs = u", ".join(`x` for x in self.subtrees)
                return u"%s(%s)" % (self.root, subreprs)
        else:
            return super(FolFormula, self).__repr__()

    def _parenthesize(self, op, operand, pos=RIGHT):
        PREC, ASSOC = self.PREC, self.ASSOC
        sop = operand.root
        if op in PREC and sop in PREC:
            opp, sopp = PREC[op], PREC[sop]
            if opp[0] < sopp[0]:    # sub-expression binds weaker than op
                return u'(%s)' % operand
            elif opp[0] == sopp[0] and (ASSOC != opp[1] != pos or ASSOC != sopp[1] != pos):  
                # same precedence but irregular associativity
                return u'(%s)' % operand
        return unicode(operand)

    def __repr__(self):
        return self.__unicode__().encode(errors='replace')
    
    @property
    def symbols(self):
        return set(n.root for n in self.nodes)

    @classmethod
    def promote(cls, obj):
        if isinstance(obj, cls):
            return obj
        else:
            return cls(cls.Identifier.promote(obj))

    def split(self, connective=AND):
        """
        Breaks a formula expression tree down to a forest according to some
        connective.
        E.g.  (a | b) & (c -> b) & ((c & d) | e)  --->  [a|b, c->b, (c&d)|e]
        
        @param connective: an identifier or list/tuple/set thereof, by which to split
        @return a list of formulas
        """
        if not isinstance(connective, (list, tuple, set)): connective = (connective,)
        if self.root in connective:
            return [part for s in self.subtrees for part in s.split(connective)]
        else:
            return [self]

    @classmethod
    def join(cls, connective, formulas, default_value=None, assoc=LEFT):
        formulas = list(formulas)  # yeah, not that efficient but needed to check for empty case
        if formulas:
            if assoc == cls.LEFT:
                return reduce(lambda x,y: cls(connective, [x, y]), formulas)
            elif assoc == cls.RIGHT:
                return reduce(lambda x,y: cls(connective, [y, x]), reversed(formulas))
            else:
                raise ValueError, "invalid association '%s', should be either %r or %r" % (assoc, cls.LEFT, cls.RIGHT)
        else:
            return cls(default_value)

    @classmethod
    def conjunction(cls, list_of_conjuncts):
        return cls.join(cls.AND, list_of_conjuncts, default_value=cls.TRUE)
    
    @classmethod
    def disjunction(cls, list_of_disjuncts):
        return cls.join(cls.OR, list_of_disjuncts, default_value=cls.FALSE)


class FolSignature(object):
    
    def __init__(self, funcs=[], preds=[]):
        """
        @param funcs: function symbols, each of the form (f, arity)
        @param preds: predicate symbols, each of the form (p, arity)
        """
        self.funcs = funcs
        self.preds = preds
        
    @property
    def constants(self):
        return [c for c,arity in self.funcs if arity == 0]
    
    @property
    def symbols(self):
        return set(self.itersymbols())

    def itersymbols(self):
        return (c for slist in (self.funcs, self.preds) for c,arity in slist)
    
    def __repr__(self):
        return "%s f%r p%r" % (type(self).__name__, self.funcs, self.preds)
        
    def used_fragment(self, theory):
        narrow = type(self)()
        symbols = set([(s,a) for phi in theory for (s,a) in self._symbols_with_arity(phi)])
        narrow.funcs = [(f,a) for f,a in self.funcs if (f,a) in symbols]
        narrow.preds = [(p,a) for p,a in self.preds if (p,a) in symbols]
        return narrow
    
    def _symbols(self, phi):
        return (x.root for x in PreorderWalk(phi))
    
    def _symbols_with_arity(self, phi):
        return ((x.root, len(x.subtrees)) for x in PreorderWalk(phi))
    
    def __or__(self, other):
        if type(other) == FolSignature: # intentionally NOT using isinstance
            return FolSignature(set(self.funcs) | set(other.funcs),
                                set(self.preds) | set(other.preds))
        else:
            return NotImplemented
        
    def __sub__(self, other):
        if type(other) == FolSignature: # intentionally NOT using isinstance
            return FolSignature(set(self.funcs) - set(other.funcs),
                                set(self.preds) - set(other.preds))
        else:
            return NotImplemented

    def update(self, other):
        self.funcs = set(self.funcs) | set(other.funcs)
        self.preds = set(self.preds) | set(other.preds)


class FolSymbolic(Tree, promote.SimplisticPromoteMixIn):
    """
    Provides syntactic sugar for building first-order formulas.
    There are two recommended usage forms:
    1. Define variables of type FolSymbolic, each representing a single
       symbol (variable, function, predicate), then compose them using
       operators {~, &, |, >>, %, **, //}, and eventually call .to_formula().
       e.g.
       a = FolSymbolic(Identifier('a', 'predicate'))
       u = FolSymbolic(Identifier('u', 'variable'))
       phi = (u ** (a(u) >> ~a(u))).to_formula()
    2. Define a lambda function with arguments each representing a symbol
       (variable, function, predicate) and performing logical operations on
       them using {~, &, |, >>, %, **, //}; then call .formula(...).
       e.g.
       sig = {'a': Identifier('a', 'predicate'), 
              'u': Identifier('u', 'predicate')}
       phi = FolSymbolic(lambda a,u: u ** (a(u) >> ~a(u)))
    
    ~  stands for logical not (¬)
    &  stands for logical and (∧)
    |  stands for logical or (∨)
    >> stands for implication (➝)
    %  stands for if-and-only-if (↔)
    ** stands for universal quantification (∀)
    // stands for existential quantification (∃)
    """
    
    SUGAR = {'~':  FolFormula.NOT,
             '&':  FolFormula.AND,
             '|':  FolFormula.OR,
             '>>': FolFormula.IMPLIES,
             '%':  FolFormula.IFF,
             '**': FolFormula.FORALL,
             '//': FolFormula.EXISTS
            }
    VECTOR = Identifier(u"◦⃗", "macro")
    
    def __invert__(self):
        return type(self)('~', [self])
    
    def __and__(self, other):
        return type(self)('&', [self, other])
    
    def __or__(self, other):
        return type(self)('|', [self, other])
    
    def __rshift__(self, other):
        return type(self)('>>', [self, other])

    def __mod__(self, other):
        return type(self)('%', [self, other])

    def __pow__(self, other):
        return type(self)('**', [self, other])
    
    def __floordiv__(self, other):
        return type(self)('//', [self, other])
    
    def __sub__(self, operator):
        if isinstance(operator, FolSymbolic):
            operator = operator.root
        if isinstance(operator, Callable):
            return type(self)(operator(self.root), self.subtrees)
        else:
            return NotImplemented
    
    def __call__(self, *args):
        if self.subtrees:
            raise SyntaxError, "invalid use of () after '%r'" % self
        elif isinstance(self.root, Identifier):
            return type(self)(self.root, [x if isinstance(x, FolSymbolic) else FolSymbolic(x)
                                          for x in args])
        else:
            return type(self)(self.root(*((x.root if isinstance(x, FolSymbolic) else x)
                                          for x in args)))
        
    def __getitem__(self, subscript):
        if isinstance(self.root, (Sequence, Mapping)):
            return type(self)(self.root[subscript])
        else:
            return NotImplemented
        
    def build(self, root, subtrees):
        return type(self)(root, [self.promote(x) for x in subtrees])
        
    def with_identifiers(self, identifiers):
        self.identifiers = identifiers
        return self
        
    def to_formula(self):
        r = self.root
        if isinstance(r, FolFormula):
            return r
        elif isinstance(r, list):
            r = [isinstance(x, FolFormula) and x or FolFormula(x) for x in r]
            return FolFormula(self.VECTOR, r)
        else:
            formula = FolFormula(self.SUGAR.get(r, r),
                                 [sub.to_formula() for sub in self.subtrees])
            return self.expand_vectors(formula)
            
    def expand_vectors(self, formula):
        root = formula.root
        subtrees = formula.subtrees
        if root in [FolFormula.FORALL, FolFormula.EXISTS] and subtrees[0].root == self.VECTOR:
            formula = reduce(lambda x,y: FolFormula(root, [y, x]),
                             reversed(subtrees[0].subtrees), 
                             subtrees[1])
        elif isinstance(root, Identifier) and root.kind != "connective":
            flatten = [x for s in subtrees for x in 
                       (s.root != self.VECTOR and [s] or s.subtrees)]
            formula = FolFormula(root, flatten)
        elif root == self.VECTOR:
            raise ValueError, "a vector is not allowed here: '%s'" % formula

        formula = FolFormula(formula.root, [self.expand_vectors(x) for x in formula.subtrees])
        return formula
            
    @classmethod
    def construct(cls, lambda_expr, signature_vars={}):
        import inspect #@UnresolvedImport
        if isinstance(lambda_expr, str) or isinstance(lambda_expr, unicode):
            lambda_expr = flam(lambda_expr)
        symbols, _, _, _ = inspect.getargspec(lambda_expr)
        def mksymbol(literal):
            if literal == 'true': return True
            if literal == 'false': return False
            try:
                return signature_vars[literal]
            except KeyError:
                return Identifier(literal, '?')
        ids = [mksymbol(s) for s in symbols]
        ids_genuine = [i for i in ids if isinstance(i, Identifier)]
        id_args = tuple(cls(i) for i in ids)
        retval = lambda_expr(*id_args)
        return cls.promote(retval).with_identifiers(ids_genuine)
        
    @classmethod
    def formula(cls, lambda_expr, signature_vars={}):
        return cls.construct(lambda_expr, signature_vars).to_formula()
    
    class Language(object):
        """
        Just a bit of syntactic sugar to avoid too much repetition in programs
        where there are lots of formulas.
        """
        def __init__(self, signatures=[]):
            if not isinstance(signatures, collections.Sequence):
                signatures = [signatures]
            self.signatures = []
            for sig in signatures:
                if hasattr(sig, '__bases__'):
                    ex = [c for c in oop.all_ur_base(sig) if c is not object]
                else:
                    ex = [new.classobj('Signature', (), {'formal': sig})]
                self.signatures.extend(ex)
            self.dict = {}
            self.FolSymbolic = FolSymbolic
            for signature in reversed(self.signatures):
                self.dict.update(signature.__dict__)
        def with_(self, **kw):
            c = copy.copy(self)
            c.dict = copy.copy(c.dict)
            c.dict.update(kw)
            return c
        def with_sugar(self, *sugars):
            """
            Combines the functionality of one or more FolSymbolic mix-ins,
            for use in the syntax of formulas processed by this language.
            """
            bases = (CovertOps,) + sugars + (self.FolSymbolic,)
            self.FolSymbolic = new.classobj('FolSymbolic+', bases,
                                            {'_': self.signatures[0]})
            return self
        @property
        def signature(self):
            return reduce(lambda x,y: x|y, (s.formal for s in self.signatures if hasattr(s, 'formal')))
        def formula(self, expr):
            return self.FolSymbolic.formula(expr, self.dict)
        def __mul__(self, expr):
            if isinstance(expr, list):
                from logic.fol.syntax.theory import FolTheory
                return FolTheory(self.formula(el) for el in expr)\
                        .with_signature(self.signature)
            else:
                return self.formula(expr)
        

def flam(s):
    import compiler #@UnresolvedImport
    c = compiler.compile(s, "<flam>", "eval")
    return eval("lambda %s: %s" % (",".join(c.co_names), s))



if __name__ == '__main__':
    l = FolSymbolic
    inputs = [lambda a: ~a,
              lambda x,y,z: (x >> y) | z,
              lambda a,u,v: a(u,v) >> a(v,u),
              lambda a,u,v: u ** v ** (a(u,v) >> a(v,u)),
              lambda a,u,v,f: u ** v ** (a(f[1](u, v), f[2](v,u)))]

    I = FolFormula.Identifier
    s = {'f': [None, I('f[1]', 'function'), I('f[2]', 'function')]}
    
    for input in inputs: #@ReservedAssignment
        print FolSymbolic.formula(input, s)

    print FolFormula.conjunction(FolSymbolic.formula(input, s) for input in inputs) #@ReservedAssignment
    print FolFormula.disjunction(FolSymbolic.formula(input, s) for input in inputs) #@ReservedAssignment
    
