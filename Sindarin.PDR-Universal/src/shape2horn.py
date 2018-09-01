from z3 import *


def replace(Q, n, subst):
    if is_select(Q) and is_select(Q.arg(0)) and Q.arg(0).arg(0).eq(n):
	return subst(Q.arg(0).arg(1), Q.arg(1))
    if is_app(Q) and is_and(Q):
	return And([ replace(arg, n, subst) for arg in Q.children()])
    if is_app(Q) and is_or(Q):
	return Or([ replace(arg, n, subst) for arg in Q.children()])
    if is_app(Q):
	args = [ replace(arg, n, subst) for arg in Q.children()]
	return Q.decl()(args)
    if is_quantifier(Q):
	vars = [ Const(Q.var_name(i), Q.var_sort(i)) for i in range(Q.num_vars())]
	vars.reverse()
	new_body = replace(Q.body(), n, subst)
	if Q.is_forall():
	    return ForAll(vars, new_body)
	else:
	    return Exists(vars, new_body)
    if is_var(Q):
	return Q
    print "Not handled", Q
    return Q

def next(n, x, y):
    return Select(Select(n, x), y)

def mk_fresh(s):
    ctx = s.ctx
    return ExprRef(Z3_mk_fresh_const(ctx.ref(), "X", s.ast), ctx)

class Assume:
   # Assume phi
   def __init__(self, phi):
       self.phi = phi
   
   def wp(self, Q):
       return Implies(self.phi, Q)

class Assert:
   # Assert phi
   def __init__(self, phi):
       self.phi = phi
   
   def wp(self, Q):
       return And(self.phi, Q)


class XnEQY:
   # x.n := y
   def __init__(self, x, n, y):
       self.x = x
       self.y = y
       self.n = n

   def N(self, x, y):
       return next(self.n, x, y)

   def subst(self, a, b):
       return Or(self.N(a, b), 
                 And(self.N(a, self.x), self.N(self.y, b)))

   def wp(self, Q):
       return And(Not(self.N(self.y, self.x)), 
                  replace(Q, self.n, self.subst))

class XEQYn:
   # x := y.n
   def __init__(self, x, n, y):
       self.x = x
       self.y = y
       self.n = n

   def N(self, x, y):
       return next(self.n, x, y)

   def subst(self, a, b):
       return Or(self.N(a, b), 
                 And(self.N(a, self.x), self.N(self.y, b)))

   def p_next1(self, s, t):
       return And(self.N(s, t), s != t)

   def p_next(self, s, t):
       g = mk_fresh(s.sort())
       return And(self.p_next1(s, t), 
                  ForAll(g, Implies(self.p_next1(s, g), self.N(t, g))))

   def wp(self, Q):
       a = mk_fresh(self.x.sort())
       p = self.p_next(self.y, a)
       Q = substitute(Q, (self.x, a))
       return ForAll(a, Implies(p, Q))

class XEQY:
   # x := y
   def __init__(self, x, y):
       self.x = x
       self.y = y

   def wp(self, Q):
       return substitute(Q, (self.x, self.y))


class XNew:
   # x := new
   def __init__(self, x, n, vars):
       self.x = x
       self.n = n
       self.vars = vars

   def N(self, x, y):
       return next(self.n, x, y)

   def wp(self, Q):
       a = mk_fresh(self.x.sort())
       pre = And([ Not(self.N(p, a)) for p in self.vars])
       post = substitute(Q, (self.x, a))
       return ForAll([a], Implies(pre, post))
       
class XNextNull:
   # x.n := null
   def __init__(self, x, n):
       self.x = x
       self.n = n

   def N(self, x, y):
       return next(self.n, x, y)

   def subst(self, a, b):
       return And(self.N(a, b), 
                  Or(Not(self.N(a, self.x)), self.N(b, self.x)))

   def wp(self, Q):
       return replace(Q, self.n, self.subst)


