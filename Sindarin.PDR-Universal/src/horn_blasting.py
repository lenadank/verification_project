# encoding=utf-8
import linker  # @UnusedImport
from z3 import *  # @UnusedWildImport
from logic.fol.syntax.formula import FolFormula
from copy import deepcopy
#from synopsis.proof import ProofSynopsis, DummyStopwatch
#from synopsis.af_wp import ExpansionPreprocessor, ExpansionWithSubst,\
#    ProtectedDeltaReduction
#from synopsis.af_comp import WhileFrontendExtension, detptr_libraries
from logic.fol.syntax.transform.delta import PatternDeltaReduction
from logic.fol.syntax.transform.alpha import AlphaRenaming
import itertools
#from synopsis.stats import Stopwatch
from logic.fol.syntax.transform import AuxTransformers
from logic.fol.syntax import Identifier
from pprint import pprint
from eprv.synopsis.proof import ProofSynopsis, DummyStopwatch
from pattern.debug.profile import Stopwatch
#from twinkie import Z3FormulaToFolFormula



def is_forall_var(v):
    return v.root == FolFormula.FORALL

#creates one formula
def create_one_f(v,f,c):
    if f.root == v.root:
        f.root = c 
    subf_len = len( f.subtrees )
    for i in xrange(0,subf_len):
        f.subtrees[i] = create_one_f(v,f.subtrees[i],c)
    return f


def conjunct_formulas( fs ):
    return FolFormula.conjunction( fs )


def replace_with_conjuncts(v,f,concretes):
    fs  = []
    for c in concretes:
        fcopy = deepcopy(f)
        cur = create_one_f(v,fcopy,c)                
        fs.append( cur )
    res = conjunct_formulas(fs)
    return res    


def blast_horn_body(f,concretes):    
    if is_forall_var(f):
        rhs = blast_horn_body( f.subtrees[1], concretes )        
        f.subtrees[1] = rhs
        one_blast = replace_with_conjuncts(f.subtrees[0],f.subtrees[1],concretes)        
        return one_blast
    else:
        return f


def formula_forall_prefix_get(formula):
    res = []
    f   = formula
    while is_forall_var(f):
        res.append(f.subtrees[0].root)
        f = f.subtrees[1]
    return res


def formula_wo_forall_prefix_get(formula):
    f   = formula
    while is_forall_var(f):        
        f = f.subtrees[1]
    return f

        
def horn_body_get(formula):    
    f   = formula_wo_forall_prefix_get( formula )            
    if f.root == FolFormula.IMPLIES:    
        return f.subtrees[0]
    else:
        raise ValueError, 'horn_body_get(): Not a horn clause! '
        
    
def horn_body_set(f_org,new_body):
    res = deepcopy(f_org)
    f   = res
    if f.root == FolFormula.IMPLIES:    
        f.subtrees[0]  = new_body    
    else:
        raise ValueError, 'horn_body_set(): not horn formula'    
    return res


def horn_head_set(f_org,new_head):
    res = deepcopy(f_org)
    f   = res
    if f.root == FolFormula.IMPLIES:    
        f.subtrees[1]  = new_head   
    else:
        raise ValueError, 'horn_body_set(): not horn formula'    
    return res


def forall_prefix_formula_body_set(org,blasted):
    res = deepcopy(org)
    f   = res
    while is_forall_var(f):        
        f = f.subtrees[1]
        
    #f.root        = blasted.root
    f.subtrees[0]  = blasted
    #f.subtrees[1] = blasted.subtrees[1]
    return res


def parse_fml(str_to_parse):
    from eprv.synopsis.expand import Expansion
    L          =  Expansion.FormulaReader().parser
    return  L(str_to_parse)
    

def blast_horn_clause(t,concretes):
    horn_body  =  horn_body_get(t)
    #concretes  =  formula_forall_prefix_get(t)    
    blast_wo_forall_prefix =  blast_horn_body(horn_body,concretes)    
    res = forall_prefix_formula_body_set(t, blast_wo_forall_prefix)        
    return res

    
