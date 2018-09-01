# encoding=utf-8
'''
Admits a set of functions into the EPR signature.
To be able to extend the language with functions, these functions have to uphold
certain properties as described in doc/cycles.tex.
We then follow the proposed construction to reduce the resulting formula back to
a relation-only signature, without introducing more quantifier alternation.

Basically a function
    f : V -> V
is reduced to a relation
    F : V * V -> bool
But then we would need an axiom such as forall u (exists v (F(u,v))),
which would violate EPR. Hence we replace it by a weaker axiom s.t. the
system remains equi-satisfiable.
'''
from logic.fol import Identifier, FolFormula
from logic.fol.syntax.transform.alpha import AlphaRenaming
from adt.tree.transform import TreeTransform
from logic.fol.semantics.extensions.equality import FolWithEquality
from logic.fol.semantics.extensions.sorts import FolManySortSignature, FolSorts
from logic.fol.syntax import RepresentationForm
from adt.tree.walk import PostorderWalk


import sys
from eprv.extensions.fresh import RenumberLiterals
from adt.tree import Tree
sys.setrecursionlimit(10000)


class EasyFunctionsExtension(object):
    
    class BracketedModifier(RepresentationForm):
        def repr(self, elements):
            return u"%s[%s]" % (self, ", ".join(`r` for r in elements))
    
    def __init__(self):
        self.constants = set()#[Identifier(c, 'function') for c in ['x0', 'y0', 't0', 's0', 'r_', 'q_']]
        self.funcs = []
        self.rel_funcs = []
        self.rel_modifier = self.BracketedModifier('R', 'modifier')
        self.unnest = UnnestTerms()
        
    def _rel(self, f):
        return Identifier("R_%s" % f, 'predicate')
        #return Identifier(FolFormula(self.rel_modifier, [FolFormula(f)]), 'predicate')
    
    def _img(self, f, x, ns=None):
        f = self.BracketedModifier(f, 'modifier')
        return Identifier(FolFormula(f, [FolFormula(x)]), 'function', ns=ns)
        
    def construct_totality(self, xbar=None):
        ns = AlphaRenaming.NS()
        xbar = list(self.constants if xbar is None else xbar)
        #xbar_funcs = [(x, f) for x in xbar for f in self.rel_funcs]
        #ren = RenumberLiterals()
        #y = Identifier(u'α', 'variable', ns=ns)
        _ = FolFormula
        q = _.promote
        def instantiate(node, varsym):
            l = []
            for s in node.subtrees:
                f = s.root
                new_var = Identifier(u"%s_%s" % (f, varsym), 'variable', ns=ns)
                img = _(self._rel(f), [q(varsym), q(new_var)])
                imgs = _.conjunction([img] + instantiate(s, new_var))
                l += [_(_.EXISTS, [q(new_var), imgs])]
            return l
        #conjs = [_(self._rel(f), [q(x), q(y)]) for x, f in xbar_funcs]
        #return _.conjunction(_(_.EXISTS, [q(y), q(conj)]) for conj in conjs)
        return _.conjunction(inst for x in xbar for inst in instantiate(self.rel_funcs, x))
    
    def _mark_context_sign(self, phi, root_sign='+'):
        neg_root_sign = self.NEG_SIGN[root_sign]
        r, s = phi.root, phi.subtrees
        phi.context_sign = root_sign
        if r == 'disable-relativization':
            root_sign = '--'
        elif r == FolFormula.IMPLIES and s:
            for x in s[:-1]: self._mark_context_sign(x, neg_root_sign)
            self._mark_context_sign(s[-1], root_sign)
            return
        elif r == FolFormula.NOT:
            root_sign = neg_root_sign
        
        for x in s: self._mark_context_sign(x, root_sign)

    NEG_SIGN = {'+': '-', '-': '+', '+-': '+-', '--': '--'}
    
    def relativize_quantifiers(self, phi):
        """
        forall x (P(x))  --->  forall x (exists cx (R[f](x,cx)) -> P(x))
        exists x (P(x))  --->  exists x (exists cx (R[f](x,cx)) & P(x))
        """
        def gen_tot(t, r, s, connective):
            for x in s[:-1]:
                if x.subtrees:
                    raise ValueError, "nonterminal quantified variable '%s'" % (x,)
            imp = self.construct_totality([x.root for x in s[:-1]])
            T = type(t)
            return T(r, s[:-1] + [T(connective, [imp, s[-1]])])
        def xform(t):
            r, s = t.root, t.subtrees
            if r == 'disable-relativization':
                return FolFormula.conjunction(s)
            elif r.kind == 'quantifier' and  t.context_sign == '--':
                return None  # skip relativization for this quantifier (disable-relativization)
            elif r.kind == 'quantifier' and (u'β' in s[0].root.literal or u'γ' in s[0].root.literal):
                return None
            elif r == FolFormula.FORALL and t.context_sign == '+':
                return gen_tot(t, r, s, FolFormula.IMPLIES)
            elif r == FolFormula.EXISTS and t.context_sign == '-':
                return gen_tot(t, r, s, FolFormula.AND)
            elif r in [FolFormula.FORALL, FolFormula.EXISTS] and t.context_sign == '+-':
                raise NotImplementedError, "ambiguous context for quantifier: '%s'" % (t,)
        self._mark_context_sign(phi)
        return TreeTransform([xform], dir=TreeTransform.BOTTOM_UP).inplace(phi)
    
    def replace_equalities_with_atomic(self, phi, quantifier_type):
        '''f(x) = y    --->   R[f](x, y)
           y = f(x)    --->   R[f](x, y)
           f(x) = g(y) --->   forall z (R[f](x,z) -> R[g](y,z))   /
                              exists z (R[f](x,z) & R[g](y,z))
                              
           The quantifier is determined according to quantifier_type (either FolFormula.FORALL or FolFormula.EXISTS)
           when the atomic formula occurs in a positive context. In a negative 
           context, the other quantifier is used.
           '''
        EQ = FolWithEquality.eq
        def xform(t):
            if not self.unnest.is_fine(t):
                raise ValueError, "nested term not allowed; in '%s'" % t
            r, s = t.root, t.subtrees
            s = sorted(s, key=lambda x: len(x.subtrees), reverse=True)
            if r == EQ and len(s) == 2 and s[0].root in self.funcs:
                if s[1].root in self.funcs:
                    _ = FolFormula
                    gamma = Identifier(u'γ', 'variable', ns=AlphaRenaming.NS())
                    if (quantifier_type, t.context_sign) in [(_.FORALL, "+"), (_.EXISTS, "-")]:
                        quantifier, connective = _.FORALL, _.IMPLIES
                    elif (quantifier_type, t.context_sign) in [(_.FORALL, "-"), (_.EXISTS, "+")]:
                        quantifier, connective = _.EXISTS, _.AND
                    else:
                        raise ValueError, "invalid quantifier context %s" % ((quantifier_type, t.context_sign),)
                    return _(quantifier, [_(gamma), _(connective, [_(self._rel(s[0].root), s[0].subtrees + [_(gamma)]),
                                                                   _(self._rel(s[1].root), s[1].subtrees + [_(gamma)])])])
                else:
                    return FolFormula(self._rel(s[0].root), s[0].subtrees + s[1:])
        self._mark_context_sign(phi)
        return TreeTransform([xform]).inplace(phi)
    
    def _simplify(self, phi):
        """A naive simplification that strips away "True ->" and "True &"."""
        #print "NOT SIMPLIFIED: ", phi
        def noop_elim(phi):
            if phi.root in [FolFormula.IMPLIES, FolFormula.AND] and phi.subtrees[0].root == True:
                return phi.subtrees[1]
        for n in PostorderWalk(phi):
            n.subtrees = [noop_elim(x) or x for x in n.subtrees]
        phi = noop_elim(phi) or phi
        #print "SIMPLIFIED: ", phi
        return phi 
    
    def __call__(self, t, e=None):
        """
        Modifies lemmas such that they have totality antecedents at the 
        beginning for global constants and then again for every universally
        quantified variable.
        """
        simpl = self._simplify
        ar = AlphaRenaming()
        if t.root == 'lemma' and len(t.subtrees) == 1:
            phi = simpl(t.subtrees[0])
            phi = self.unnest(phi, self.constants, FolFormula.FORALL)
            totc = self.construct_totality()
            relt = self.replace_equalities_with_atomic(self.relativize_quantifiers(phi), quantifier_type=FolFormula.EXISTS)
            phi = FolFormula(FolFormula.IMPLIES, [totc, relt])
            phi = FolFormula.conjunction(ar(conj) for conj in phi.split())
            return simpl(FolFormula(t.root, [phi])) 
        else:
            phi = simpl(t)
            # @todo resolve cyclic dependency
            from eprv.synopsis.proof import CheckQuantifierAlternation
            if not CheckQuantifierAlternation().is_universal(phi):
                raise ValueError, "axioms must be universal; this one isn't: '%s'" % phi 
            phi = self.unnest(phi, self.constants, FolFormula.FORALL)
            phi = simpl(self.replace_equalities_with_atomic(phi, quantifier_type=FolFormula.FORALL))
            phi = FolFormula.conjunction(ar(conj) for conj in phi.split())
            return phi
        
    def inplace(self, phi):
        """
        Causes 'phi' to be modified, if it is a lemma, by adding totality 
        antecedents where needed.
        """
        phi_prime = self(phi)
        if phi_prime:
            self._rewrite(phi, phi_prime)
            
    def _rewrite(self, phi, psi):
        phi.root, phi.subtrees = psi.root, psi.subtrees
        return phi
            
    def declare_relations(self, signature):
        for f in self.funcs:
            Rf = self._rel(f)
            if Rf not in signature.preds:
                for from_, to_ in signature.sort_of(f):
                    signature |= FolManySortSignature.from_sorts(
                        FolSorts({Rf: [(tuple(from_) + (to_,), 'bool')]}))

    def inspect_formula(self, phi, ctx):
        '''Collects constants occurring in assertions.'''
        # TODO: remove 'used_fragment', take all the functions ever
        s = ctx.signature #.used_fragment([phi])
        self.constants = [c for c,_ in s.funcs if s.sorts.is_const(c, of_sort="V")]
        self.funcs = [c for c,a in s.funcs if a == 1 and s.sorts.returns(c, "V")]
        #self.rel_funcs = self.funcs
        #self.rel_funcs = [c for c in self.funcs if (c,1) in s.used_fragment([phi]).funcs or c in ["k0", "km0"]]
        
        _ = Tree
        #rel_funcs = _('', [_('k10', [_('k20'), _('km20')]),
        #                   _('km10', [_('k20'), _('km20')])
        #                   ] + [_(x) for x in ["f", "g", "l0", "k0", "km0", "k20", "km20"]])
        rel_funcs = _('', [_(x) for x in ["f", "g", "l0", "k0", "km0", "k10", "km10", "k20", "km20", "en0"]])
        def xform(t):
            r, s = t.root, t.subtrees
            if r != '':
                f = [c for c in self.funcs if c.literal == r]
                if f:
                    new_r = f[0]
                else:
                    return Tree('')
            else:
                new_r = r
            return Tree(new_r, [x for x in s if x.root != ''])
        
        self.rel_funcs = TreeTransform([xform], dir=TreeTransform.BOTTOM_UP)(rel_funcs)
        #[c for c in self.funcs if c in ["f", "g", "l0", "k0", "km0", "k10", "km10", "k20", "km20", "k2k10", "km2k10", "k2km10", "km2km10"]]
        self.declare_relations(ctx.signature)
        
        self.inplace(phi)
        
   

      

