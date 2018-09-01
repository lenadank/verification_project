# encoding=utf-8
import linker
from z3 import *
from relaxed_trace import *
import collections
from logic.fol.semantics.extensions.sorts import FolManySortSignature, FolSorts
from eprv.synopsis.declare import TypeDeclarations
from eprv.synopsis.expand import SynopsisFormulaParser
from eprv.synopsis.proof import Expansion, TCSpecific, ProofSynopsis
from logic.fol.syntax.formula import FolFormula
from logic.fol.semantics.extensions.equality import FolWithEquality
from logic.fol.syntax import Identifier
from logic.fol.syntax.scheme import FolScheme, FolSubstitution
from ui.text.table import Table
from logic.fol.syntax.transform import AuxTransformers
from shape2horn import hoist_forall
from pattern.debug.profile import Stopwatch
from pattern.collection.basics import OneToOne
from logic.fol.semantics.graphs import AlgebraicStructureGraphTool

from z3support.adapter import Z3ModelToFolStructure, Z3FormulaToFolFormula
from mini_bmc import BMC
from logic.fol.syntax.transform.delta import DeltaReduction



#------------------------------------------------------------------------------#
#  Declarations
#

impSort = V = DeclareSort('V')
n       = Function('n*', V, V, BoolSort())
n0      = Function('n*0', V, V, BoolSort())
n_prime = Function('n*@', V, V, BoolSort())
eqrel   = Identifier('eqrel', 'macro')
eqpred  = Identifier('eqpred', 'macro')

def nPlus(x,y):
    return And(x != y, n(x,y))

#
#------------------------------------------------------------------------------#


class Z3Gate(object):

    def __init__(self):
        self.z3_sort_map = OneToOne({'bool': BoolSort(), '': BoolSort()}).of(self._mksort)
        self.z3_decls = {}
        self.signature = FolManySortSignature()
        self.expansion = None

    def _mksort(self, sort):
        if isinstance(sort, Identifier): sort = sort.literal
        return DeclareSort(sort)

    def define_symbols(self, signature):
        """
        @param signature: an FolManySortSignature instance
        """
        self.signature |= signature
        return {sym: self.define_symbol(sym, (from_, to))
                for sym, (from_, to) in signature.sorts.iterdefs()}

    def define_symbol(self, sym, (from_, to)):
        if from_:
            return Function(sym.literal, *(self.z3_sort_map[x] for x in list(from_)+[to]))
        else:
            return Const(sym.literal, self.z3_sort_map[to])
        
    def formula(self, fol_formula):
        if isinstance(fol_formula, (str, unicode)):
            fol_formula = FolFormula.conjunction(self.expansion([fol_formula]))
        f_aux = AuxTransformers.renumber_bound_vars( fol_formula )
        return fol_formula_to_z3(f_aux, self.z3_decls)
    
    def formula_back(self, z3_formula):
        return Z3FormulaToFolFormula()(z3_formula)
    
    def structure(self, z3_model, signature=None):
        if signature is None:
            signature = self.signature
        return Z3ModelToFolStructure(signature, z3g.z3_decls)(z3_model)



def fol_formula_to_z3(f,decls):
    flen = len( f.subtrees )
    if f.root in decls:
        fsym = decls[f.root]
        args = [fol_formula_to_z3(a, decls) for a in f.subtrees]
        return fsym(*args) if args else fsym
    elif flen == 0:
        if f.root == 'true':
            return True
        elif f.root == FolFormula.FALSE or f.root == 'false':
            return False
        else:
            #raise KeyError, "undeclared constant '%s'" % f
            return Const(f.root.literal, impSort)
    elif flen == 1:
        if f.root == FolFormula.NOT:
            arg = fol_formula_to_z3( f.subtrees[0], decls)
            return Not( arg )