def replace_nstar_with_bools( a, decls = {}, ack_bools = {}, ack_vars = {} ):
    if is_app_of(a, Z3_OP_SELECT):        
        lSelSide = a.arg(0)
        if is_app_of(lSelSide, Z3_OP_SELECT):
            lhs       = lSelSide.arg(1)
            rhs       = a.arg(1)
            boolName  = 'n_' + str(lhs) + '_' + str(rhs)
                                
            res                 = Bool( boolName )        
            ack_bools[boolName] = res            
            boolTuple           = ( lhs, rhs, res )            
            ack_vars[boolName]  = boolTuple
            return res
    elif is_const(a):
        return a
               
    elif is_app_of(a, Z3_OP_IMPLIES)\
        or is_app_of(a, Z3_OP_OR)\
        or is_app_of(a, Z3_OP_EQ)\
        or is_app_of(a, Z3_OP_DISTINCT): #!=, NEQ

        lhs = replace_nstar_with_bools( a.arg(0), decls, ack_bools, ack_vars )
        rhs = replace_nstar_with_bools( a.arg(1), decls, ack_bools, ack_vars )
        
        if is_app_of(a, Z3_OP_IMPLIES):
            return Implies(lhs,rhs)
        elif is_app_of(a, Z3_OP_DISTINCT):
            return lhs != rhs
        elif is_app_of(a, Z3_OP_EQ):
            return lhs == rhs
        elif is_app_of(a, Z3_OP_OR):
            return Or(lhs,rhs)
        else:
            print 'Unknown connective', a
            raise SystemExit
                        
    elif is_app_of(a, Z3_OP_NOT):
        return Not( replace_nstar_with_bools( a.arg(0), decls, ack_bools, ack_vars ) )
        
    elif is_app_of(a, Z3_OP_AND):
        cRes = []
        for c in a.children():
            c = replace_nstar_with_bools( c, decls, ack_bools, ack_vars)
            cRes.append(c)
        return And( *cRes )
        
    elif is_quantifier(a) and a.is_forall():
        vars0 = [ Const(a.var_name(i), a.var_sort(i)) for i in range(a.num_vars())]    
        vars0.reverse()
        #print 'forall vars' , vars0
        b = substitute_vars(a.body(), *vars0)
        b = replace_nstar_with_bools( b,decls, ack_bools, ack_vars )
        ack_bools_ls = ack_bools.values()
        return ForAll( vars0 + ack_bools_ls , b)

    else:        
        #print a, a.children(), a.decl(), a.decl().kind(), a.num_args(), is_var(a), len(a.children() )        
        for v in decls.values():
            if eq(v,a.decl() ):
                cRes = []
                for c in a.children():
                    c = replace_nstar_with_bools( c, decls, ack_bools, ack_vars )
                    cRes.append(c)
                fsym = a.decl()
                return fsym( cRes )
        print 'Unknown symbol: ', a
        raise SystemExit

    print 'Error Should not get here'
    raise ValueError                 

        
####################################
# defs for z3 stuff from shape2horn#
####################################

def next(n, x, y):
    return Select(Select(n, x), y)




impSort = IntSort()

n = Array('n', impSort, ArraySort(impSort, BoolSort()))
_n = Array('_n', impSort, ArraySort(impSort, BoolSort()))
#p = Array('p', impSort, ArraySort(impSort, BoolSort()))
#_p = Array('_p', impSort, ArraySort(impSort, BoolSort()))
C = Array('C', impSort, BoolSort())

#null, iprime, i, j, jprime1, jprime2, h    =  Ints('null, iprime i j jprime1 jprime2 h')
#Q  = Function('Q', IntSort(), IntSort(), IntSort(), IntSort(), IntSort(), 
#                    BoolSort(), BoolSort(), BoolSort(), BoolSort(), BoolSort() )
#Q2 = Q(null, i, j, h, jprime1,  next(n, h, j), next(n,j, i), next(n, j, jprime1), next(n, i, j) )
#Q3 = Q(null, iprime, i, h, jprime2, next(n, h, i), next(n,i, iprime), next(n, i, jprime2), next(n, iprime, i) )
#Q3 = Q(iprime, i, h, jprime, next(n, h, iprime), next(n, h, i), next(n, i, jprime))
#Q3 = Q(iprime, i, h, jprime, next(n, h, iprime), next(n, h, i), next(n, i, jprime))

# NSB:
# Where do you bind 'null' and 'x' ?
# These variables are free in the formulas you produce.

####################################

