# This is a mini-version of PDR specialized to
# EPR style transition systems and using
# a heuristic to extract quantifier-free invariants
# (so far quantifier-free, an extension is to be for quantifiers).

import sys
import heapq
import copy
import itertools
from z3 import *

from z3support.vocabulary import Z3Alphabet, Z3Renaming, Z3TwoVocabulary

class UPDRAnomaly(Exception):
    pass

# Does not handle formulas of the form
# f == Forall(x, g) or f == Exists(x, g)

def is_universal(f):
    if is_quantifier(f):
        if f.is_forall():
            return is_universal(f.body())
        else: # is_exists
            return False
    if is_and(f) or is_or(f):
        return reduce(lambda x,y: x and is_universal(y), f.children(), True)
    if is_not(f):
        return is_existential(f.children()[0])
    if is_app_of(f, Z3_OP_IMPLIES):
        a = f.children()[0]
        b = f.children()[1]
        return is_existential(a) and is_universal(b)
    if is_app_of(f, Z3_OP_IFF):
        a = f.children()[0]
        b = f.children()[1]
        return is_existential(a) and is_universal(b) and \
               is_existential(b) and is_universal(a)
    return True

def is_existential(f):
    if is_quantifier(f):
        if f.is_forall():
            return False
        else: # is_exists
            return is_existential(f.body())
    if is_and(f) or is_or(f):
        return reduce(lambda x,y: x and is_existential(y), f.children(), True)
    if is_not(f):
        return is_universal(f.children()[0])
    if is_app_of(f, Z3_OP_IMPLIES):
        a = f.children()[0]
        b = f.children()[1]
        return is_universal(a) and is_existential(b)
    if is_app_of(f, Z3_OP_IFF):
        a = f.children()[0]
        b = f.children()[1]
        return is_existential(a) and is_universal(b) and \
               is_existential(b) and is_universal(a)
    return True

def is_subset(A, B):
    for x in A:
        if x not in B:
            return False
    return True

def get_id(f):
    return Z3_get_ast_id(f.ctx.ref(), f.as_ast())

_u_id = 0

def next_id():
    global _u_id
    res = _u_id
    _u_id += 1
    return res

def fresh_name_id(s):
    return s + "!" + str(next_id())

def fresh_var_of_sort(s):
    return Const(fresh_name_id('x!' + s.name()), s)

# General purpose SMT utilities
class SMT:
    def check_assumptions(self, s, assumptions):
        preds = [ Const('p$%d' % j, BoolSort()) for j in range(len(assumptions)) ]
        for j in range(len(assumptions)):
            s.add(preds[j] == assumptions[j])
        r = s.check(preds)
        if r == sat:
            return (sat, [])
        preds2assumptions = {}
        for j in range(len(assumptions)):
            preds2assumptions[get_id(preds[j])] = assumptions[j]
        core = self.minimize_core(s)
        core = [preds2assumptions[get_id(c)] for c in core]
        return (unsat, core)
        
    def minimize_core(self, s):
        core = [ c for c in s.unsat_core()]
        ids = { get_id(c):c for c in core }
        seed = [ get_id(c) for c in core]
        current = set(seed)
        for i in seed:
            if i not in current:
                continue
            current.remove(i)
            if unsat == s.check([ids[id] for id in current]):  # @ReservedAssignment
                current = set ([get_id(c) for c in s.unsat_core()])
            else:
                current.add(i)
        return [ids[id] for id in current]  # @ReservedAssignment