#        elif f.root == 'C':
#            arg = fol_formula_to_z3( f.subtrees[0], decls)
#            res = Select(C, arg)
#            return res
        else:
            raise ValueError, 'unknown formula: %s' %f
    elif flen == 2:
        lhs = fol_formula_to_z3( f.subtrees[0], decls)
        rhs = fol_formula_to_z3( f.subtrees[1], decls)
        if f.root == FolFormula.IMPLIES:
            res = Implies( lhs,rhs )
            return res
        elif f.root == FolFormula.AND:
            res = And( lhs,rhs )
            return res
        elif f.root == FolFormula.IFF:
            return lhs == rhs

        elif f.root == '=':
            return lhs == rhs
        elif f.root == '!=' or f.root == FolWithEquality.neq:
            return lhs != rhs
        elif f.root == FolFormula.OR:
            res = Or( lhs,rhs )
            return res
        elif f.root == 'n*':
            res = n( lhs,rhs )
            return res
        elif f.root == 'n*0':
            res = n0( lhs,rhs )
            return res
        elif f.root == "n*'":
            res = n_prime( lhs,rhs )
            return res
        elif f.root == FolFormula.FORALL:
            if is_quantifier(rhs) and rhs.is_forall():
                vars0 = [ Const(rhs.var_name(i), rhs.var_sort(i)) for i in range(rhs.num_vars())]
                vars0.reverse()
                b = substitute_vars(rhs.body(), *vars0)
                return ForAll( [lhs]+vars0, b )
            else:
                return ForAll( [lhs],rhs)
        elif f.root == FolFormula.EXISTS:
            if is_quantifier(rhs) and rhs.is_exists():
                vars0 = [ Const(rhs.var_name(i), rhs.var_sort(i)) for i in range(rhs.num_vars())]
                vars0.reverse()
                b = substitute_vars(rhs.body(), *vars0)
                return Exists( [lhs]+vars0, b )
            else:
                return Exists( [lhs],rhs)
        else:
            raise ValueError, "unknown root '%s' in '%s'" % (f.root, f)
    elif flen == 3 and f.root == "ite":
        a, b, c = (fol_formula_to_z3( x , decls) for x in  f.subtrees)
        return If(a, b, c)
    else:
        raise ValueError, "unknown root '%s' in '%s'" % (f.root, f)


class MainLoop(collections.namedtuple("MainLoop", "prologue cond body epilogue")): 

    SEMI = Identifier(";", '?')
    SKIP = Identifier("skip", '?')
    BAD = "~ite(cond, wp_ae(loopBody,true), wp_ae(epilogue, post))"

    @classmethod
    def factor_loop(cls, program):
        stmts = program.split(";")
        for i, stmt in enumerate(stmts):
            if stmt.root == "while":
                cond, _, body = stmt.subtrees
                return cls(prologue=stmts[:i], cond=cond, body=body, epilogue=stmts[i+1:])
        return None

    @classmethod
    def locate_loop(cls, expansion):
        [program] = expansion("program")
        if program.subtrees:
            l = cls.factor_loop(program)
            if l: return l
        [cond] = expansion("cond")
        [body] = expansion("loopBody")
        return cls(prologue=[], cond=cond, body=body, epilogue=[])
    
    def redefine(self, synopsis):
        """
        Defines macros 'cond', 'loopBody', 'epilogue', and 'bad' in the environment.
        """
        stmts = lambda x: FolFormula.join(self.SEMI, x, self.SKIP)
        delta = synopsis.expansion.delta
        delta.transformers += [DeltaReduction.Transformer(delta, name, params=[], body=expr)
                               for name, expr in [("cond", self.cond), ("loopBody", self.body),
                                                  ("epilogue", stmts(self.epilogue))]]
        
        if not any(getattr(t, 'head', None) == "bad" for t in delta.transformers):
            bad = synopsis.expansion.parser * self.BAD
            delta.transformers += [DeltaReduction.Transformer(delta, "bad", params=[], body=bad)]



def prime_equillibrium(vocab, signature, aux=set()):
    """
    Generates the formula:
       x = x' & y = y' & n* = n*' & ...
    for all the symbols in the vocabulary
    @param vocab symbols to process
    @param signature a (sorted) signature
    @param aux symbols to skip
    """
    res = []
    vocab_prime = vocab.prime()
    
    for v,vprime in vocab_prime.locals:
        # HACK: Exclude non-deterministic variables
        if v.literal.startswith('nondet') or v in aux: continue

        if  tuple(signature.sorts[v][0].from_) == ("V","V"):
            f = FolFormula( eqrel,[FolFormula(v),FolFormula(vprime)] )
        elif  tuple(signature.sorts[v][0].from_) == ("V",):
            f = FolFormula( eqpred,[FolFormula(v),FolFormula(vprime)] )
        else:
            f = FolFormula( FolWithEquality.eq,[FolFormula(v),FolFormula(vprime)] )
        res.append(f)

    return FolFormula.conjunction(res), vocab_prime


def transition_system(syn, loop, vocab, signature):
    fin, vocab_prime = prime_equillibrium(vocab, signature)
    L = syn.expansion.parser
    rho = FolScheme(L*'wp_ea([?loopBody],[?trans])')(loop.body, fin)
    rho0 = FolFormula.conjunction(syn.first_pass([rho]))
    # set back in time; x->x0, x'->x
    rho0 = vocab.to_past(rho0)
    rho0 = vocab_prime.to_past(rho0)
    return rho0


