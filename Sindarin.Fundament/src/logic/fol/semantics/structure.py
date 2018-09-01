# encoding=utf-8

from pattern.functor import Inverse, MembershipFunctor, ExplicitFunctor
from pattern.quantifier.mux import MultiDomain
from logic.fol.syntax.formula import FolFormula, FolSignature
from logic.fol.semantics import FolSemanticError
from logic.fol.semantics.extensions.sorts import FolManySortSignature
from pattern.collection.sort import SortBy
from ui.text.table import Table
 


class FolAssignment(dict):
    
    def __div__(self, more_values):
        c = FolAssignment(self)
        c.update(more_values)
        return c
    
    
class FolStructure(object):
    
    def __init__(self, domain, interpretation=None):
        self.domain = domain
        if interpretation is None:
            self.interpretation = {}
        else:
            self.interpretation = interpretation
        
    def __repr__(self):
        return u"M=〈D=%r, I=%r〉" % (self.domain, self.interpretation)
        
    def domain_of(self, symbol, signature):
        d = MultiDomain.promote(self.domain)
        s = FolManySortSignature.promote(signature)
        for (from_,_) in s.sort_of(symbol):
            if len(from_) == 1:
                l = d[from_[0]]
            else:
                l = d[from_]
            for el in l: yield el
            
    def range_of(self, symbol, signature):
        d = MultiDomain.promote(self.domain)
        s = FolManySortSignature.promote(signature)
        for r in set(to_ for _,to_ in s.sort_of(symbol)):
            for el in d[r]: yield el
        
    def evaluate(self, formula, assignment=FolAssignment()):
        try:
            return self._evaluate(formula, assignment)
        except Exception, e:
            raise NestedException(formula, e)
            
    def _evaluate(self, formula, assignment=FolAssignment()):
        lit = formula.root
        # Quantifier semantics
        if formula.root == FolFormula.FORALL:
            variable, subformula = formula.subtrees
            variable = variable.root
            for v in self.domain:
                if not self.evaluate(subformula, assignment / {variable: v}):
                    return False
            return True
        if formula.root == FolFormula.EXISTS:
            variable, subformula = formula.subtrees
            variable = variable.root
            for v in self.domain:
                if self.evaluate(subformula, assignment / {variable: v}):
                    return True
            return False
        # Connective semantics
        elif formula.root == FolFormula.IMPLIES:
            lhs, rhs = formula.subtrees
            return not self.evaluate(lhs, assignment) \
                    or self.evaluate(rhs, assignment)
        elif formula.root == FolFormula.IFF:
            lhs, rhs = formula.subtrees
            return self.evaluate(lhs, assignment) == \
                   self.evaluate(rhs, assignment)
        elif formula.root == FolFormula.AND:
            lhs, rhs = formula.subtrees
            return self.evaluate(lhs, assignment) \
                    and self.evaluate(rhs, assignment)
        elif formula.root == FolFormula.OR:
            lhs, rhs = formula.subtrees
            return self.evaluate(lhs, assignment) \
                    or self.evaluate(rhs, assignment)
        elif formula.root == FolFormula.NOT:
            rhs, = formula.subtrees
            return not self.evaluate(rhs, assignment)
        # Structure interpretation semantics
        elif lit in self.interpretation:
            func_interp = self.interpretation[lit]
            if isinstance(lit, FolFormula.Identifier) and lit.kind == "macro":
                arguments = [self, assignment] + formula.subtrees
            else:
                arguments = [self.evaluate(x, assignment) for x in formula.subtrees]
            if len(arguments) == 0:
                return func_interp
            elif isinstance(func_interp, dict):
                if len(arguments) == 1:
                    return func_interp[arguments[0]]
                else:
                    return func_interp[tuple(arguments)]
            else:
                return func_interp(*arguments)
        elif isinstance(formula.root, FolFormula.Identifier):
            if lit in assignment:
                return assignment[lit]
            else:
                raise FolSemanticError(lit)
        else:
            raise ValueError, formula

    @classmethod
    def build(cls, signature, domain, dictionary, *standard):
        interpretation = dict((cnst, dictionary[cnst]) for cnst in signature.constants)
        for pred, _ in signature.preds:
            interpretation[pred] = MembershipFunctor(set(dictionary[pred]))
        for func, arity in signature.funcs:
            if arity > 0 and func in dictionary:
                interpretation[func] = ExplicitFunctor(dictionary[func])
        for more in standard:
            interpretation.update(more)
        return cls(domain, interpretation)
    
    def pretty(self, omit=()):
        """
        Formats the contents of the structure as a text string for
        human-readable output display.
        @param omit: a list of symbols whose interpretation should never be
          displayed (usually standard symbols)
        @return a unicode string
        """
        lines = [u"D=%s" % self.domain, u"I="]
        for key in SortBy(repr)(self.interpretation.keys()):
            if key not in omit:
                value = self.interpretation[key]
                lines += [u"   %s: %s" % (key, value)]
        return u"\n".join(lines)
        
    def binary_relation_as_table(self, relation_name):
        """
        Represents a binary relation R textually using a 2-dimensional
        table where the row headers represent values of the first arguments
        and column headers - the second argument.
        """
        vals = self.domain  # TODO: MultiDomain
        t = Table()
        t.header = [relation_name] + list(vals)
    
        r = self.interpretation[relation_name]
        for u in vals:
            row = [u]
            for v in vals:
                row += ['x' if r(u, v) else '']
            t.data += [row]
        return t