class TheoryOfNextStar:
    def __init__(self):
	self.n = []

    def add_next(self, n):
	self.n += [n]

    def axiomatize(self):
	return And([self.axiomatize1(n) for n in self.n])

    def axiomatize1(self, n):
	return And([self.reflexivity(n), self.transitivity(n), self.linear(n)])

    def reflexivity(self, n):
	x = Const('x', n.domain())
	return ForAll([x], next(n, x, x))

    def transitivity(self, n):
	x, y, z = Consts('x y z', n.domain())
	return ForAll([x,y,z], Implies(And(next(n, x, y), next(n, y, z)), next(n, x, z)))

    def linear(self, n):
	x, y, z = Consts('x y z', n.domain())
	return ForAll([x,y,z], Implies(And(next(n, z, x), next(n, z, y)), Or(next(n, x, y), next(n, y, x))))
        
	
def wp(assigns, Q):
    if assigns == []:
	return Q
    else:
	return assigns[0].wp(wp(assigns[1:], Q))
    

# Some beautification routines:

def flatten_and(a):
    if is_app_of(a, Z3_OP_IMPLIES):
       b = flatten_and(a.arg(1))
       if is_app_of(b, Z3_OP_IMPLIES):
          return Implies(flatten_and(And(a.arg(0),b.arg(0))), b.arg(1))
       return Implies(flatten_and(a.arg(0)), b)
    if is_app_of(a, Z3_OP_AND):
       args = []
       for c in a.children():
           x = flatten_and(c)
           if is_app_of(x, Z3_OP_AND):
              args += x.children()
           elif is_true(x):
              pass
           else:
              args += [x]
       return And(args)    
    return a

##
# Transform:
#   B -> forall u (forall w (J)) -> K
# Into:
#   forall u (B & forall w J(u)) -> K
##

def hoist_implies(x, y):
    b = hoist_forall(y)
    if is_quantifier(b) and b.is_forall():
       vars = [ Const(b.var_name(i), b.var_sort(i)) for i in range(b.num_vars())]
       vars.reverse()
       new_body = substitute_vars(b.body(), *vars)
       return ForAll(vars, flatten_and(Implies(x, new_body)))
    return flatten_and(Implies(x, b))
def hoist_forall(a):
    if is_app_of(a, Z3_OP_IMPLIES):
       return hoist_implies(a.arg(0), a.arg(1))
    if is_app_of(a, Z3_OP_OR) and is_app_of(a.arg(0), Z3_OP_NOT):
       return hoist_implies(a.arg(0).arg(0), a.arg(1))
    if is_quantifier(a) and a.is_forall():
       vars0 = [ Const(a.var_name(i), a.var_sort(i)) for i in range(a.num_vars())]
       vars0.reverse()
       b = substitute_vars(a.body(), *vars0)
       b = hoist_forall(b)
       if is_quantifier(b) and b.is_forall():
          b = hoist_forall(b)
          vars1 = [ Const(b.var_name(i), b.var_sort(i)) for i in range(b.num_vars())]
          vars1.reverse()
          b = substitute_vars(b.body(), *vars1)
          return ForAll(vars0 + vars1, b)
       else:
          return ForAll(vars0, b)             
    return flatten_and(a)

def hoist_horn(e):
    if is_quantifier(e) and e.is_forall():
       vars = [ Const(e.var_name(i), e.var_sort(i)) for i in range(e.num_vars()) ]
       vars.reverse()
       new_body = substitute_vars(e.body(), *vars)
       return [ ForAll(vars, b) for b in hoist_horn(new_body) ]
    if is_app_of(e, Z3_OP_IMPLIES):
       return [ Implies(e.arg(0), b) for b in hoist_horn(e.arg(1)) ]
    if is_and(e):
       return [ b for ch in e.children() for b in hoist_horn(ch) ]
    return [e]

def blast_horn(b):
    if is_quantifier(b) and b.is_forall():
       vars = [ Const(b.var_name(i), b.var_sort(i)) for i in range(b.num_vars())]
       vars.reverse()
       new_body = substitute_vars(b.body(), *vars)
       new_body = blast_implies(vars, new_body)
       return ForAll(vars, new_body)
    else:
       return b

def blast_implies(vars, b):
    if is_app_of(b, Z3_OP_IMPLIES):
       return Implies(blast_body(vars, b.arg(0)), blast_implies(vars, b.arg(1)))
    return b

