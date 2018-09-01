#encoding=utf-8

from z3 import *  # @UnusedWildImport
from logic.fol.syntax.formula import FolFormula
from logic.fol.syntax import Identifier
from logic.fol.semantics.extensions.arith import FolIntegerArithmetic
from pattern.meta.oop import InnerClasses
from collections import namedtuple
from logic.fol.syntax.scheme import FolScheme
from logic.fol.semantics.extensions.equality import FolWithEquality
from logic.fol.semantics.extensions.sorts import FolManySortSignature, FolSorts
from logic.fol.semantics.structure import FolStructure
from pattern.functor import MembershipFunctor, ExplicitFunctor
from logic.fol.semantics.graphs import AlgebraicStructureGraphTool
from z3support import get_id



class Z3FormulaToFolFormula(object):
    
    def __init__(self):
        self.map_ops = {Z3_OP_AND: FolFormula.conjunction,
                        Z3_OP_OR: FolFormula.disjunction,
                        Z3_OP_NOT: FolFormula.NOT,
                        Z3_OP_IMPLIES: FolFormula.IMPLIES,
                        Z3_OP_IFF: FolFormula.IFF,
                        Z3_OP_EQ: FolWithEquality.eq,
                        Z3_OP_DISTINCT: FolWithEquality.neq,
                        Z3_OP_ADD: FolIntegerArithmetic.add,
                        Z3_OP_MUL: FolIntegerArithmetic.mul,
                        Z3_OP_LE: FolIntegerArithmetic.le,
                        Z3_OP_GE: FolIntegerArithmetic.ge,
                        Z3_OP_SELECT: self._array_select}

    class ConversionProcess(InnerClasses.Owned):
        
        Var = namedtuple("Var", 'identifier sort')
        
        def __init__(self, o):
            super(Z3FormulaToFolFormula.ConversionProcess, self).__init__(o)
            self.vars = {}
    
        def with_some_vars(self, vars0):
            """ vars0 is a list of Var instances """
            import copy
            c = copy.copy(self)
            nz = len(vars0)
            c.vars = {k+nz: v for k,v in c.vars.iteritems()} #c.vars.copy()
            for i, v in enumerate(vars0):
                c.vars[i] = v
            return c
    
        def __call__(self, t):
            if is_var(t):
                return FolFormula(self._get_free_var(t))
            elif is_true(t) or is_false(t):
                return FolFormula(is_true(t))
            elif is_const(t):
                kind = 'predicate' if is_bool(t) else 'function'
                return FolFormula(Identifier(unicode(t), kind))
            elif is_quantifier(t) and t.is_forall():
                return self._quantify_forall(t)
            elif is_app(t):
                r = t.decl()
                for k,v in self.o.map_ops.iteritems():
                    if is_app_of(t, k):
                        r = v
                        break
                else:
                    r = Identifier(unicode(r), '?')
                if callable(r):
                    return r([self(x) for x in t.children()])
                else:
                    return FolFormula(r, [self(x) for x in t.children()])
            else:
                raise NotImplementedError
            
        def _get_free_var(self, var):
            i = get_var_index(var)
            if i in self.vars:
                return self.vars[i].identifier
            else:
                self.vars[i] = v = self.Var(Identifier("$%d" % i, 'variable'), var.sort())
                return v.identifier

        def _quantify_forall(self, t):
            vars0 = [ self.Var(Identifier(t.var_name(i), 'variable'), None)
                      for i in reversed(xrange(t.num_vars()))]
            body = self.with_some_vars(vars0)(t.body())
            phi = body
            for v in vars0:
                phi = FolFormula(FolFormula.FORALL, [FolFormula(v.identifier), phi])
            return phi

    def __call__(self, t):
        phi = self.scheme(t)
        if not phi.placeholders:
            return phi.formula
        else:
            return phi
        
    def scheme(self, t):
        cp = self.ConversionProcess(self)
        phi = cp(t)
        return FolScheme(phi, [v.identifier for v in cp.vars.itervalues()])
    
    
    def _array_select(self, (arr, subscript)):
        return FolFormula(arr.root, arr.subtrees + [subscript])
    
            

BOOL = BoolSort()