class PDR:
    def __init__(self, init, rho, bad, background, globals, locals, relations, # @ReservedAssignment
            universal=False, partial=False, enumsorts=[], gen_enums=False, experiment=False): 
        init_id = get_id(init)
        #init_id = get_id(BoolVal(False))    # seems to work just as well
        self.N = 1
        self.Rs = [set([init_id]),set([])]
        self.Init = init
        self.Rho = rho
        self.Bad = bad
        self.background = background
        self.Globals = globals
        self.Locals = Z3TwoVocabulary.promote(locals)
        self.Relations = relations
        self.Univ = []
        self.ground_properties = []
        self.fmls = { init_id: init }
        self.goals = []
        self.smt = SMT()
        self.counterexample = None
        self.universal = universal
        self.partial = partial
        self.check = True
        self.min_models = False
        self.verbose = False
        self.init_is_universal = is_universal(init)
        self.experiment = experiment

        # OPTIMIZATION STUFF
        self.enumsorts = enumsorts
        self.gen_enums = gen_enums

        self.enumsorts_universes = \
            { get_id(t) : [ t.constructor(i)() for i in range(t.num_constructors()) ]
                for t in self.enumsorts }

        self.enumsorts_subst = []
        for i in self.enumsorts_universes:
            vs = [ (e, fresh_var_of_sort(e.sort())) for e in self.enumsorts_universes[i] ]
            self.enumsorts_subst += vs

        self.collected_constants = set([])
        for u in self.enumsorts_universes.values():
            self.collected_constants |= set(map(get_id, u))
        self.collected_constants |= set(map(get_id, self.Globals))
        self.collected_constants |= set(map(get_id, zip(*self.Locals)[1]))

        # Modify max width for formulas printing.
        # Default values are:
        # max_lines=200, max_width=60, max_indent=40, max_depth=20
        #set_param(max_lines=1000, max_width=200, max_indent=120, max_depth=40)
        set_param(max_lines=1000, max_width=120, max_indent=80, max_depth=40)
        print "init", init
        if self.init_is_universal:
            print "INIT IS UNIVERSAL"
        else:
            print "INIT IS NOT UNIVERSAL"
        print "rho", rho
        print "bad", bad
        print "background", background
        # Restore default values
        set_param(max_lines=200, max_width=60, max_indent=40, max_depth=20)

        self.iteration_count = 0
        self.sat_query_count = 0
        
        self._opt_Rs_last_induction = []
        #for n in self.Relations:
        #    for args1 in self.populate_args(n, 0, [], []):
        #        self.ground_properties += [n(args1)]

    def run(self):
        if not self.check_init():
            return False
        while True:
            self.iteration_count += 1
            inv = self.is_valid()
            #inv = self.is_valid(prune=False)
            if inv:
                print "valid"
                return inv
            if self.unfold():
                self.induction()
                continue
            while self.goals != []:
                if self.verbose:
                    print "* Get a diagram from the queue of goals."
                (i, props) = self.goals[0]                
                if i == 0:
                    for g in self.goals:
                        print "** FRAME %d" % g[0]
                        for l in g[1]:
                            print l
                    #print self.goals
                    print "trace"
                    return False
                if self.verbose:
                    print "* Frame %d: cube to block" % i
                    print props
                    print "* The previous frame F[%d] is" % (i-1)
                    print self.rename(self.R(i-1))
                    sys.stdout.flush()
                if not self.init_is_universal and i == 1:
                    s_init = Solver()
                    s_init.add(self.background)
                    s_init.add(self.Init)
                    (r, core) = self.smt.check_assumptions(s_init, props)
                    if sat == r:
                        print "NO UNIVERSAL INVARIANT EXISTS"
                        print s_init.model()
                        sys.exit()
                s = Solver()
                s.add(self.background)
                s.add(Or(self.Init, And(self.rename(self.R(i-1)), self.Rho)))
                #print self.rename(self.R(i-1))
                self.sat_query_count += 1
                #s.push() # used for inductive generalizations
                (r, core) = self.smt.check_assumptions(s, props)
                #s.pop() # used for inductive generalizations
                ### XXX: comment out the following line in order to use unsat cores
                #core = props
                if unsat == r:
                    if self.verbose:
                        print "* The cube is blocked! Learned a new lemma."
                    if not core:
                        # TODO: check the previous frame for consistency
                        print "THIS SHOULD NEVER HAPPEN! INCONSISTENT FORMALIZATION?"
                    if self.universal:
                        #print core
                        core = self.subst_redundant_vars(core)
                        #print core
                        vs = self.get_vars(core)
                        #core = self.inductive_generalization(s, core, vs)
                        lemma = Not(And(core))
                        if vs:
                            #print vs
                            lemma = ForAll(vs, lemma)
                    else:
                        lemma = Not(And(core)) #Or([Not(e) for e in core])
                        if self.Univ:
                            lemma = ForAll(self.Univ, lemma)

                    lemma_id = get_id(lemma)
                    self.fmls[lemma_id] = lemma

                    if False:
                        s_ = Solver()
                        s_.add(And(self.Init, Not(lemma)))
                        if sat == s_.check():
                            print "BAD LEMMA"
                            print lemma
                            print "BLOCKED CUBE"
                            print props
                            print "*** FRAMES"
                            for j in range(i+1):
                                print "\n"
                                print "*** FRAME % d" % j
                                print self.Rs[j]
                            sys.exit()

                    for j in range(i+1):
                        self.Rs[j].add(lemma_id)
                    print "lemma: ", i, lemma
                    sys.stdout.flush()

                    # OLD COMMENT
                    # simplification: IC3 uses the priority queue and
                    # re-inserts the goal with a higher index as long
                    # as this is below self.N

                    k = 0
                    if self.universal and self.experiment:
                        # propagate lemma forwards
                        for k in range(i,len(self.Rs)-1):
                            print "* TRY INDUCTIVE STRENGTHEN: %d" % k
                            if self.is_inductive(self.fmls[lemma_id], k):
                                print "* Strengthen during the small iteration", (k+1), self.fmls[lemma_id]
                                self.Rs[k+1].add(lemma_id)
                            else:
                                break

                    heapq.heappop(self.goals)
                    #if self.experiment:
                    #    # more optimizations
                    #    if i < k:
                    #        print "* Re-inserting the cube with index %d (%d)" % (k+1, self.N)
                    #        heapq.heappush(self.goals, (k+1, props))
                elif sat == r:
                    m = s.model()
                    #print "****"
                    #print m
                    if self.min_models:
                        m = self.get_min_model([self.background, Or(self.Init,
                            And(self.rename(self.R(i-1)), self.Rho))] + props, m)
                    if self.universal:
                        props1 = self.get_diagram(m, is_transition=True)
                    else:
                        props1 = self.get_properties(m, True)
                    #print i-1, props1
                    if self.verbose:
                        print "* Enqueue the bad cube."
                        sys.stdout.flush()
                    heapq.heappush(self.goals, (i-1, props1))
                else:
                    raise RuntimeError, 'unknown result (%s)' % r

    def check_init(self):
        print "* Check if the initial condition is satisfiable"
        s = Solver()
        s.add(self.background)
        s.add(self.Init)
        if sat == s.check():
            print "OK"
        else:
            print "THE INITIAL STATE IS NOT CONSISTENT"
            return False
        s = Solver()
        s.add(self.background)
        s.add(self.Init)
        s.add(self.Bad)
        self.sat_query_count += 1
        if sat == s.check():
            print "THE INITIAL CONDITION IS NOT SAFE"
            self.counterexample = s.model()
            return False
        return True


    def is_valid(self, prune=True):
        for i in range(self.N):
            if self.Rs[i].issubset(self.Rs[i+1]):
                if prune:
                    if self.verbose:
                        print "* Fixpoint found!"
                        self.print_diffs()
                        print "* Fixpoint R[%d] before pruning =" % i
                        print self.R(i)
                        print
                    self.prune(i)
                    inv = self.to_cnf(self.R(i))
                    print "* Fixpoint R[%d] =" % i
                    print inv
                    print
                else:
                    inv = self.to_cnf(self.R(i))
                return inv
        return None
    
    def to_cnf(self, phi):
        def demorg(phi):
            if is_not(phi) and is_and(phi.arg(0)):
                return simplify(Or(*(Not(x) for x in phi.arg(0).children())))
            elif is_quantifier(phi) and phi.is_forall():
                vars0 = [Const(phi.var_name(i), phi.var_sort(i)) for i in xrange(phi.num_vars())]
                return ForAll(vars0, demorg(phi.body()))
            else:
                return phi
        phi = simplify(phi)
        if is_and(phi):
            return And(*(demorg(x) for x in phi.children()))
        else:
            return demorg(phi)

    def print_diffs(self):
        print
        print "* The initial state:"
        print "========================="
        print self.Init
        print
        print "* R[0] (all the facts ever inferred):"
        print "========================="
        for f in self.Rs[0]:
            print self.fmls[f]
        print
        for i in range(self.N-1):
            print "* R[%d] - R[%d]:" % (i,i+1)
            print "========================="
            for f in self.Rs[i]:
                if not f in self.Rs[i+1]:
                    print self.fmls[f]
            print
        print "* R[%d] (the last frame):" % (self.N-1)
        print "========================="
        for f in self.Rs[self.N-1]:
            print self.fmls[f]
        print

    #
    # A very simplistic version of inductive strengthening.
    # 
    def induction(self):
        last_Rs = self._opt_Rs_last_induction
        for i in range(len(self.Rs)-1):
            if i < len(last_Rs) and last_Rs[i] == self.Rs[i]: continue   # optimization
            Rs_i = self.Rs[i].copy()
            for lemma_id in Rs_i:
                if lemma_id not in self.Rs[i+1] and self.is_inductive(self.fmls[lemma_id], i):
                    print "Strengthen ", (i+1), self.fmls[lemma_id]
                    if self.universal:
                        self.Rs[i+1].add(lemma_id)
                    else:
                        # A naive approach would be:
                        # self.Rs[i+1].add(lemma_id)
                        # But this one does something more sophisticated:
                        self.strengthen(lemma_id, i)
            # MODIFIED
            if self.is_valid(prune=False): break  # optimization
                    
        self._opt_Rs_last_induction = copy.deepcopy(self.Rs)
                        
    def is_inductive(self, lemma, i):
        s = Solver()
        s.add(self.background)
        s.add(Or(self.Init, And(self.rename(And(self.R(i), lemma)), self.Rho)))
        s.add(Not(lemma))
        self.sat_query_count += 1
        return unsat == s.check()
    
    def strengthen(self, lemma_id, i):
        lemma = self.fmls[lemma_id]
        literals = [lemma]
        if is_or(lemma):
            literals = lemma.children()
        old_length = len(literals)
        j = 0
        while j < len(literals):
            save = literals[j]
            literals[j] = BoolVal(False)
            if self.is_inductive(Or(literals), i):
                literals[j] = literals[-1]
                literals.pop()
            else:
                literals[j] = save
                j += 1
        if old_length == len(literals):
            self.Rs[i+1].add(lemma_id)
        else:
            for j in range(i+1):
                self.Rs[j].remove(lemma_id)        
            lemma = Or(literals)
            lemma_id = get_id(lemma)
            self.fmls[lemma_id] = lemma
            for j in range(i+2):
                self.Rs[j].add(lemma_id)

    def prune(self, i):
        removed = []
        for j in self.Rs[i]:
            s = Solver()
            s.add(self.background)
            for id in self.Rs[i]:  # @ReservedAssignment
                if j == id:
                    s.add(Not(self.fmls[id]))
                elif id in removed:
                    pass
                else:
                    s.add(self.fmls[id])
            self.sat_query_count += 1
            if unsat == s.check():
                removed += [j]
        self.Rs[i] = set([ j for j in self.Rs[i] if j not in removed])

    def unfold(self):
        if self.verbose:
            print "* Unfold is called for the frame %d" % self.N
            print "* Check if F[%d] has a bad state" % self.N
            print "* Current F[%d]:" % self.N
            print self.R(self.N)
            sys.stdout.flush()
        s = Solver()
        s.add(self.background)
        s.add(self.Bad)
        s.add(self.R(self.N))
        self.sat_query_count += 1
        if unsat == s.check():
            self.N += 1
            self.Rs += [set([])]
            if self.verbose:
                print "* No bad state! Add a new empty frame."
                print "* The last frame index N = %d" % self.N
                sys.stdout.flush()
            return True
        if self.verbose:
            print "* Bad state found"
        m = s.model()
        #print "*** We are at the frontier."
        #print "*** Here is a new bad model to block"
        #print m
        if self.min_models:
            print "Counterexample model at the frontier"
            print m
            m = self.get_min_model([self.background, self.Bad, self.R(self.N)], m)
            print "Minimal model"
            print m
        if self.universal:
            props = self.get_diagram(m, is_transition=False)
        else:
            props = self.get_properties(m, False)
        if self.verbose:
            print "* Cube of the bad state is "
            print props
            sys.stdout.flush()
        heapq.heappush(self.goals, (self.N, props))
        return False

    def get_min_model(self, fs, m):
        max_size = self.size_of_model(m)
        sort = m.sorts()[0]
        print max_size
        for size in range(1, max_size + 1):
            s = Solver()
            for f in fs:
                s.add(f)
            vs = [ Const('v_%i' % i, sort) for i in range(size) ]
            z = Const('z_', sort)
            #f = ForAll(vs, (ForAll(z, Or([ z == v for v in vs ]))))
            f = ForAll(z, Or([ z == v for v in vs ]))
            print f
            s.add(f)
            if unsat == s.check():
                print unsat
                continue
            return s.model()

    def size_of_model(self, m):
        return len(m.get_universe(m.sorts()[0]))
        #print "# Extracting the cube from the given model"
        #print m
        #print m.decls()
        #print m.sorts()
        #print "universes:"
        #for s in m.sorts():
        #    print m.get_universe(s)

    def R(self, i):
        fmls = [self.fmls[id] for id in self.Rs[i]]  # @ReservedAssignment
        if fmls == []:
            return BoolVal(True)
        return And(fmls)

    #
    # Return set of EPR properties associated with 'm'
    # when projected to current state variables.
    # really simplistic implementation (equalities can be done
    # more efficiently).
    # This is the quantifier-free version (so not all models
    # will be extended to real counter-examples)
    #
    def toggle_pred(self, m, p, q):
        p_eval = m.eval(p)
        # print p_eval
        if is_true(p_eval):
            return q
        if is_app_of(q, Z3_OP_EQ):
            return (q.arg(0) != q.arg(1))  # looks nicer
        return (Not(q))

    def insert_value(self, vl, x, roots, ps):
        v = get_id(vl)
        if is_true(vl):
            ps += [x]
        elif is_false(vl):
            ps += [Not(x)]
        elif v not in roots:
            roots[v] = x
        else:       # equal terms always have the same sort
            y = roots[v]
            ps += [y == x]
        
    def get_properties(self, m, is_transition):
        roots = {}
        ps = []
        for (x0, x) in self.Locals:
            if not is_const(x): continue
            if not is_transition:
                x0 = x
            vl = m.eval(x0)
            self.insert_value(vl, x, roots, ps)
        for y in self.Globals:
            vl = m.eval(y)
            self.insert_value(vl, y, roots, ps)
        # we can also use distinct clause.
        for v in roots:
            for w in roots:
                if v != w:
                    x, y = roots[v], roots[w]
                    if get_id(x.sort()) == get_id(y.sort()):
                        ps += [x != y]
        if is_transition:
            ps += [self.toggle_pred(m, self.rename(prop), prop)
                   for prop in self.ground_properties]
        else:
            ps += [self.toggle_pred(m, prop, prop) 
                   for prop in self.ground_properties]

        return ps

    def inductive_generalization(self, s, assumptions, vs):
        print s
        print "*** Inductive strengthening for the cube"
        print assumptions
        preds = [ Const('p$_$%d' % j, BoolSort()) for j in xrange(len(assumptions)) ]
        for j in xrange(len(assumptions)):
            s.add(preds[j] == assumptions[j])
        r = s.check(preds)
        if r == sat:
            raise UPDRAnomaly
        preds2assumptions = {}
        for j in xrange(len(assumptions)):
            preds2assumptions[get_id(preds[j])] = assumptions[j]
        print preds2assumptions
        #core_preds = [ preds2assumptions[get_id(c)] for c in s.unsat_core() ]
        core_preds = s.unsat_core()
        print core_preds
        ids = { get_id(c) : c for c in core_preds } # maps ids to boolean predicates of the unsat core
        seed = [ get_id(c) for c in core_preds ]
        current = set(seed)
        def cube_of_current():
            cur_preds = ( ids[id] for id in current ) # @ReservedAssignment
            return And([ preds2assumptions[get_id(i)] for i in cur_preds ])
        for i in seed:
            if i not in current:
                continue
            current.remove(i)
            if not current:
                current.add(i)
                break
            cube = self.rename(cube_of_current())
            print "cube of current"
            print cube
            f_current = ForAll(vs, Not(cube)) if vs else Not(cube)
            print "f current"
            print f_current
            s.push()
            s.add(f_current)
            #print s
            if unsat == s.check([ ids[id] for id in current ]):  # @ReservedAssignment
                print "PROGRESS IN INDUCTIVE STRENGTHENING!!!"
                current = set([ get_id(c) for c in s.unsat_core() ])
            else:
                current.add(i)
            s.pop()
        cur_preds = [ ids[id] for id in current ]  # @ReservedAssignment
        core = [ preds2assumptions[get_id(c)] for c in cur_preds ]
        return core

    # Subtitute variables occuring in equalities of the form: c = x
    def subst_redundant_vars(self, fs):
        subst = [ (f.arg(1), f.arg(0)) for f in fs if is_eq(f) ]
        fs = itertools.imap(lambda f: substitute(f, *subst), fs)
        fs = itertools.ifilter(lambda f: not is_eq(f) or get_id(f.arg(0)) != get_id(f.arg(1)), fs)
        return list(fs)

    def subst_redundant_vars_old(self, fs):
        subst = [ (f.arg(1), f.arg(0)) for f in fs if is_eq(f) ]
        fs = map(lambda f: substitute(f, *subst), fs)
        fs = filter(lambda f: not is_eq(f) or get_id(f.arg(0)) != get_id(f.arg(1)), fs)
        return fs

    def get_vars_old(self, fs):
        enums = set([ get_id(c) for u in self.enumsorts_universes.itervalues() for c in u ])
        id2vars = {}
        for f in fs:
            #print f
            if is_app(f):
                if is_not(f):
                    f = f.arg(0)
                for i in range(f.num_args()):
                    t = f.arg(i)
                    #print "arg %d: %s" % (i,t)
                    c = t if is_const(t) else t.arg(0)
                    ci = get_id(c)
                    if not ci in enums:
                        id2vars[ci] = c
            else:
                raise TypeError
        for x in self.Globals:
            if get_id(x) in id2vars:
                del id2vars[get_id(x)]
        for x0,x in self.Locals:
            if get_id(x0) in id2vars:
                del id2vars[get_id(x0)]
            if get_id(x) in id2vars:
                del id2vars[get_id(x)]
        return id2vars.values()

    def get_vars(self, fs):
        id2vars = {}
        for f in fs:
            #print f
            if is_app(f):
                if is_not(f):
                    f = f.arg(0)
                for i in range(f.num_args()):
                    t = f.arg(i)
                    #print "arg %d: %s" % (i,t)
                    c = t if is_const(t) else t.arg(0)
                    id2vars[get_id(c)] = c
            else:
                raise TypeError
        for i in self.collected_constants:
            if i in id2vars:
                del id2vars[i]
        return id2vars.values()

    def get_diagram(self, m, is_transition):
        if False:
            print "# Extracting the cube from the given model"
            print "IS_TRANSITION = ",
            print is_transition
            print m
            print "declarations:"
            print m.decls()
            print "sorts:"
            print m.sorts()
            print "universes:"
            for s in m.sorts():
                print m.get_universe(s)

        decl_ids = map(get_id, m.decls())
        eqs = []

        # Globals are constant symbols or functional symbols
        #print "globals"
        for x in self.Globals:
            if is_const(x):
                if self.partial:
                    if get_id(x.decl()) in decl_ids:
                        eqs.append(x == m.eval(x))
                    else:
                        sort = x.sort()
                        univ = self.enumsorts_universes[get_id(sort)] \
                                if get_id(sort) in self.enumsorts_universes \
                                else m.get_universe(sort)
                        eqs.append(Or([ x == e for e in univ ]))
                else:
                    eqs.append(x == m.eval(x, model_completion = True))
                # Both for full and partial diagrams, compute values for all the constants
                #eqs.append(x == m.eval(x, model_completion = True))
            if is_func_decl(x):
                doms = (x.domain(i) for i in range(x.arity()))
                # TODO: check that d is in m.sorts()
                univs = ( self.enumsorts_universes[get_id(d)]
                            if get_id(d) in self.enumsorts_universes
                            else m.get_universe(d)
                            for d in doms )
                # TODO: I think all global functional symbols _must_ be interpreted as well
                if self.partial:
                    if get_id(x) in decl_ids:
                        eqs += [ x(t) == m.eval(x(*t)) for t in itertools.product(*univs) ]
                    else:
                        print "%s is not in %s" % (str(x), str(m.decl()))
                else:
                    eqs += [ x(t) == m.eval(x(*t), model_completion = True)
                             for t in itertools.product(*univs) ]
        #print eqs

        #print "locals"
        for x0, x in self.Locals:
            if not is_const(x):
                continue
            # skip nullary predicates
            if x.sort() == BoolSort():
                continue
            if not is_transition:
                x0 = x
            if self.partial:
                if get_id(x0.decl()) in decl_ids:
                    eqs.append(x == m.eval(x0))
                else:
                    sort = x0.sort()
                    univ = self.enumsorts_universes[get_id(sort)] \
                            if get_id(sort) in self.enumsorts_universes \
                            else m.get_universe(sort)
                    eqs.append(Or([ x == e for e in univ ]))
            else:
                eqs.append(x == m.eval(x0, model_completion = True))
            # Both for full and partial diagrams, compute values for all the constants
            #eqs.append(x == m.eval(x0, model_completion = True))
        #print "EQS FOR GLOBALS AND LOCALS"
        #print eqs

        #print "relations"
        evals = {} 
        evals0 = {} # for nullary predicates (boolean constants)
        # Compute values of the predicates on the elements of the model
        #print "* Compute values of the predicates in the model"
        for r in self.Relations:
            #print r
            r0 = self.rename(r) if is_transition else r
            #print r0
            if is_const(r0): # nullary predicate
                if self.partial:
                    if get_id(r0.decl()) in decl_ids:
                        evals0[get_id(r)] = m.eval(r0)
                else:
                    evals0[get_id(r)] = m.eval(r0, model_completion = True)
            else:
                doms = [ r0.domain(i) for i in range(r0.arity()) ]
                univs = ( self.enumsorts_universes[get_id(d)]
                            if get_id(d) in self.enumsorts_universes
                            else m.get_universe(d)
                            for d in doms )
                #univs = [ x for x in univs ]
                #print univs
                tuples = itertools.product(*univs)
                #tuples = [ x for x in tuples ]
                #print tuples
                if self.partial:
                    if get_id(r0) in decl_ids:
                        evals[get_id(r)] = [ (t, m.eval(r0(*t))) for t in tuples ]
                else:
                    evals[get_id(r)] = \
                        [ (t, m.eval(r0(*t), model_completion = True)) for t in tuples ]

        #print "* Construct a cube for the model"
        l = [ r(*t) if is_true(b) else Not(r(*t))
                for r in self.Relations
                if get_id(r) in evals
                for t, b in evals[get_id(r)] ]
        l += [ r if is_true(evals0[get_id(r)]) else Not(r)
                for r in self.Relations
                if get_id(r) in evals0 ]

        if False:
            for r in self.Relations:
                if get_id(r) in evals:
                    for t, b in evals[get_id(r)]:
                        if not is_true(b) and not is_false(b):
                            print "BAD VALUE"
                            print b
                            sys.exit()

        chain = itertools.chain
        imap = itertools.imap
        starmap = itertools.starmap
        combinations = itertools.combinations

        neq = lambda x,y: x != y
        distinct = chain( *(starmap(neq, combinations(m.get_universe(s), 2)) for s in m.sorts()) )

        # Renaming the constants
        # TODO: optimize
        #vs  = list(chain.from_iterable(( m.get_universe(d) for d in m.sorts())))
        #vs1 = ( fresh_var_of_sort(v.sort()) for v in vs )
        #subst = list(itertools.izip(vs, vs1))
        vs = chain.from_iterable(( m.get_universe(d) for d in m.sorts() ))
        fresh_dup = lambda v: (v, fresh_var_of_sort(v.sort()))
        subst = list(itertools.imap(fresh_dup, vs))
        if self.gen_enums:
            subst += self.enumsorts_subst

        l        = imap(lambda p: substitute(p, *subst), l)
        eqs      = imap(lambda p: substitute(p, *subst), eqs)
        distinct = imap(lambda p: substitute(p, *subst), distinct)
        enum_eqs = ( e == x for e,x in self.enumsorts_subst ) \
                        if self.gen_enums else iter([])

        res = chain(l, eqs, distinct, enum_eqs)
        #res = l + eqs
        #res += distinct
        #res += enum_eqs
        #print "Result:"
        #res = list(res)
        #print res
        return list(res)

    # TODO: populate_args is not used
    def populate_args(self, r, i, args, res):
        if i == r.arity():
            return res + [args]
        for _, x in self.Locals:
            if get_id(x.sort()) == get_id(r.domain(i)):
                res = self.populate_args(r, i+1, args + [x], res)
        for y in self.Globals:
            if get_id(y.sort()) == get_id(r.domain(i)):
                res = self.populate_args(r, i+1, args + [y], res)
        return res

    def rename(self, term):
        return self.Locals.rename_past_tense(term)

    def verify(self, inv):
        correct = True

        # 1) check that inv satisfies the initial condition
        s = Solver()
        s.add(self.background)
        s.add(self.Init)
        s.add(Not(inv))
        if sat == s.check():
            print "* The inferred formula may not hold in the initial condition"
            correct = False

        # 2) check that inv is preserved by the transition relation
        s = Solver()
        s.add(self.background)
        s.add(self.rename(inv))
        s.add(self.Rho)
        s.add(Not(inv))
        if sat == s.check():
            print "* The inferred formula may be not preserved by the transition relation"
            correct = False

        # 3) check that inv is disjoint from the set of bad states
        s = Solver()
        s.add(self.background)
        s.add(inv)
        s.add(self.Bad)
        if sat == s.check():
            print "* The inferred formula is not safe"
            correct = False

        if correct:
            print "* The inferred formula is an inductive invariant!"
        return correct


def nPlus(x, y):
    return And(x != y, n(x, y))


if __name__ == '__main__':
    A = DeclareSort('A')
    B = BoolSort()
    n = Function('n', A, A, B)
    
    x, y, l, h, x0, z = Consts('x y l h x0 z', A)
    init    = And(x == h, Implies(n(h, y), nPlus(y, l)))
    rho     = And(nPlus(x0, x), ForAll([z], Implies(nPlus(x,z),n(x0,z))))
    bad     = And(x == y, x == l)
    background = ForAll([z], n(z,z))
    globals = [y, l, h]    # @ReservedAssignment
    locals  = [(x0,x)]  # @ReservedAssignment
    print globals
    print locals
    print rho
    print background
    print init
    print bad
    
    pdr = PDR(init, rho, bad, background, globals, locals, [n])
    pdr.run()
