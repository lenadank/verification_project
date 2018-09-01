# encoding=utf-8
from adt.tree.transform.substitute import TreeSubstitution
from logic.fol.syntax.transform.alpha import AlphaRenaming



class FastSubstitutionOperator(object):
    
    def __call__(self, phi):
        return self.Operation()(AlphaRenaming()(phi))

    class Operation:
        def __init__(self):
            self.scopes = [{}]
        
        def __call__(self, phi):
            r, s = phi.root, phi.subtrees
            if r == 'dr':
                new_scope = self.scopes[-1].copy()
                for eq in s[:-1]:
                    assert eq.root == ':='
                    lhs, rhs = eq.subtrees
                    assert not any(x.subtrees for x in lhs.subtrees)
                    new_scope[lhs.root] = (lhs.subtrees, self(rhs))
                    
                self.scopes.append(new_scope)
                    
                self(s[-1])
                phi.root, phi.subtrees = s[-1].root, s[-1].subtrees
                del self.scopes[-1]
            else:
                r_ = self.scopes[-1].get(r)
                if r_:
                    if len(r_[0]) == len(s):
                        if not s: 
                            phi.root, phi.subtrees = r_[1].root, r_[1].subtrees
                        else:
                            dphi = TreeSubstitution({k.root: v for k,v in zip(r_[0], s)})(r_[1])
                            phi.root, phi.subtrees = dphi.root, dphi.subtrees
                    elif not r_[1].subtrees:  #  Special case:   dr(b := R, b(x)) --> R(x)
                        phi.root = r_[1].root
    
                for x in s: self(x)
    
            return phi
    
    def inspect_formula(self, phi, ctx=None):
        self(phi)
        



if __name__ == '__main__':
    fso = FastSubstitutionOperator()
    from eprv.synopsis.expand import Expansion
    L = Expansion.FormulaReader().parser

    phi = L * "forall u (dr(x := u, P(x) | dr(Q(z) := P(z) | P(x), Q(z)) ))"
    phi = L * "dr(f(u) := h(u), dr(f(u) := f(f(u)), g(u) := f(u), P(g(u), f(u))))"
    
    print phi
    
    fso(phi)
    
    print phi