class Z3SymbolsToFolManySortSignature(object):
    
    def __call__(self, z3_elements):
        sorts = FolSorts()
        decls = {}
        for z3_symbol in z3_elements:
            idf = Identifier(z3_symbol.name(), self._get_kind(z3_symbol))
            decls[idf] = z3_symbol
            if is_const(z3_symbol):
                sorts[idf] = FolSorts.FunctionType((), z3_symbol.sort())
            elif is_func_decl(z3_symbol):
                z3_domains = [z3_symbol.domain(i)
                              for i in xrange(z3_symbol.arity())]
                z3_range = z3_symbol.range()
                sorts[idf] = FolSorts.FunctionType(tuple(z3_domains), z3_range)
                
        sigma = FolManySortSignature.from_sorts(sorts)
        sigma.z3_decls = decls
        return sigma
    
    def _get_kind(self, z3_symbol):
        if is_const(z3_symbol):
            return 'function'
        elif is_func_decl(z3_symbol):
            return 'predicate' if z3_symbol.range() == BOOL else 'function'
                
        

class Z3ModelToFolStructure(object):
    
    def __init__(self, signature, z3_decls):
        self.sigma = signature
        self.z3_decls = z3_decls
    
    def __call__(self, model):
        BOOL = BoolSort()
        m = FolStructure({})
        domain = {}
        
        for symbol in self.sigma.itersymbols():
            try:
                z3_symbol = self.z3_decls[symbol]
            except KeyError:
                continue
            if is_func_decl(z3_symbol) and z3_symbol.arity() == 0:
                z3_symbol = z3_symbol()
            if is_const(z3_symbol):
                z3_val = model.evaluate(z3_symbol)
                #print "CONST", z3_symbol, ":", z3_symbol.sort(), "=", z3_val
                el = self.locate_element(domain, model, z3_val)
                if el is not None:
                    m.interpretation[symbol] = el
            if is_func_decl(z3_symbol):
                pop = [((), ())]
                interp = model.get_interp(z3_symbol)
                if interp is None: continue
                interp = interp.as_list()
                for i in xrange(z3_symbol.arity()):
                    z3_sort = z3_symbol.domain(i)
                    z3_dom = model.get_universe(z3_sort)
                    dom = self.translate_universe(domain, z3_sort, z3_dom)
                    if not dom:
                        dom = [(self.locate_element(domain, model, x[i]), x[i]) 
                               for x in interp if isinstance(x, list)]
                    pop = [(tup + (el,), z3_tup + (z3_el,))
                            for tup,z3_tup in pop for el,z3_el in dom]
                    
                # annoying corner case
                pop = [(tup[0] if len(tup)==1 else tup, z3_tup) for tup,z3_tup in pop]
                    
                #print z3_symbol, ",  |values| =", len(pop)

                if z3_symbol.range() == BOOL:
                    vals_hash = {tup for tup, z3_tup in pop
                                 if is_true(model.evaluate(z3_symbol(*z3_tup)))}
                    m.interpretation[symbol] = MembershipFunctor(vals_hash)
                else:
                    vals_dict = {tup: self.locate_element(domain, model,
                                                          model.evaluate(z3_symbol(*z3_tup)))
                                 for tup, z3_tup in pop}
                    m.interpretation[symbol] = ExplicitFunctor(vals_dict)
                    
                #print "      (got it)"
            
        m.domain.update({k: set(x for x,_ in v) for k,v in domain.iteritems()})    
        return m
                
    def translate_universe(self, domains, z3_sort, universe):
        name = z3_sort.name()
        try:
            return domains[name]
        except KeyError:
            if not universe: return []
            domains[name] = u = [(unicode(el).replace("!val!", ":"), el)
                                 for el in universe]
            return u
        
    def locate_element(self, domains, model, z3_val):
        if is_int(z3_val):
            return z3_val.as_long()
        if is_bool(z3_val):
            return is_true(z3_val)
        z3_sort = z3_val.sort()
        z3_dom = model.get_universe(z3_sort)
        dom = self.translate_universe(domains, z3_sort, z3_dom)
        for el, z3_el in dom:
            if get_id(z3_el) == get_id(z3_val):
                return el

    @classmethod
    def get_interp(cls, model, symbol):
        import itertools
        def enumerate_domain(model, funcdecl):
            args = [funcdecl.domain(i) for i in xrange(funcdecl.arity())]
            def elements(sort):
                if isinstance(sort, DatatypeSortRef):
                    # Assume enumerator type
                    return [sort.constructor(i)() for i in xrange(sort.num_constructors())]
                else:
                    return model.get_universe(sort)
            return itertools.product(*(elements(a) for a in args))
        if is_func_decl(symbol):
            return [(el, model.evaluate(symbol(*el))) for el in enumerate_domain(model, symbol)]
        else:
            return model.get_interp(symbol)



