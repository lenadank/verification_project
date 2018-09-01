# This is a mini-version of PDR specialized to
# EPR style transition systems and using
# a heuristic to extract quantifier-free invariants
# (so far quantifier-free, an extension is to be for quantifiers).

from z3 import *
import heapq
import copy
from z3support.vocabulary import Z3Alphabet, Z3Renaming, Z3TwoVocabulary


def is_subset(A, B):
    for x in A:
        if x not in B:
            return False
    return True

def mk_not(e):
    if is_not(e):
       return e.arg(0)
    else:
       return Not(e)

def mk_or(es):
    if len(es) == 0: 
       return False
    if len(es) == 1:
       return es[0]
    return Or(es)

def mk_and(es):
    if len(es) == 0: 
       return BoolVal(True)
    if len(es) == 1:
       return es[0]
    return And(es)

def get_id(f):
    return Z3_get_ast_id(f.ctx.ref(), f.as_ast())


# General purpose SMT utilities
class SMT:
    def __init__(self):
        self.index = 0
        self.proxies2fml = {}

    def is_pure(self, fml):
        if is_not(fml):
           return self.is_pure(fml.arg(0))
        if not is_app(fml):
           return False
        if fml.decl().kind() != Z3_OP_UNINTERPRETED:
           return False
        return len(fml.children()) == 0

    def fml2proxy(self, s, proxies, fml):
        if self.is_pure(fml):
           self.proxies2fml[get_id(fml)] = fml
           return fml
        fid = get_id(fml)
        if fid in proxies:
           return proxies[fid]
        p = Const('p%d' % self.index, BoolSort())
        self.index += 1
        proxies[fid] = p
        self.proxies2fml[get_id(p)] = fml
        s.add(Implies(p, fml))
        return p

    def proxy2fml(self, proxy):
        fid = get_id(proxy)
        return self.proxies2fml[fid]

    def check_assumptions(self, s, proxies, assumptions):
        preds = [ self.fml2proxy(s, proxies, fml) for fml in assumptions ]
        r = s.check(preds)
        if r == sat:
           return (sat, [])
        core = self.minimize_core(s)
        core = [self.proxy2fml(c) for c in core]
        return (unsat, core)
        

    # Basic core minimization
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
    def __init__(self, init, rho, bad, background, globals, locals, relations):  # @ReservedAssignment
        init_id = get_id(init)
        #init_id = get_id(BoolVal(False))    # seems to work just as well
        self.N = 1
        self._Rs = [set([init_id]),set([])]
        self._solvers = []
        self._proxies = []
        self.Pre = Bool("pre")
        self.Init = init
        self.Rho = rho
        self.Bad = bad
        self.background = background
        self.Globals = globals
        self.Locals = Z3TwoVocabulary.promote(locals)
        self.Relations = relations
        self.Univ = []
        self.ground_properties = []
        self.fmls = { init_id: init}
        self.goals = []
        self.smt = SMT()
        self.counterexample = None
        print "init", init
        print "rho", rho
        print "bad", bad  
        self.add_solver()
        self.add_solver()
	self._solvers[0].add(self.rename(init))      
        
        self.iteration_count = 0
        self.sat_query_count = 0
        
        self._opt_Rs_last_induction = []
        #for n in self.Relations:
        #    for args1 in self.populate_args(n, 0, [], []):
        #        self.ground_properties += [n(args1)]


    def add_solver(self):
        self._solvers += [Solver()]
        self._solvers[-1].add(self.background)
        self._solvers[-1].add(Or(self.Init, And(self.Pre, self.Rho)))
        self._proxies += [{}]

    def assert_fml(self, i, fml):
        fml_id = get_id(fml)
        for j in range(i+1):
           if fml_id not in self._Rs[j]:
              self._Rs[j].add(fml_id)
              self._solvers[j].add(Implies(self.Pre, self.rename(fml)))
        self.fmls[fml_id] = fml 

    def run(self):
        if not self.check_init():
            return False
        min_level = self.N            # skip levels below min_level during induction strengthening.
        unfoldSolver = Solver()
        unfoldSolver.add(self.Bad)
        unfoldSolver.add(self.background)

        while True:
            self.iteration_count += 1
            inv = self.is_valid()
            if inv:
                print "valid"
                return inv
            if self.unfold(unfoldSolver):
                self.induction(min_level)
                unfoldSolver = Solver()
                unfoldSolver.add(self.Bad)
                unfoldSolver.add(self.background)
                continue
            min_level = self.N
            while self.goals != []:
                (i, props) = self.goals[0]                
                if i == 0:
                    for g in self.goals: print g
                    #print self.goals
                    print "trace"
                    return False
                if i < min_level:
                   min_level = i
                s = self._solvers[i-1]
                self.sat_query_count += 1
                (r, core) = self.smt.check_assumptions(s, self._proxies[i-1], props)
                if unsat == r:
                    lemma = mk_or([mk_not(e) for e in core])
                    if self.Univ:
                        lemma = ForAll(self.Univ, lemma)
                    self.assert_fml(i, lemma)
                    print "lemma: ", i, lemma
                    # simplification: IC3 uses the priority queue and
                    # re-inserts the goal with a higher index as long
                    # as this is below self.N
                    heapq.heappop(self.goals)
                elif False and sat == r and self.is_inductively_blocked(s, props):
                    print "Inductively blocked"
                    not_props = [mk_not(p) for p in props]
                    stronger, literals = self.try_strengthen_literals(not_props, i-1)
                    lemma = mk_or(literals)
                    if self.Univ:
                        lemma = ForAll(self.Univ, lemma)
                    self.assert_fml(i, lemma)
                    heapq.heappop(self.goals)
                elif sat == r:
                    m = s.model()
                    props1 = self.get_properties(m, True)
                    #print i-1, props1
                    heapq.heappush(self.goals, (i-1, props1))
                else:
                    raise RuntimeError, 'unknown result (%s)' % r

    def check_init(self):
        s = Solver()
        s.add(self.background)
        s.add(self.Init)
        s.add(self.Bad)
        self.sat_query_count += 1
        if sat == s.check():
            print "initial condition is not safe"
            self.counterexample = s.model()
            return False
        return True


    def is_valid(self, prune=True):
        for i in range(self.N):
            if self._Rs[i].issubset(self._Rs[i+1]):
                if prune:
                    self.prune(i)
                    print "R[%d] =" % i
                    print self.R(i)
                return self.R(i)
        return None

    #
    # A very simplistic version of inductive strengthening.
    # 
    def induction(self, min_level):
        last_Rs = self._opt_Rs_last_induction
        for i in range(min_level-1, len(self._Rs)-1):
            if i < len(last_Rs) and last_Rs[i] == self._Rs[i]: continue   # optimization
            Rs_i = self._Rs[i].copy()
            for lemma_id in Rs_i:
                if lemma_id not in self._Rs[i+1]:
                    self.try_strengthen(lemma_id, i)
            if self.is_valid(prune=False): break  # optimization
                    
        self._opt_Rs_last_induction = copy.deepcopy(self._Rs)
                        
    def is_inductive(self, lemma, i):        
        s = self._solvers[i]
        s.push()
        s.add(Implies(self.Pre, self.rename(lemma)))
        s.add(Not(lemma))
        self.sat_query_count += 1
        r = (unsat == s.check())
        s.pop()
        return r
    
    def try_strengthen_literals(self, literals, i):
        old_length = len(literals)
        j = 0
        while j < len(literals):
            save = literals[j]
            literals[j] = BoolVal(False)
            if self.is_inductive(mk_or(literals), i):
                literals[j] = literals[-1]
                literals.pop()
            else:
                literals[j] = save
                j += 1
        return old_length > len(literals), literals


    def try_strengthen(self, lemma_id, i):
        lemma = self.fmls[lemma_id]
        if False and is_or(lemma):   ## NB. Inductive strengthening is disabled!
           literals = lemma.children()
           stronger, literals = self.try_strengthen_literals(literals, i)
           if stronger:
              self.assert_fml(i+1, mk_or(literals))
              return
        if self.is_inductive(lemma, i):
           print "Strengthen ", (i+1), lemma
           self.assert_fml(i+1, lemma)

    def is_inductively_blocked(self, s, props):
        s.push()
        s.add(Implies(self.Pre, Not(Or(props))))
        for p in props:
            s.add(p)            
        r = s.check()
        s.pop()
        return r == unsat
 
    # We use a local solver for the pruning step.
    # Pruning is about identifying relative redundancies.
    
    def prune(self, i):