def extract_states(model, pre, post):
    m = model

    domain = m.get_universe(impSort)

    def repr_element(x):
        return unicode(x).replace("V!val!", ":")

    for br in [pre, post]:
        t = Table()
        t.header = [br] + map(repr_element, domain)
        t.data += [[repr_element(x)] + ['x' if is_true(m.eval(br(x,y))) else '' for y in domain] for x in domain]
        print t


def generate_z3_condition(folformula,syn,decls):
    c = list( syn.first_pass([folformula]) )
    f = FolFormula.conjunction( c )
    f_aux = AuxTransformers.renumber_bound_vars( f )
    f_z3 = fol_formula_to_z3( f_aux, decls)
    return hoist_forall(f_z3)


def generate_gamma(syn, preds, decls):
    dtca = Identifier('dtca', '?')
    starred = [z for z in preds if '*' in z.literal]
    gamma = FolFormula.conjunction([FolFormula(dtca, [FolFormula(z)]) for z in starred])
    return generate_z3_condition(gamma, syn, decls)



def generate_named_properties(name_property_list, type_decls):
    named_axioms = []

    for name, property_formula in name_property_list:
        p = Identifier(name, 'predicate')
        type_decls.sorts[p] = [((),'')]
        axiom = FolFormula(FolFormula.IFF, [FolFormula(p), property_formula])
        named_axioms += [(p,axiom)]

    return named_axioms 
    

        

def generate_n_properties(syn, consts, vocab):
    """
    Extra properties:  {n(u,v) | u,v program variables + null}
    """
    ntot_template = FolFormula.conjunction(map(FolScheme, syn.expansion("ntot_([?u],[?v])")))

    extras = [('n%s%s' % (u,v), ntot_template(u,v))
              for u in consts for v in consts]

    return AbstractionProperties.from_named_formulas(extras, vocab)


def generate_p_properties(syn, consts, vocab):
    """
    Extra properties:  {n(u,v) | u,v program variables + null}
    """
    ptot_template = FolFormula.conjunction(map(FolScheme, syn.expansion("ptot_([?u],[?v])")))

    extras = [('p%s%s' % (u,v), ptot_template(u,v))
              for u in consts for v in consts]

    return AbstractionProperties.from_named_formulas(extras, vocab)


def generate_nstar_properties(syn, consts):
    nstar_template = FolScheme(syn * "n*([?u],[?v])")
    return generate_binary_properties_from_template(nstar_template, consts)

def generate_binary_properties_from_template(template, consts):
    return [template(u,v)
              for u in consts for v in consts]
    

def generate_unary_pred_properties(type_decls, preds, consts):
    ts = type_decls.sorts
    for p in preds:
        for (from_, to) in ts.ary(p, 1):
            if to in ['', 'bool']:
                arg_sort = from_[0]
                for c in consts:
                    if type_decls.sorts.returns(c, arg_sort):
                        yield FolFormula(p, [FolFormula(c)])

def generate_binary_pred_properties(type_decls, preds, consts):
    ts = type_decls.sorts
    for p in preds:
        if p == 'F0': continue  # hack
        for (from_, to) in ts.ary(p, 2):
            if to in ['', 'bool']:
                arg_sort0, arg_sort1 = from_
                for c0 in consts:
                    for c1 in consts:
                        if type_decls.sorts.returns(c0, arg_sort0) and \
                           type_decls.sorts.returns(c1, arg_sort1):
                            yield FolFormula(p, [FolFormula(c0), FolFormula(c1)])


def generate_order_and_sorting_properties(syn, vocab):
    sorted_templ = FolScheme( syn * "sorted(ivlco([?u],[?v],n*))" )
    null = Identifier('null', 'function')
    a = AbstractionProperties.from_named_formulas(
           [('sorted%s%s' % (u,v), sorted_templ(u,v)) 
            for u in vocab.consts for v in [null]], vocab)
    #a.props += generate_binary_properties_from_template\
    #        (FolScheme(syn * "R([?u],[?v])"), vocab.consts)
    return a

def generate_stability_properties(syn, vocab):
    stable_templ = FolScheme( syn * "stable([?u])" )
    a = AbstractionProperties.from_named_formulas(
           [('stable%s' % u, stable_templ(u)) for u in vocab.consts], vocab)
    return a


def generate_rev_properties(syn, vocab, binary_too=True):
    np_rev_templ = FolScheme( syn * "subrev(ivlco([?u],null,n*),n*,p*)")
    pn_rev_templ = FolScheme( syn * "subrev(ivlco([?u],[?v],n*),p*,n*)")
    a = AbstractionProperties.from_named_formulas(
           [('n_p_subrev%s' % u, np_rev_templ(u)) for u in vocab.consts], vocab)
    # There is some scalability issue here,
    # so these can be turned off
    if binary_too:
        #iv = []
        iv = vocab.consts
        #iv = [v for v in vocab.consts if v in ['i','j']]   # some ad-hoc compromise
        a += AbstractionProperties.from_named_formulas(
               [('p_n_subrev%s%s' % (u,v), pn_rev_templ(u,v)) 
                for u in vocab.consts for v in iv], vocab)
    return a
    