def blast_body(vars, b):
    if is_app_of(b, Z3_OP_AND):
       return And([ blast_body(vars, e) for e in b.children()])
    if is_app_of(b, Z3_OP_OR):
       return Or([ blast_body(vars, e) for e in b.children()])
    if is_quantifier(b) and b.is_forall():
       fmls = []
       for bound in enumerate_bound(vars, b):
           bound.reverse()
           fmls += [ substitute_vars(b.body(),*bound) ]
       return blast_body(vars, And(fmls))
    return b


def enumerate_bound(vars, b):
    nv = b.num_vars()
    bound = [ 0 for i in range(nv) ]
    return enumerate_bound_aux(vars, b, 0, bound, [])

def enumerate_bound_aux(vars, b, i, bound, result):
    nv = b.num_vars()
    if i == nv:
       return [[b for b in bound]] + result
    s1 = b.var_sort(i)
    for v in vars:
        s2 = v.sort()
        if s1.eq(s2):
           bound[i] = v
           result = enumerate_bound_aux(vars, b, i+1, bound, result)
    return result


#x,y,z,v1,v2 = Ints('x y z v1 v2')
#a = Bool('a')
#P = Function('P', IntSort(), IntSort(), BoolSort())
#for b in enumerate_bound([x,y,a,z], ForAll([v1,v2], P(v1,v2))):
#    print b
# [x, y, a, z] & [v1, v2] -> [x,x],[y,x],[z,x],[x,y],[y,y],[z,y],[x,z],[y,z],[z,z]
#
# print blast_horn(ForAll([x,y,a],Implies(ForAll([v1,v2], P(v1,v2)), P(x,x))))
     

def normalize(a):
    return hoist_forall(a)

th = TheoryOfNextStar()

def ImpliesTh(a, b):
    return Implies(And(th.axiomatize(), a), b)

def mk_benchmark(clauses):
    clauses = [normalize(c) for c in clauses]
#   print clauses
    _clauses = (Ast * len(clauses))()
    for i in range(len(clauses)):
	_clauses[i] = clauses[i].as_ast()
    ctx = clauses[0].ctx_ref()
    _true = BoolVal(True).as_ast()
    s = Z3_benchmark_to_smtlib_string(ctx,
				      "EPR Horn",
				      "HORN",
				      "sat",
				      "",
				      len(clauses)-1,
				      _clauses,
				      _clauses[len(clauses)-1])
    return s


def test1():
    A = IntSort()
    null  = IntVal(0)
    x     = Int('x')
    t     = Int('t')
    nSort = ArraySort(IntSort(), ArraySort(IntSort(), BoolSort()))
    n     = Array('n', IntSort(), ArraySort(IntSort(), BoolSort()))
    th.add_next(n)
    
    R     = Function('R', IntSort(), BoolSort(), BoolSort(), BoolSort())
    R1 = R(x, Select(Select(n,x),null),Select(Select(n,null),x))

    # x := null
    # while *
    #   t := new
    #   t.n := null
    #   t.n := x
    #   x := t
    # assert x<n*>null
    
    mk_benchmark(
	[ ForAll([x,n], ImpliesTh(True, wp([XEQY(x, null)], R1))),
	  ForAll([x,n], ImpliesTh(R1, wp([XNew(t, n, [x, null]),
					  XNextNull(t, n),
					  XnEQY(t, n, x),
					  XEQY(x, t)], R1))),
	  ForAll([x,n], ImpliesTh(R1, next(n, x, null)))])
    


def test2():
    # i := h; 
    # {I} while i != null 
    #      i.data := null; 
    #      j := i; 
    #      i = i.n
    # {Post} = {h < n* > j and j.n = null}
    
    i, j, h = Ints('i j h')

    A = IntSort()
    null  = IntVal(0)
    x     = Int('x')
    t     = Int('t')
    nSort = ArraySort(IntSort(), ArraySort(IntSort(), BoolSort()))
    n     = Array('n', IntSort(), ArraySort(IntSort(), BoolSort()))
    th.add_next(n)

    
    Q = Function('Q', IntSort(), IntSort(), IntSort(), IntSort(), BoolSort(), BoolSort(), BoolSort(), BoolSort())
    Q1 = ForAll([x], Q(i, j, h, x, next(n, i, j), next(n, h, j), next(n, x, j)))
    
    mk_benchmark(
	[ForAll([i, j, h, n], ImpliesTh(True,
					wp([XEQY(i, h)], Q1))),     
	 ForAll([i, j, h, n], ImpliesTh(And(Q1, Not(i == null)),
					wp([XEQY(j,i), XEQYn(i, n, i)], Q1))),
	 
	 ForAll([i, j, h, n], ImpliesTh(And(Q1, i == null),
					ForAll([x], And(next(n, h, j),
							Implies(next(n, j, x), Or(x == j, x == null))))))])
    