if __name__ == '__main__':
  
  def demo1():   
    V = IntSort()
    B = BoolSort()
    sorts = [V] * 6 + [B] * 6
    
    _z3_Var = Var
    
    def Var(idx):
        return _z3_Var(idx, sorts[idx])
    
    I = (
     And(Var(3) + -1*Var(5) <= 0,
         Or(Var(5) + -1*Var(4) >= 0, Var(4) + -1*Var(2) >= 0),
         Or(Var(4) + -1*Var(2) >= 0, Var(5) + -1*Var(4) <= 0),
         Or(Var(5) + -1*Var(4) >= 0, Var(4) + -1*Var(2) <= 0),
         Or(Var(5) + -1*Var(4) >= 0, Var(7)),
         Or(Var(5) + -1*Var(4) <= 0, Var(4) + -1*Var(2) <= 0),
         Or(Var(5) + -1*Var(4) <= 0, Var(7)),
         Var(5) + -1*Var(3) <= 0,
         Not(Var(11)),
         Or(Not(Var(3) + -1*Var(2) <= 0),
            Not(Var(8)),
            Not(Var(10)),
            Not(Var(3) + -1*Var(2) >= 0)),
         Or(Var(9), Not(Var(8)), Not(Var(10))),
         Or(Var(11) == Var(7), Var(6)),
         Or(Var(2) + -1*Var(4) <= 0, Var(6)),
         Or(Var(0) + -1*Var(4) <= -1,
            Var(6),
            Var(9),
            Var(4) + -1*Var(0) <= -1),
         Or(Not(Var(0) + -1*Var(1) >= 0),
            Not(Var(10)),
            Var(6),
            Not(Var(0) + -1*Var(1) <= 0)))
         )
    
    try:
        from synopsis.proof import SynopsisFormulaParser
        L = SynopsisFormulaParser()
        I_args = L('I(u,h,i,j,t,null, n*(h,i), C(i), n*(h,u), n*(i,u), C(u), C(null))').subtrees
    except ImportError:
        raise  # this is just so I don't get an error marker in Eclipse
    
    print I
    Is = Z3FormulaToFolFormula().scheme(I)
    print Is
    Is = Is(*I_args)#(Identifier(x, 'function') for x in 'abcdefghijkl'))
    for phi in Is.split():
        print phi

  def demo2():
    V = DeclareSort("V")
    R = Function("R", V, V, BoolSort())
    u, v, w = Consts("u v w", V)
    po = And(ForAll([u,v,w], Implies(And(R(u,v), R(v,w)), R(u,w))),   # transitive
             ForAll([u,v], Not(And(R(u,v), R(v,u))))                  # antisymmetric
             )
    s = Solver()
    s.add(po)
    s.add(u != v)
    s.add(u != w)
    s.add(And(Or(R(u,v), R(v,u)), Or(R(u,w), R(w,u))))
    print s.check()
    m = s.model()
    class _:
        u = Identifier('u', 'function')
        v = Identifier('v', 'function')
        w = Identifier('w', 'function')
        R = Identifier('R', 'predicate')
        sorts = FolSorts({u: u'→V', v: u'→V', w: u'→V', R: u'V×V→'})
    sig = FolManySortSignature.from_sorts(_.sorts)
    z3m = Z3ModelToFolStructure(sig, {_.u: u, _.v: v, _.w: w, _.R: R})
    mm = z3m(m)
    print mm
    from adt.graph.format import DEFAULT as FORMATTER
    mm.domain = mm.domain['V']
    print FORMATTER(AlgebraicStructureGraphTool(mm, [_.R])())
    
  demo2()