def id_to_z3(x):
    return Const(x.literal, impSort)


def num_clauses(formula):
    if is_and(formula):
        return len(formula.children())
    elif formula == True or is_true(formula) or \
         formula == False or is_false(formula):
        return 0
    else:
        return 1

def num_univ_clauses(formula):
    if is_and(formula):
        fs = formula.children()
        n = 0
        for f in fs:
            if is_quantifier(f) and f.is_forall():
                n += 1
        return n
    elif is_quantifier(formula) and formula.is_forall():
        return 1
    else:
        return 0

def unzip(list_of_tuples, n):
    """ Auxiliary function: 
    [(a1,b1,c1), (a2,b2,c2),...] --> [a1,a2,...], [b1,b2,...], [c1,c2,...]
    """
    ls = [[] for _ in xrange(n)]
    for t in list_of_tuples:
        for i,x in enumerate(t):
            ls[i].append(x)
    return ls


def display_invariant(inv, abs_props):
    z3g = Z3Gate()
    fol_inv = z3g.formula_back(inv)
    bnd = [t.subtrees[0] for t in fol_inv.nodes if t.root.kind == 'quantifier']
    subst = {v: FolFormula(Identifier("x%d"%i, 'variable')) for i,v in enumerate(bnd)}
    subst.update(abs_props.defs)
    fol_inv = FolSubstitution(subst)( fol_inv )
    print " - " * 20
    print fol_inv
    print " - " * 20

    
def display_invariant_latex(inv):
    import functools
    def typeset_clause(phi, vars0=[]):
        typeset_clause_ = functools.partial(typeset_clause, vars0=vars0)
        if is_and(phi):
            return "(%s)" % r" \land ".join(map(typeset_clause_, phi.children()))
        elif is_or(phi):
            return "(%s)" % r" \lor ".join(map(typeset_clause_, phi.children()))
        elif is_not(phi):
            if is_eq(phi.arg(0)):
                return r"(%s \neq %s)" % (typeset_clause_(phi.arg(0).arg(0)), typeset_clause_(phi.arg(0).arg(1)))
            else:
                return "\lnot %s" % typeset_clause_(phi.arg(0))
        elif is_true(phi): return r"\mtrue"
        elif is_false(phi): return r"\mfalse"
        elif is_quantifier(phi):
            greek = [ r"\alpha", r"\beta", r"\gamma", r"\delta" ]
            vars0 = [ (greek[i] if i < len(greek) else phi.var_name(i)) for i in xrange(phi.num_vars())]
            body = typeset_clause(phi.body(), vars0)
            if phi.is_forall():
                return r"\forall %s.~ %s" % (" ".join(vars0), body)
            elif phi.is_exists():
                return r"\exists %s.~ %s" % (" ".join(vars0), body)
            else:
                raise NotImplementedError, "quantifier??"
        elif is_var(phi):
            return vars0[get_var_index(phi)]
        elif is_eq(phi):
            return r"(%s = %s)" % (typeset_clause_(phi.arg(0)), typeset_clause_(phi.arg(1)))            
        elif is_app(phi):
            head = unicode(phi.decl())
            args = map(typeset_clause_, [phi.arg(i) for i in xrange(phi.num_args())])
            symbs = {"ms": "m_s", "mt": "m_t"}
            stars = {"n*": r"\nrtc", "k*": r"\krtc", "_n*": r"\unrtc", "_k*": r"\ukrtc"}
            if not args:
                return symbs.get(head, head)
            elif head in stars:
                return r"%s%s" % (stars[head], "".join("{%s}" % x for x in args))
            else:
                if head.startswith("_"): head = r"\pre{%s}" % head[1:]
                return r"%s(%s)" % (head, ", ".join(args))
        else:
            raise NotImplementedError, phi
        
    print " - " * 20
    if is_and(inv):
        for idx, clause in enumerate(inv.children()):
            print r"L_{%d} & ~=~ & %s \\ " % (idx, typeset_clause(clause))
    else:
        print typeset_clause(inv)
    print " - " * 20