def fol_formula_to_z3(f,decls):
    flen = len( f.subtrees )
    if f.root in decls:
        fsym = decls[f.root]
        args = [fol_formula_to_z3(a, decls) for a in f.subtrees]
        return fsym(*args)
    elif flen == 0:        
        if f.root == 'true':
            return True
        elif f.root == FolFormula.FALSE or f.root == 'false':
            return False    
        else:        
            return Const(f.root.literal, impSort)
    elif flen == 1:
        if f.root == FolFormula.NOT:
            arg = fol_formula_to_z3( f.subtrees[0], decls)        
            #Hack, was: return Not( arg )
            if 0:
                if isinstance(arg, bool ):
                    return True
                else:
                    return Not( arg )
            #Hack, was: return Not( arg )        
            return Not( arg )
        elif f.root == 'C':
            arg = fol_formula_to_z3( f.subtrees[0], decls)            
            res = Select(C, arg)
            return res                    
        else:                
            raise ValueError, 'unknown formula: %s' %f
    else:                
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
        elif f.root == '!=' or f.root == u"≠":
            return lhs != rhs            
        elif f.root == FolFormula.OR:                       
            res = Or( lhs,rhs )
            return res            
        elif f.root == 'n*':            
            res = next( n,lhs,rhs )
            return res
        elif f.root == '_n*':            
            res = next( _n,lhs,rhs )
            return res
#        elif f.root == '_p*':            
#            res = next( _p,lhs,rhs )
#            return res                
#        elif f.root == 'p*':            
#            res = next( p,lhs,rhs )
#            return res                
                        
        elif f.root == FolFormula.FORALL:            
            if is_quantifier(rhs) and rhs.is_forall():
                vars0 = [ Const(rhs.var_name(i), rhs.var_sort(i)) for i in range(rhs.num_vars())]    
                vars0.reverse()
                b = substitute_vars(rhs.body(), *vars0)                
                return ForAll( [lhs]+vars0, b )                
            else:
                return ForAll( [lhs],rhs)                            
        else:
            print 'unknown f.root', f.root,f      
            raise SystemExit


def transform_concretes_to_z3_prefix(concretes):
    res = []
    for c in concretes:
        pf = Const(c.literal, impSort )
        res.append(pf)
    
    #TODO add a map from all the relations to their Z3 declerations
    res.append(n)
    res.append(_n)
    #res.append(p)
    #res.append(_p)
    res.append(C)
    
    return res
    

def transform_formula_to_z3(prefix, t,decls={}):
    f                 =  t
    horn_wo_prefix    =  f    
    z3_horn_prefix    =  transform_concretes_to_z3_prefix(prefix)
    z3_horn_wo_prefix =  fol_formula_to_z3(horn_wo_prefix,decls)    
    return  [ ForAll(z3_horn_prefix,z3_horn_wo_prefix) ]


def benchmark_print_to_file(h,formulas):
    from shape2horn import mk_benchmark    
    benchmark =  mk_benchmark(formulas)
        
    if h.output_smt is not None:
        with open(h.output_smt,'w') as f:
            f.write( unicode(benchmark) )
    
    print benchmark               


def formulas_solver( h, formulas, I, I_args):
    
    print 'Solving...'    
    s = Tactic('horn').solver()
    
    for f in formulas:
        s.add( f )

    r = s.check()
    print 'Result:', r
    #st =  s.statistics()
    if r == sat:
        print s.model()
        I_interp  = s.model().get_interp(I)      
        #print s.get_answer() from fix points
        print I_interp
        I_res     = I_interp_in_human_readable_form_get( I_interp, I_args )         

        print I, "=\n", I_res
        #print Z3FormulaToFolFormula()(I_interp.else_value())(*I_args)
        #print s.get_answer() from fix points
    elif r == unknown:                       
        print s.reason_unknown()

    
gamma_linord = """ forall a b c ( ( n*(a,a) ) &
                 ( ( n*(a,b) & n*(b,c) ) -> n*(a,c) ) & 
                 ( ( n*(a,b) & n*(a,c) ) -> ( n*(b,c) | n*(c,b) ) ) &
                 ( ( n*(a,b) & n*(b,a) ) -> a = b ) &
                 ( n*(null,a) -> a = null ) &
                 ( n*(a,null) -> a = null ) )
             """
    #reflexive  = """forall a ( n*(a,a) )"""
    #transitive = """forall a b c ( ( n*(a,b) & n*(b,c) ) -> n*(a,c) )"""
    #linear     = """forall a b c ( ( n*(a,b) & n*(a,c) ) -> ( n*(b,c) | n*(c,b) ) )"""
    #antisymetric = """forall a b ( ( n*(a,b) & n*(b,a) ) -> a = b )"""
    #nulltype     = """forall a ( n*(null,a) -> a = null )"""
    