class BidirectionalDict(dict):
    
    def get_backwards(self, value):
        ''' returns key such that self[key] == value '''
        for k, v in self.iteritems():
            if v == value: return k
        else:
            raise KeyError, value

        

class UnnestTerms(object):
    '''
    P(f(x))  --->  let y=f(x) in (P(y))
    '''
    
    def __call__(self, phi, constants, quantifier_context):
        phi = TreeTransform([self._xform], dir=TreeTransform.BOTTOM_UP)(phi)
        return self._xform_toplevel(phi, constants, quantifier_context)
        
    def _rename_terms_over(self, phi, variable):
        ns = AlphaRenaming.NS()
        new_names = BidirectionalDict({FolFormula(variable): FolFormula(variable)})
        def _scan(t):
            if t.root != '=':
                return type(t)(t.root, [_collect(x) or x for x in t.subtrees]) 
        def _collect(t):
            if t.root.kind == 'function':
                try:
                    t_prime = new_names.get_backwards(t)
                    return t_prime
                except KeyError:
                    if t.subtrees and all(new_names.has_key(x) for x in t.subtrees):
                        c = FolFormula(Identifier(u"β%d" % len(new_names), 'variable', ns=ns))
                        new_names[c] = t
                        return c
        return TreeTransform([_scan], dir=TreeTransform.BOTTOM_UP)(phi), new_names
        
    def _add_quantifier_prefix(self, phi, quantifier, new_names):
        _ = FolFormula
        EQ = FolWithEquality.eq
        conj = _.conjunction(_(EQ, [new_name, term]) for new_name, term in new_names.iteritems())
        conn = {_.FORALL: _.IMPLIES, _.EXISTS: _.AND}[quantifier]
        phi = _(conn, [conj, phi])
        for new_name in new_names.iterkeys():
            phi = _(quantifier, [new_name, phi])
        return phi
        
    def _xform_toplevel(self, phi, constants, quantifier_context):
        for c in constants:
            phi, new_names = self._rename_terms_over(phi, c)
            del new_names[FolFormula(c)]
            phi = self._add_quantifier_prefix(phi, quantifier_context, new_names)
        return phi
        
    def _xform(self, t):
        r, s = t.root, t.subtrees
        _ = FolFormula
        if r.kind == 'quantifier':
            u, body = s[0].root, s[1]
            body_prime, new_names = self._rename_terms_over(body, u)
            del new_names[s[0]]
            # e.g. forall u body  --->  forall u (forall v (v1 = f(u) & v2 = f(v1) -> body[v2/f(f(u))]))
            #      exists u body  --->  exists u (exists v (v1 = f(u) & v2 = f(v1) & body[v2/f(f(u))]))
            body_prime = self._add_quantifier_prefix(body_prime, r, new_names)
            return _(t.root, [s[0], body_prime])
                
    def is_fine(self, atom):
        '''Only atoms of the form f(x)=y are allowed to have functions.'''
        r, s = atom.root, atom.subtrees
        if r == FolWithEquality.eq and len(s) == 2:
            return all(not w.subtrees for x in s for w in x.subtrees)
        elif r.kind == 'predicate':
            return all(not x.subtrees for x in s)
        else:
            return True



if __name__ == '__main__':
    from logic.fol.syntax.parser import FolFormulaParser
    from eprv.synopsis.declare import TypeInference

    L = FolFormulaParser()
    f = Identifier('f', 'function')
    g = Identifier('g', 'function')
    sigma = FolManySortSignature.from_sorts( FolSorts({f: u'V→V', g: u'V→V'}) )
    ti = TypeInference()
    ti.declarations = sigma.sorts
    phi = ti(L * "forall u (ite(u=u, f(u) = u, f(u) = g(u)))")
    
    from eprv.synopsis.proof import ProofSynopsis
    ef = EasyFunctionsExtension()
    
    ef.inspect_formula(phi, ProofSynopsis.Context(None, sigma))
    print phi