def display_structure(structure, vocab):
    from adt.graph.format import DEFAULT as FORMATTER
    
    m = structure
    m.domain = m.domain['V']
    print "V = %s" % (sorted(m.domain),)
    for c in vocab.consts:
        try:
            print "%s = %s" % (c, m.interpretation[c])
        except KeyError:
            pass
    for nstar in vocab.preds:
        if vocab.type_declarations.sorts.ary(nstar, 2):
            try:
                n = TCSpecific.restore_edge_relation_from_tc(m, rtc_relation_name=nstar)
            except (KeyError, ValueError):
                continue
            print FORMATTER(AlgebraicStructureGraphTool(m, [n])())
    for p in vocab.preds:
        if vocab.type_declarations.sorts.ary(p, 0):
            try:
                print "%s = %s" % (p, m.interpretation[p])
            except KeyError:
                pass
        if vocab.type_declarations.sorts.ary(p, 1):
            try:
                print "%s = %s" % (p, m.interpretation[p])
            except KeyError:
                pass
             
   

def report_failure(pdr, z3g, vocab):
    if pdr.counterexample:
        print '-' * 80
        display_structure(z3g.structure(pdr.counterexample), vocab)
        print '-' * 80
        return "invalid"
    else:
        print 'Looking for concrete error trace...'
        bmc = BMC(pdr.Init, pdr.Rho, pdr.Bad, pdr.background, pdr.Locals)
        m = bmc.find_concrete_trace(pdr.N)
        if m:
            for m_i in m:
                print '-' * 80
                display_structure(z3g.structure(m_i), vocab)
            print '-' * 80
            return "invalid"
        else:
            print "no concrete trace found (abstraction too coarse)"
            return "unknown"



def store_stats(shelf_filename, args, status, outcome, watch, pdr):
    import shelve, time
    try:
        sh = shelve.open(shelf_filename)
    except:
        print "- not saved (to store results in '%s', install bsddb)" % shelf_filename
        return
    key = os.path.basename(args.filename)
    qualifiers = (["safe"] if "safety-only" in args.filename else []) + \
      (["bug"] if "bugs" in args.filename else []) + \
      (["univ"] if args.u else []) + (["part"] if args.p else []) + (["opt"] if args.o else [])
    key = "".join([key] + ["[%s]" % k for k in sorted(qualifiers)])
    print key
    sh[key] = {'status': status,
               'inv': str(outcome),
               'time': watch.clock.elapsed,
               'N': pdr.N,
               '#iterations': pdr.iteration_count,
               '#Z3': pdr.sat_query_count,
               '#clauses': num_clauses(outcome),
               '#univ_clauses': num_univ_clauses(outcome),
               'timestamp': int(time.time())}
    sh.close()



EXTRA_PROP_MACROS = """
stable(p) := forall u v (n*(p,u) & alloc(u) & n*(u,v) -> alloc(v))
sorted(ivl) := forall u v (u!=null & v!=null & in(u,ivl) & in(v,ivl) & R(u,v) -> n*(u,v))
subrev(ivl,r,s) := forall u v (in(u,ivl) & in(v,ivl) & s(u,v) -> r(v,u))
"""



class TwoVocabulary(object):
    
    def __init__(self):
        self.locals = []
        self.globals = []
        self.aux = set()
        self.type_declarations = TypeDeclarations()

    def __lshift__(self, formulas):
        trans_decls = []
        for phi in formulas:
            if phi.root == FolFormula.IMPLIES and len(phi.subtrees) == 2:
                if all(self.type_declarations.is_declaration(d) for d in phi.subtrees):
                    trans_decls += [phi]
                    continue
            yield phi

        t = self.type_declarations
        t.read_from([x for d in trans_decls for x in d.subtrees])
        self.locals += [tuple(x.subtrees[0].root for x in d.subtrees)
                        for d in trans_decls]
        self.globals = [s for s in t.symbols if s not in self.locals_flat]

    @staticmethod
    def _past_tense(consts, type_decls):
        consts0 = []
        for p in consts: 
            p0 = Identifier('%s0' % p, p.kind)
            type_decls.sorts[p0] = type_decls.sorts[p][:]
            consts0 += [p0]
        
        return consts0
    
    def prime(self):
        prime = lambda x: Identifier("%s'" % x.literal, x.kind)
        vocab_prime = TwoVocabulary()
        vocab_prime.locals = [(x,prime(x)) for _,x in self.locals]
        return vocab_prime

    @property
    def symbols_flat(self):
        return self.locals_flat | set(self.globals)

    @property
    def locals_flat(self):
        return set(x for d in self.locals for x in d)

    @property
    def consts(self):
        return [z for z in set(x for _,x in self.locals) | set(self.globals)
                if t.sorts.is_const(z, of_sort='V')]
        
    @property
    def preds(self):
        return [z for z in set(x for _,x in self.locals) | set(self.globals)
                if t.sorts.returns(z, 'bool') or t.sorts.returns(z, '')]
        
    @property
    def preds_flat(self):
        return [z for z in self.symbols_flat
                if t.sorts.returns(z, 'bool') or t.sorts.returns(z, '')]
        
    @property
    def to_past(self):
        return FolSubstitution({x: x0 for (x0, x) in self.locals})