class WeakestPreSynthesis(object):
    """
    TODO Actually not really using this; should just use ProofSynthesis directly.
    """
    
    def __init__(self):       
        self.syn = ProofSynopsis()
                
    def configure(self, (preface, libraries)):
        self.syn.smt.preface = preface
        self.syn.libs += libraries
                        
    def __call__(self, prog, gui=True, z3_swatch=DummyStopwatch()):        
        e      = self.syn.expansion
        stream = itertools.chain(*[e(x) for x in self.syn.libs + [prog]])
        for f in stream:
            #print f
            yield f
        
        #return run_z3_and_produce_model(ofn, gui=gui, swatch=z3_swatch)

####################################
                

z3_sortmap = { 'V' : impSort, 'bool' : BoolSort() }
            
def define_symbol(sym):    
    sym_name           = sym[0]    
    sym_from, sym_to   = sym[1]
    sym_sorts = [] #[ IntSort(), IntSort(), ..., BoolSort() ]
    
    for s in list(sym_from) + [sym_to] :        
        z3_sym = z3_sortmap[s]
        sym_sorts.append(z3_sym)

    Q  = Function( sym_name.literal, *sym_sorts )
    return Q


def inv_args_get(wps, I):
    inv = wps.syn.expansion('pick(prog)')    
    for phi in inv:
        print phi
        for x in phi.nodes:            
            if x.root.literal == I:                
                return x.subtrees
            

def as_dummy_z3_var(term):
    return Int(str(term))
                  

def I_interp_in_human_readable_form_get(a, I_args):
    I_z3_args = [as_dummy_z3_var(x) for x in I_args]
    f   =  a.else_value()
    res =  substitute_vars( f, *I_z3_args )
    return res 

                
def wps_formula_get(wps,wp_prog):
    td = wps.syn.type_declarations
    formulas = []     
    for f in wps(wp_prog):
        if td.is_declaration(f):
            td.read_from([f])                    
        else:
            formulas.extend( f.split() ) 

    return formulas, { x[0]: define_symbol(x)     
        for x in td.sorts.iterdefs()         
        }
                

def wp_forall_prefix_get(f):
    if not f.subtrees:
        if f.root in ['true','false']: # or f.root.literal == 'C':
            return []
        else:
            return [f.root]    
    else:
        l = (wp_forall_prefix_get(x) for x in f.subtrees)
        return set(y for x in l for y in x)


def gamma_add(f):
    f_body = horn_body_get(f)
    gamma  = parse_fml(gamma_linord)    
    gamma_wo_forall_prefix = formula_wo_forall_prefix_get( gamma )
    #gamma_forall_prefix    = formula_forall_prefix_get( gamma )
    body_wo_forall = conjunct_formulas( [gamma_wo_forall_prefix,f_body] )    
    body           = forall_prefix_formula_body_set(gamma, body_wo_forall )
    f_wt_gamma     = horn_body_set(f,body)    
    return f_wt_gamma

        
def create_f_with_implies(b,h):
    f = FolFormula( FolFormula.IMPLIES )
    f.subtrees = []
    f.subtrees.append( b )
    f.subtrees.append( h )
    return f


def create_one_ackerman_clause( x,y,z,w, bxy, bzw):
    lhs = And( x == z, y == w )    
    return Implies( lhs , bxy == bzw )


def all_bool_perumtes_get( variables ):
    return itertools.permutations(variables, 2)


def ackm_clause_to_horn_f_add( a, ackm_clauses ):
    if is_quantifier(a) and a.is_forall():
        vars0 = [ Const(a.var_name(i), a.var_sort(i)) for i in range(a.num_vars())]    
        vars0.reverse()
        b = substitute_vars( a.body(), *vars0 )
        
        if is_app_of( b, Z3_OP_IMPLIES ):                                       
            horn_body = b.arg(0)
            horn_head = b.arg(1)
             
            if is_app_of( horn_body, Z3_OP_AND):
                horn_body_conjuct = []                
                for c in horn_body.children():
                    horn_body_conjuct.append(c)
                    
                horn_body_conjuct += ackm_clauses  
                res =  ForAll( vars0, Implies( And( *horn_body_conjuct ),  horn_head  ) )
                return res
        

def ackerman_reduction_get( f, ack_map ):        
    ps = all_bool_perumtes_get( ack_map.keys() )        
    ackm_clauses = []
    
    for p in ps:
        l = ack_map[p[0]]
        r = ack_map[p[1]]
        ackm_clause = create_one_ackerman_clause( l[0], l[1], r[0], r[1], l[2], r[2])            
        ackm_clauses.append( ackm_clause )

    res = ackm_clause_to_horn_f_add( f , ackm_clauses)    
    return res