def register_relation(fp, c):
    while True:
	if is_quantifier(c) and c.is_forall():
	    c = c.body()
	    continue
	if is_app_of(c, Z3_OP_IMPLIES):
	    c = c.arg(1)
	    continue
	if c.decl().kind() == Z3_OP_UNINTERPRETED:
	    fp.register_relation(c.decl())
	return

def is_query(c):
    while True:
	if is_quantifier(c) and c.is_forall():
	    c = c.body()
	    continue
	if is_app_of(c, Z3_OP_IMPLIES):
	    c = c.arg(1)
	    continue
	if c.decl().kind() == Z3_OP_UNINTERPRETED:
	    return False
	return True

def mk_query(c):
    return Not(c)

def horn2fixedpoint(fp, clauses):
    new_clauses = []
    q = None
    for c in clauses:
	register_relation(fp, c)
    for c in clauses:
	if is_query(c):
	    q = mk_query(c)
	else:
	    fp.add_rule(c)
    if not q:
	raise "No query found"
    return fp.query(q)
    
# Next steps:
# . Check transition encodings, or replace by own implementation.
# . Produce benchmarks in this Horn format for sample programs.
#   Use the function for pretty printing SMTLIB forumulas.
#   It is called Z3_smtlib_benchmark_to_string.
#   The benchmark logic should be marked as "HORN".
#   It is unlikely these can be handled already, but it will be nice
#   to be able to process such formulas.
# . define a function that walks these Horn clauses and
#   instantiates eagerly universal quantifiers with negative polarity.
#   (meaning universal quantifiers in the bodies of the Horn clauses)
#   This is akin to blasting EPR formulas into SAT.
# . Perform an Ackerman reduction on the resulting Horn clauses.
#   This means replacing n[x][y] by a fresh propositional variable,
#   and adding axioms of the form x = x' & y = y' => n[x][y] = n[x'][y']
#   in the body of the Horn clauses. This Ackerman reduction will not
#   be necessary for a solver that can deal with arrays. HSF and Eldarica
#   don't handle arrays yet. Z3 a little bit. Duality probably a bit more.
# . After blasting and Ackerman reduction, the formulas are essentially
#   propositional (apart from equalities over integers).
#   Try different tools on these (huge?) formulas.
#   If we die during pre-processing, then modify the "replace" function
#   to use memoization. 
#
# Next, next steps:
# Going back, and improving the overall solving algorithm to be less
# blasty.
# . When body of Horn clauses contains universal quantifiers, then
#   don't instantiate them eagerly. Instead send a set of Horn clauses
#   to solver where the universally quantified formulas are replaced
#   by "True". 
# . The modified set of Horn clauses may be a bad under-approximation.
#   It may produce a counter-example trace that is not really a counter
#   example trace. Extract this from the Horn clause solver (not too easy,
#   but possible by using the "trace" feature from Z3/PDR).
#   The Horn clauses along the trace are checked for feasibility.
#   More details about this have to be worked out and explained.
# . In a second-degree of laziness also consider the set of atoms
#   that are passed to R1. We could for instance start with R1 just being
#   R(x) where R is of sort Int -> Bool (instead of Int * Bool * Bool -> Bool)
#   This template will be too weak to express the inductive invariant.
# . In a third degree of laziness grow the number of quantifiers.
# Lots of details of these steps have to be worked out. 



def assume(phi):
    return Assume(phi)

class NewExpr:
   def __str__(self):
       return "new"
     
class Expr:
   def __init__(self, e):
       self.expr = e
   def __str__(self):
       return "%s" % self.expr
   def __le__(self, other):
       return Assign(self, other)
   def __getitem__(self, other):
       return AccessExpr(self.expr, other.expr)
   def __eq__(self, other):
       return self.expr == other.expr
   def __ne__(self, other):
       return self.expr != other.expr