class AbstractionProperties(object):
    
    def __init__(self):
        self.props = []
        self.axioms = []
        self.axioms0 = []
        self.defs = {}
        
    def __iadd__(self, other):
        self.props += other.props
        self.axioms += other.axioms
        self.axioms0 += other.axioms0
        self.defs.update(other.defs)
        return self
        
    @classmethod
    def from_named_formulas(cls, named_formulas, vocab):
        """
        @param named_formulas:  a list of (name, formula) where 'name' is a string
          and 'formula' is a boolean formula.
        """
        a = cls()
        p, a.axioms = unzip(generate_named_properties(named_formulas, vocab.type_declarations), n=2)
        vocab.locals += zip(TwoVocabulary._past_tense(p, t), p)
        a.defs.update({symbol: formula for symbol, (_, formula) in zip(p, named_formulas)})
    
        a.axioms0 = map(vocab.to_past, a.axioms)
        
        #a = cls()
        #a.props, a.axioms0, a.axioms = [], ntot0_axioms, ntot_axioms
        vocab.aux |= set(p)
        return a


def module_system_default():
    import os.path
    from filesystem.paths import SearchPath, find_closest
    from eprv.modules import ModuleSystem
    from eprv.synopsis.proof import module_system_default as module_system_base
    here = os.path.dirname(os.path.realpath(__file__))
    
    return ModuleSystem(module_system_base().module_search_path +
                        SearchPath([find_closest("modules", start_at=here)]))