#       self.unit_prune(i)
        removed = []
        s = Solver()
        s.add(self.background)
        for j in self._Rs[i]:
            s.push()
            for id in self._Rs[i]:  # @ReservedAssignment
                if j == id:
                    s.add(Not(self.fmls[id]))
                elif id in removed:
                    pass
                else:
                    s.add(self.fmls[id])
            self.sat_query_count += 1
            if unsat == s.check():
                print "Pruned ", self.fmls[j] #, " by ", [self.fmls[id] for id in self._Rs[i] if id != j ], self.background
                removed += [j]
            s.pop()
        self._Rs[i] = set([ j for j in self._Rs[i] if j not in removed])

    #
    # TBD: We can possibly a Z3 tactic that makes this more efficient.
    # Z3's PDR implementation uses the "unit-subsumption-tactic"
    # but we have to be careful about formulas switching Id's   
    # It is also not clear if it pays to maintain also the background.
    # seems one could just reset the solver state after a round of pruning.
    #

    def unit_prune(self, i):
        tac = Tactic('unit-subsume-simplify')
        g = Goal()
        for j in self._Rs[i]:
            g.add(self.fmls[j])
        subgoal = tac(g)    
        s = Solver()
        self._solvers[i] = s
        self._Rs[i] = set([])
        s.add(self.background)   
        s.add(Or(self.Init, And(self.Pre, self.Rho)))
        for fml in subgoal[0]:
            fid = get_id(fml)
            self._Rs[i].add(fid)
            s.add(Implies(self.Pre, self.rename(fml))) 
        

    def unfold(self, s):
        s.add(self.R(self.N))
        self.sat_query_count += 1
        if unsat == s.check():
            self.N += 1
            self._Rs += [set([])]
            self.add_solver()
            return True
        m = s.model()
        heapq.heappush(self.goals, (self.N, self.get_properties(m, False)))
        return False

    def R(self, i):
        fmls = [self.fmls[id] for id in self._Rs[i]]  # @ReservedAssignment
        if fmls == []:
            return True
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


    def run_alpha(self):
        r = BoolVal(False)
        s = Solver()
        s.add(self.background)
        while True:
            vc = And(Or(self.Init, And(self.rename(r), self.Rho)), Not(r))
            s.push()
            s.add(vc)
            self.sat_query_count += 1
            r = s.check()
            if r == sat:		
        	m = s.model()
        	props = self.get_properties(m, False)
        	props = self.prime_implicant(vc, props)
        	print props
        	r = Or(r, mk_and(props))
            s.pop()
            if r == unsat:
        	break
            if r == unknown:
        	return None
        # check if the property holds
        vc = And(r, self.Bad)
        s.push()
        r = s.check()
        s.pop()
        return r == unsat

    # A suitable notion of prime implicant is a question.
    @classmethod
    def prime_implicant(cls, fml, literals):
        return literals
	
          
def nPlus(x,y):
    return And(x != y, n(x,y))

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