def Exprs(names, sort):
    consts = Consts(names, sort)
    return [Expr(c) for c in consts]

class NullExpr(Expr):
   def __init__(self):
       Expr.__init__(self, Const('null',IntSort()))

class AccessExpr(Expr):
   def __init__(self, a, i):
       self.a = a
       self.i = i
   def __str__(self):
       return "%s[%s]" % (self.a, self.i)

null = NullExpr()

class Assign:
  def __init__(self, lhs, rhs):
      self.lhs = lhs
      self.rhs = rhs
  def __str__(self):
      return "%s := %s" % (self.lhs, self.rhs)
  
  def wp(self, Q):
      l = self.lhs
      r = self.rhs
      tr = None
      if isinstance(r, NullExpr) and isinstance(l, AccessExpr): 
	  tr = XNextNull(l.a, l.i)
      elif isinstance(r, NullExpr):
	  tr = XEQY(l.expr, r.expr)
      elif isinstance(l, AccessExpr):
	  tr = XnEQY(l.a, l.i, r.expr)
      elif isinstance(r, AccessExpr):
	  tr = XEQYn(l.expr, r.i, r.a) 
      elif isinstance(r, NewExpr):
	  print "TODO: supply set of variables using analyis of the verification condtion."
	  tr = XNew(l.expr)
      else:
	  tr = XEQY(l.expr, r.expr)
      return tr.wp(Q) 

def wps(*args):
    l = len(args)
    Q = args[-1]
    i = l - 2
    while i >= 0:
	Q = args[i].wp(Q)
	i -= 1
    # TBD close Q under auxiliary sll/dll axioms and universal quantification
    print Q

D = IntSort()
B = BoolSort()
N = ArraySort(D, ArraySort(D, B))


# dll-polze.imp
# A simple program that converts a singly-linked list to a doubly-linked list
# by adjusting the back pointers.
#
# program([
#    i := h ; j := null ;
#    while $i != null$ {$I$} (
#       i.p := null ; i.p := j ;
#       j := i ;
#       i := i.n
#    )
# ])
# sll(n*)
# sll(p*)
# P := forall u v (p*(u,v) -> u = v)
# I := (i != null -> n*(h,i)) & 
#      ite(j = null, i = h,
#                    n*(h,j) & ntot_(j,i)) &
#      forall u v (p*(v,u) -> n*(u,v)) &
#      forall u v (n*(h,u) -> n*(u,v) -> ~n*(i,v) -> p*(v,u))                   
# Q := forall u v (n*(h,u) -> (n*(u,v) <-> p*(v,u)))                   
# lemma(P -> WP(Q))

    
def dll_polze():    
    i, h, j, u, v, null = Consts('i h j u v null', D)
    n, p = Consts('n p', N)
    P = ForAll([u,v], Implies(next(p, u, v), u == v))
    Q = ForAll([u,v], Implies(next(n, h, u), next(n, u, v) == next(p, v, u)))
    I = Function('I', D, D, D, D, B, B, B, B, B, B)
    I = ForAll([u,v], I(null, i, h, j, next(p,v,u), next(n,u,v), next(n, h,j), next(n,h,u), next(n,i,v)))
    # TBD: domain axioms sll?
    i, h, j = Exprs('i h j', D)
    null = NullExpr()
    n, p = Exprs('n p', N)
    wps(assume(P), i <= h, j <= null, I)
    wps(assume(I), assume(i != null), i[p] <= null, i[p] <= j, j <= i, i <= i[n], I)
    wps(assume(I), assume(i == null), Q)

# dll-splice
# program([
#     if $h != null & i != h$ then (
#        j := i.p ;
#        j.n := null ;
#        i.p := null
#     )
#     else skip
# ])
#
#
# dll(n*,p*) := sll(n*) & sll(p*) & forall u v (n*(u,v) <-> p*(v,u))
# 
# dll(n*,p*)
# 
# P := n*(h,i) & eqrel(_n*, n*)
# Q := dll(n*,p*) & 
#      forall u v (_n*(h,u) -> (n*(u,v) <-> _n*(u,v) & (_n*(i,u) <-> _n*(i,v))))
# lemma(P -> WP(Q))