def load_data():
    import argparse

    a = argparse.ArgumentParser()
    a.add_argument('filename', type=str, nargs='?', default=argparse.SUPPRESS)
    a.add_argument('-u', action='store_true', help="universal invariant inference")
    a.add_argument('-a', action='store_true', help="(experimental) use alpha-from-below")
    a.add_argument('-p', action='store_true', help="(experimental) use partial models, not sound")
    a.add_argument('-e', action='store_true', help="(experimental) stuff, broken")
    a.add_argument('--gen-enums', action='store_true', help="generalize enum values")
    a.add_argument('--no-preds-dll', action='store_true',
                   help="do not generate abstraction predicates for dll")
    a.add_argument('--no-preds-sorted', action='store_true',
                   help="do not generate 'sorted' abstraction predicates")
    a.add_argument('--domain', type=str, default=None)
    a.add_argument('--disable-opt', dest="o",
                   action='store_false', default=True, help="(development) disable IC3 optimizations")
    a.add_argument('--out-inv', action='store_true',
                   help="print the discovered invariant as a first-order formula (requires unicode support)")
    a.add_argument('--latex', action='store_true', help="typeset discovered invariant using LaTeX")
    a.add_argument('-v', '--verbose', action='store_true')
    args = a.parse_args()

    if not hasattr(args, 'filename'):
        import os.path
        from filesystem.paths import find_closest
        here = os.path.dirname(__file__)
        args.filename = os.path.join(find_closest('benchmarks', start_at=here), 'sll-last.imp')

    program = open(args.filename).read().decode('utf-8')
    print "* BENCHMARK"
    # print os.path.basename(args.filename),
    print args.filename

    # Initiate proof synopsis and load required modules
    syn = ProofSynopsis()

    # annot = list(ProofSynopsis.get_annotations(program))
    annot = list(syn.get_annotations(program))

    # Get more flags from @flags annotation in input file
    # (note: there is currently no way to override @flags)
    for (key, val) in annot:
        if key == "flags": args = a.parse_args(a.convert_arg_line_to_args(val), args)

    ms = module_system_default()
    uses = [t.strip() for (key, val) in annot for t in val.split() if key == "uses"]
    if uses == []: uses = ['dtca_ea']  # backward compat
    for t in ['base', 'dtca']:
        if t not in uses: uses.append(t)

    syn.libs += [open(fn).read().decode('utf-8')
                 for module_name in uses for fn in ms.find_module_source(module_name)]
    syn.libs += [EXTRA_PROP_MACROS]

    # Construct vocabulary
    t = syn.type_declarations

    vocab = TwoVocabulary()
    vocab.type_declarations = t

    axioms = list(vocab << syn.first_pass(program))

    print "* PREDICATES"
    print vocab.preds

    print "* CONSTANTS"
    print vocab.consts

    # Extract loop from program (use cond := ... and loopBody := ... definitions as fallback)
    loop = MainLoop.locate_loop(syn.first_pass)

    if loop.prologue:
        raise NotImplementedError("loop prologue is currently not supported")
    loop.redefine(syn)

    trans = transition_system(syn, loop, vocab, t)
    cond = loop.cond
    cond0 = vocab.to_past(cond)

    ##############################################################
    use_extra_properties = not args.u

    if use_extra_properties:
        extra = generate_n_properties(syn, vocab.consts, vocab)

        extra.props += list(generate_unary_pred_properties(t, vocab.preds, vocab.consts))
        extra.props += list(generate_binary_pred_properties(t, vocab.preds, vocab.consts))

        extra.axioms += axioms

        # Stability (absence of dangling pointers)
        if FolSorts.FunctionType.parse(u'V→') in t.sorts.ary('alloc', 1):
            extra += generate_stability_properties(syn, vocab)

        # Properties for order and sorting
        if not args.no_preds_sorted:
            if FolSorts.FunctionType.parse(u'V×V→') in t.sorts.ary('R', 2):
                if args.domain is None or "S" in args.domain:
                    extra += generate_order_and_sorting_properties(syn, vocab)

        # Properties for reversal and doubly-linked lists
        if not args.no_preds_dll:
            if FolSorts.FunctionType.parse(u'V×V→') in t.sorts.ary('p*', 2):
                if args.domain is None or "R" in args.domain:
                    extra += generate_rev_properties(syn, vocab,
                                                     binary_too=(args.domain is None or "-" not in args.domain))
    else:
        extra = AbstractionProperties()
        extra.axioms += axioms

    # --- Now send everything to PDR + Z3

    z3g = Z3Gate()
    z3g.z3_decls = decls = z3g.define_symbols(t)
    z3g.expansion = syn.first_pass

    preds = [decls[x] for x in vocab.preds]

    extra_props = [z3g.formula(FolFormula.promote(p)) for p in extra.props]
    extra_axioms = [fol_formula_to_z3(phi, decls) for phi in extra.axioms]
    extra_axioms0 = [fol_formula_to_z3(phi, decls) for phi in extra.axioms0]

    init = z3g.formula("init")
    rho = And(z3g.formula(cond0),
              z3g.formula(trans),
              *(extra_axioms + extra_axioms0))

    bad = z3g.formula("bad")
    background = And(generate_gamma(syn, vocab.preds_flat, decls),
                     *extra_axioms)

    globals = [decls[x] for x in vocab.globals if t.sorts.ary(x, 0)]  # @ReservedAssignment
    locals = [(decls[x0], decls[x]) for x0, x in vocab.locals]  # @ReservedAssignment

    if args.u:
        print "*** Using universal invariant inference"
        from mini_pdr import PDR
        if args.p:
            print "*** Use partial models (experimental)"
        if args.gen_enums:
            print "*** Generalize enum values"
        args.o = False  # universals currently not supported in opt version
    if args.o:
        from mini_pdr_opt import PDR  # @Reimport
    elif args.a:
        print "*** Using alpha from below"
        from mini_pdr_opt import PDR  # @Reimport
    else:
        from mini_pdr import PDR  # @Reimport

    print "* GLOBALS"
    print globals

    print "* LOCALS"
    print locals
    """
   if args.u:
        pdr = PDR(init, rho, bad, background, globals, locals, preds,
                  universal=args.u, partial=args.p, gen_enums=args.gen_enums,
                  experiment=args.e)
    else:
        pdr = PDR(init, rho, bad, background, globals, locals, [n])
    """
    return init, rho, bad, background, globals, locals, [n], args.n