class FolDomainProjection(object):
    
    class Projected(object):
        def __init__(self, value_func, project_func, unproject_func, arity):
            self.value_func = value_func
            self.project_func = project_func
            self.unproject_func = unproject_func
            self.arity = arity
        def _call(self, xvec):
            if self.arity == 0:
                return self.value_func
            else:
                xvec_tag = tuple(self.unproject_func(x) for x in xvec)
                return self.value_func(*xvec_tag)
        
    class ProjectedFunction(Projected):
        def __call__(self, *xvec):
            return self.project_func(self._call(xvec))
        
    class ProjectedIterable(Projected):
        def __call__(self, *xvec):
            return self._call(xvec)
        def __iter__(self):
            for value in self.value_func:
                if self.arity == 1:
                    yield self.project_func(value)
                else:
                    yield tuple(self.project_func(v) for v in value)
        def iteritems(self):
            if self.arity == 1:
                return ((value, self(value)) for value in self)
            else:
                return ((value, self(*value)) for value in self)
    
    def __init__(self, signature, project_func):
        self.signature = signature
        self.project_func = project_func
        
    def __call__(self, structure):
        i = structure.interpretation
        preds = self.signature.preds
        funcs = self.signature.funcs
        elements = list(MultiDomain.promote(structure.domain))
        project_inv = Inverse(self.project_func, elements)
        i_tag = {}
        PF = self.ProjectedFunction
        PI = self.ProjectedIterable
        for p, arity in preds:
            if p in i:
                if arity == 0:
                    i_tag[p] = i[p]
                else:
                    i_tag[p] = PI(i[p], self.project_func, project_inv, arity) 
        for f, arity in funcs:
            if f in i:
                if arity == 0:
                    i_tag[f] = self.project_func(i[f])
                else:
                    i_tag[f] = PF(i[f], self.project_func, project_inv, arity)
        if isinstance(structure.domain, list):
            d_tag = [self.project_func(x) for x in structure.domain] 
        elif isinstance(structure.domain, dict):
            d_tag = dict((k, [self.project_func(x) for x in v])
                         for k,v in structure.domain.iteritems())
        return FolStructure(d_tag, i_tag)



class FolResample(object):
    
    def function(self, func, from_, domain):
        if from_ == ():
            return func
        elif len(from_) == 1:
            return ExplicitFunctor((x[0], func(*x)) for x in domain[from_])
        else:
            return ExplicitFunctor((x, func(*x)) for x in domain[from_])
    
    def predicate(self, pred, from_, domain): 
        if from_ == ():
            return pred
        elif len(from_) == 1:
            return MembershipFunctor(x[0] for x in domain[from_] if pred(*x))
        else:
            return MembershipFunctor(x for x in domain[from_] if pred(*x))
        
    def structure(self, structure, signature, domain=None):
        if domain is None: domain = structure.domain
        domain = MultiDomain.promote(domain)
        s = FolManySortSignature.promote(signature)
        i = structure.interpretation
        explicit_i = {}
        for f,_ in signature.funcs:
            explicit_i[f] = self.join(self.function(i[f], from_, domain)
                                      for from_,_ in s.sort_of(f))
        for p,_ in signature.preds:
            explicit_i[p] = self.join(self.predicate(i[p], from_, domain)
                                      for from_,_ in s.sort_of(p))
        return FolStructure(domain, explicit_i)
    
    def join(self, es):
        es = list(es)
        [es[0].update(e) for e in es[1:]]
        return es[0]


class NestedException(Exception):
    def __init__(self, context, inner):
        self.context = context
        self.inner = inner
        if isinstance(inner, self.__class__):
            self.__class__ = inner.__class__
        else:
            class NestedException(self.__class__, inner.__class__):
                __str__ = __repr__ = self.__class__.__str__
            self.__class__ = NestedException
    def __str__(self):
        return "In: %r\n%r" % (self.context, self.inner)



# Snippet
if __name__ == '__main__':
    from logic.fol import Identifier
    i = Identifier('i', 'function')
    sigma = FolSignature([(i,1)], [])
    m = FolStructure([1,2,3], {i: lambda x: x%3+1})
    p = FolDomainProjection(sigma, lambda t: t*2)
    n = p(m)
    print n.domain
    print n.interpretation['i']
    print [n.interpretation['i'](x) for x in n.domain]
    print FolResample().structure(n, sigma)
    
    print m.evaluate(FolFormula(i, [FolFormula(2)]))