class HornBlaster(object):
    VC = """  
VCaux(`skip, Q)              := true
VCaux([x:=y](x, y), Q)       := true
VCaux([x:=null](x), Q)       := true
VCaux([x:=y.n](x, y, n), Q)  := true
VCaux([x.n|=y](x, n, y), Q)  := true
VCaux([x.n:=null](x, n), Q)  := true    
VCaux([;](S1, S2), Q)        := VCaux( S1, wp(S2,Q) ) & VCaux( S2,Q )
VCaux(if(C, S1, S2), Q)      := VCaux( S1, Q ) & VCaux( S2, Q )
VCaux( while (cond, I, loopBody), Q) := VCaux( loopBody, I ) & 
            ( I & cond -> wp(loopBody, I) ) & ( I & ~cond  -> Q )
    
VCgen( P, S, Q ) := ( P -> wp( S, Q ) ) & VCaux( S, Q )   
               
wp( while(b,I,s), Q ) := I

( B -> ite( c, t, e ) ) := ( B & c -> t ) & ( B & ~c -> e )            
    """
                                    
    
    def __init__(self):
        self.output_smt = None
        

    def __call__(self, program):
        wps = WeakestPreSynthesis()    
        wps.configure(detptr_libraries())
        wps.syn.libs += [self.VC] #TODO - change        
        
        formulas , decls  =  wps_formula_get(wps,program)
        
        I_args = inv_args_get(wps, "I")
        
        formula = FolFormula.conjunction(formulas)
            
        prefix           =  wp_forall_prefix_get(formula)| set([Identifier('null', 'const')])
        bounded_prefix   =  AuxTransformers.get_all_bound_vars(formula)
        prefix-=bounded_prefix
        
        
        pprint( formulas )
        print  prefix
        
        
                
        z3_formulas_with_blasting = []    
    
        from shape2horn import hoist_forall
        from shape2horn import blast_horn
        from shape2horn import hoist_horn
        formulas_with_implies = []
        ackm_bools            = {}
        ackm_bools_to_vars    = {}
        
        #sanity = FormulaSanity()
                
        watch = Stopwatch()
        with watch:
                
            for f in formulas:
                
                if f.root == 'true':                    
                    continue 
                
                head    = f.subtrees[1]        
                body    = f.subtrees[0]
                head_ls = FolFormula.split(head) #splits conjunctions in head
                
                for i in head_ls:
                    #creates new formulas of form: body -> i
                    f_with_implies = create_f_with_implies(body,i)            
                    formulas_with_implies.append( f_with_implies )
                                
            for s in formulas_with_implies:
                print '--------   Input Clause   ----------------'
                print s      
                s_with_gamma = gamma_add( s )
                #renumber_bound_vars() renames bounded vars to unique numbers
                s_with_gamma = AuxTransformers.renumber_bound_vars( s_with_gamma )        
                print s_with_gamma                             
                z3_f = transform_formula_to_z3(prefix, s_with_gamma, decls)
                for f in hoist_horn(z3_f[0]):
                   z3_f_hoisted = hoist_forall(f)
                		
                   print '--------  Hoisted Formula  ------------------'
                   print z3_f_hoisted
                   blasted_f  =  blast_horn(z3_f_hoisted)
                
                   print '--------  Blasted Formula  ---------------------'             
                   #print blasted_f
                   if 0:                        
                      blasted_f_with_replaced_n = replace_nstar_with_bools( blasted_f, \
                                                     decls, ackm_bools, ackm_bools_to_vars )            
                      f_with_ackm_reduction = ackerman_reduction_get( \
                                            blasted_f_with_replaced_n , ackm_bools_to_vars )
                   #print ackm_bools_to_vars            
                   z3_formulas_with_blasting.append( blasted_f )
            
            #benchmark_print_to_file(h, z3_formulas_with_blasting)            
            formulas_solver ( self, z3_formulas_with_blasting, decls["I"], I_args )
        
        print 'Total sovling time: ',watch.total_time,'sec'
    
                
if __name__ == '__main__':       
    # This is for debugging errors in Eclipse
    try:
        import pydevd
        pydevd.GetGlobalDebugger().setExceptHook(Exception, True, False)
    except ImportError:
        pass
                 
    h            =  HornBlaster()
    file_prefix  = "sll-find"
    program      =  open("../benchmarks/"+file_prefix+".fol").read()    
    h.output_smt = "../benchmarks/"+file_prefix+".smt2"
    h(program)
    