if __name__ == '__main__':

    import argparse

    a = argparse.ArgumentParser()
    a.add_argument('filename', type=str, nargs='?', default=argparse.SUPPRESS)
    a.add_argument('-u', action='store_true', help="universal invariant inference")
    a.add_argument('-a', action='store_true', help="(experimental) use alpha-from-below")
    a.add_argument('-p', action='store_true', help="(experimental) use partial models, not sound")
    a.add_argument('-e', action='store_true', help="(experimental) stuff, broken")
    a.add_argument('--gen-enums', action='store_true', help="generalize enum values")
    a.add_argument('--no-preds-dll', action='store_true',
            help="do not generate abstraction predicates for dll")
    a.add_argument('--no-preds-sorted', action='store_true',
            help="do not generate 'sorted' abstraction predicates")
    a.add_argument('--domain', type=str, default=None)
    a.add_argument('--disable-opt', dest="o",
                   action='store_false', default=True, help="(development) disable IC3 optimizations")
    a.add_argument('--out-inv', action='store_true', help="print the discovered invariant as a first-order formula (requires unicode support)")
    a.add_argument('--latex', action='store_true', help="typeset discovered invariant using LaTeX")
    a.add_argument('-v', '--verbose', action='store_true')
    args = a.parse_args()
    
    if not hasattr(args, 'filename'):
        import os.path
        from filesystem.paths import find_closest
        here = os.path.dirname(__file__)
        args.filename = os.path.join(find_closest('benchmarks', start_at=here), 'sll-last.imp')

    program = open(args.filename).read().decode('utf-8')
    print "* BENCHMARK"
    #print os.path.basename(args.filename),
    print args.filename

    # Initiate proof synopsis and load required modules
    syn   = ProofSynopsis()

    #annot = list(ProofSynopsis.get_annotations(program))
    annot = list(syn.get_annotations(program))

    # Get more flags from @flags annotation in input file
    # (note: there is currently no way to override @flags)
    for (key, val) in annot:
        if key == "flags": args = a.parse_args(a.convert_arg_line_to_args(val), args)   

    ms = module_system_default()
    uses = [t.strip() for (key, val) in annot for t in val.split() if key == "uses"]
    if uses == []: uses = ['dtca_ea']  # backward compat
    for t in ['base', 'dtca']: 
        if t not in uses: uses.append(t)

    syn.libs += [open(fn).read().decode('utf-8')
                 for module_name in uses for fn in ms.find_module_source(module_name)]
    syn.libs += [EXTRA_PROP_MACROS]

    # Construct vocabulary        
    t = syn.type_declarations

    vocab = TwoVocabulary()
    vocab.type_declarations = t
    
    axioms = list(vocab << syn.first_pass(program))

    print "* PREDICATES"
    print vocab.preds

    print "* CONSTANTS"
    print vocab.consts

    # Extract loop from program (use cond := ... and loopBody := ... definitions as fallback)
    loop = MainLoop.locate_loop(syn.first_pass)

    if loop.prologue:
        raise NotImplementedError("loop prologue is currently not supported")
    loop.redefine(syn)

    trans = transition_system(syn, loop, vocab, t)
    cond = loop.cond
    cond0 = vocab.to_past(cond)

    ##############################################################
    use_extra_properties = not args.u

    if use_extra_properties:
        extra = generate_n_properties(syn, vocab.consts, vocab)

        extra.props += list(generate_unary_pred_properties(t, vocab.preds, vocab.consts))
        extra.props += list(generate_binary_pred_properties(t, vocab.preds, vocab.consts))

        extra.axioms += axioms

        # Stability (absence of dangling pointers)
        if FolSorts.FunctionType.parse(u'V→') in t.sorts.ary('alloc', 1):
            extra += generate_stability_properties(syn, vocab)

        # Properties for order and sorting
        if not args.no_preds_sorted:
            if FolSorts.FunctionType.parse(u'V×V→') in t.sorts.ary('R', 2):
                if args.domain is None or "S" in args.domain:
                    extra += generate_order_and_sorting_properties(syn, vocab)

        # Properties for reversal and doubly-linked lists
        if not args.no_preds_dll:
            if FolSorts.FunctionType.parse(u'V×V→') in t.sorts.ary('p*', 2):
                if args.domain is None or "R" in args.domain:
                    extra += generate_rev_properties(syn, vocab,
                            binary_too=(args.domain is None or "-" not in args.domain))
    else:
        extra = AbstractionProperties()
        extra.axioms += axioms

    # --- Now send everything to PDR + Z3

    z3g = Z3Gate()
    z3g.z3_decls = decls = z3g.define_symbols(t)
    z3g.expansion = syn.first_pass
    
    preds = [decls[x] for x in vocab.preds]
    
    extra_props = [z3g.formula(FolFormula.promote(p)) for p in extra.props]
    extra_axioms = [fol_formula_to_z3(phi, decls) for phi in extra.axioms]
    extra_axioms0 = [fol_formula_to_z3(phi, decls) for phi in extra.axioms0]

    init       = z3g.formula("init")
    rho        = And(z3g.formula(cond0),
                     z3g.formula(trans),
                     *(extra_axioms + extra_axioms0))

    bad        = z3g.formula("bad")
    background = And(generate_gamma(syn, vocab.preds_flat, decls),
                     *extra_axioms)

    globals = [ decls[x] for x in vocab.globals if t.sorts.ary(x, 1)] #   @ReservedAssignment
    locals  = [ (decls[x0], decls[x]) for x0,x in vocab.locals] # @ReservedAssignment

    if args.u:
        print "*** Using universal invariant inference"
        from mini_pdr import PDR
        if args.p:
            print "*** Use partial models (experimental)"
        if args.gen_enums:
            print "*** Generalize enum values"
        args.o = False # universals currently not supported in opt version

    print "* GLOBALS"
    print globals

    print "* LOCALS"
    print locals

    r_t_analyzer = Relaxed_Trace_Analyzer(init, rho, bad, background, globals, locals, preds,1)
    r_t_analyzer.run()