def dll_splice():
    i, h, j, u, v, null = Consts('i h j u v null', D)
    n, p, _n = Consts('n p _n', N)
    eqrel = lambda n, m : ForAll([u,v], next(n,u,v) == next(m,u,v))
    sll = lambda n : True # TBD!!!!!!!!
    dll = lambda n, p : And(sll(n), sll(p), ForAll([u,v], next(n, u, v) == next(p, v, u)))
    P = And(next(n, h,i), eqrel(_n, n))
    Q = And(dll(n,p), ForAll([u,v], Implies(next(_n, h, u), And(next(n, u, v) == next(_n, u, v), next(_n,i,u) == next(_n,i,v)))))
    i, h, j = Exprs('i h j', D)
    null = NullExpr()
    n, p = Exprs('n p', N)
    wps(assume(P), assume(h != null), assume(i != h), j <= i[p], j[n] <= null, i[p] <= null, Q)
    wps(assume(P), assume(h == null), Q)
    wps(assume(P), assume(h != null), assume(i == h), Q)

# dll_splice()


# sll_create:
# program([
#    h := null ;
#    while $C(h)$ {$I$} (
#       i := new ;
#       i.n := null ; i.n := h ;
#       h := i
#    )
#  ])
# sll(n*)
#
# pvars(u) := u = i | u = h | u = x
# 
# I := ~n*(h,x)
# 
# P := x != null
# 
# lemma(P -> WP(true))
 
def sll_create():
    return None

#print j[c] 
#print (j[c] <= null)
def mk_predicates():
    i = Const('i',D)
    j = Const('j',D)
    h = Const('h',D)
    z,u,y = Consts('z u y', D)
    m, n  = Consts('m n', N)
    null = Const('null', D)
    P = ForAll([z,u,y], Implies(And(next(n,h,z), next(m, z, u), next(m, y, u)), z == y))
    Q = ForAll([z,u], Implies(And(next(n,h,z), next(n,z,null)), next(m, h, u))) # TBD _m*?
    I1 = Function('I1', D, D, D, B, B)
    I1 = I1(i,j,h,next(n,h,j)) 
    I2 = Function('I2', D, D, D, B)
    I2 = I2(i,j,h)
    return P, I1, I2, Q

def test():
    P, I1, I2, Q = mk_predicates()
    i = Expr(Const('i', D))
    h = Expr(Const('h', D))
    j = Expr(Const('j', D))
    c = Expr(Const('c', N))
    k = Expr(Const('k', D))
    m = Expr(Const('m', N))
    n = Expr(Const('n', N))
    wps(assume(P), i <= h, j <= null, I1)
    wps(assume(I1), assume(i != null), k <= i, I2)
    wps(assume(I2), assume(k != null), j <= k, k <= k[m], I2)
    wps(assume(I2), assume(k == null), j[c] <= null, i <= i[n], j[m] <= null, I1)
    wps(assume(I1), assume(i == null), j[c] <= null, j[c] <= h, Q)

# test()

# TODO: complete, P, Q, other transitions as below.
# TODO: add universal closure operator + background theory to wp.

#Q := forall z u (n*(h,z) & n*(z,null) & _m*(z,u) -> m*(h,u)) &
#     forall u v (u != v & m*(u,v) -> ~C(u)) &
#     (h!=null -> C(j))
#P := forall z u y (n*(h,z) & m*(z,u) & n*(h,y) & m*(y,u) -> z = y) &
#     forall u v w (u != v & v != w & _m*(u,v) -> ~n*(v,w)) &
#     forall u v (m*(u,v) <-> _m*(u,v)) &
#     forall u v (u != v & m*(u,v) -> ~C(u))


# P  & true => wp(i := h; j := null, I1)
# I1 & i != null => wp(k := i, I2)
# I2 & k != null => wp(j := k; k := k.m, I2)
# I2 & k == null => wp(j.c := null; i := i.n; j.m := null; j.m := i; I1)
# I1 & i == null => wp(j.c := null; j.c := h, Q)

#   j[c] |= null
