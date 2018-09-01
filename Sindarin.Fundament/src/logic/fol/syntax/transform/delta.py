# encoding=utf-8
from collections import namedtuple

from pattern.meta.oop import InnerClasses
from adt.tree.transform import TreeTransform
from adt.tree.transform.substitute import TreeSubstitution,\
    TreePatternSubstitution
from logic.fol.syntax.scheme import FolScheme



class DeltaReduction(TreeTransform):
    """
    Expands definitions of symbols in an expression tree.
    A definition is a triplet of head symbol, parameters, and body, written
    as:
    
      f(x,y,z) := ...
    
    Each Transformer instance handles one defined symbol.
    """
    
    IS_DESCENDING = True
    
    class Tuning(object):
        """
        Allows transformation to be tuned by applying some pre-processing
        and post-processing to each substitution step.
        """
        before = staticmethod(lambda x: x)
        after = staticmethod(lambda x: x)
        
    class Tunings(namedtuple("Tuning", "global_ local_")): pass
    
    class Transformer(InnerClasses.Owned):
        
        def __init__(self, owner, head, params=None, body=None):
            """
            If params or body is None, then head should be a formula passed
            to .parse()
            """
            super(DeltaReduction.Transformer, self).__init__(owner)
            if params is not None and body is not None:
                self.head = head
                self.params = params
                self.body = body
            else:
                self.head, self.params, self.body = self.parse(head)

        def __call__(self, t):
            if t.root == self.head:
                if not self.params and not self.body.subtrees:      # e.g. "r := q"
                    return TreeTransform.Scalar(self.body.root)
                elif len(t.subtrees) == len(self.params):     # e.g. "r := p(a,b)" or "r(a) := p(a,b)"
                    tun = self.o.tuning
                    subst = dict(map(self._single_out, zip(self.params, t.subtrees)))
                    body = tun.local_.before(self.body)
                    return tun.local_.after(TreeSubstitution(subst)(body))
            
        def _single_out(self, (t1, t2)):
            """ (auxiliary method) If both trees are singletons (no children),
            returns just their roots."""
            if not t1.subtrees and not t2.subtrees:
                return t1.root, t2.root
            else:
                return t1, t2
    
        @classmethod
        def parse(cls, definition):
            """Helper to parse a definition that is itself written as an 
            expression with the designated operator ':='.
            @param definition: an FolFormula instance
            """
            r, s = definition.root, definition.subtrees
            if r == ':=' and len(s) == 2:
                lhs, rhs = s
                return (lhs.root, lhs.subtrees, rhs)
            else:
                raise ValueError, "not a definition"
            
        @classmethod
        def _mkparser(cls):
            from logic.fol.syntax.parser import LexerRules, FolFormulaParser
            defops = [(":=", 2, LexerRules.opAssoc.RIGHT)]
            return FolFormulaParser(operators=FolFormulaParser.OPERATORS+defops)

    def __init__(self, transformers=[], **kw):
        super(DeltaReduction, self).__init__(transformers, **kw)
        self.tuning = self.Tunings(global_=self.Tuning(), local_=self.Tuning())
        
    def parse_definition(self, definition):
        return self.Transformer(self, definition)
        
    def __call__(self, t):
        t = self.tuning.global_.before(t)
        t = super(DeltaReduction, self).__call__(t)
        return self.tuning.global_.after(t)



class PatternDeltaReduction(TreePatternSubstitution, DeltaReduction):
    
    class SimpleRewrite(DeltaReduction.Transformer): pass
    
    class ExtendedRewrite(TreePatternSubstitution.Transformer): pass
    
    class Substitution(TreePatternSubstitution.Substitution):
        def __init__(self, owner, *a, **kw):
            super(PatternDeltaReduction.Substitution, self).__init__(*a, **kw)
            self.o = owner 
        def __call__(self, match_object):
            tun = self.o.tuning
            _t = tun.local_.before(self.template)
            _s = TreePatternSubstitution.Substitution(_t)
            # hack for allowing r:=s to match in r(x,y)
            def trim(t): return t.root if not t.subtrees else t
            match_object.groups = {k: trim(v) for k,v in match_object.groups.iteritems()}
            return tun.local_.after(_s(match_object))
    
    def parse_definition(self, definition):
        """Helper to parse a definition that is itself written as an 
        expression with the designated operator ':='.
        @param definition: an FolFormula instance
        @return if the definition is a simple reduction of the form
           f(a,b,c) := some term
          with a, b, and c all different symbols, then a 
          DeltaReduction.Transformer is returned.
          Otherwise an ExtendedRewrite transformer is returned.
        """
        r, s = definition.root, definition.subtrees
        if r == ':=' and len(s) == 2:
            lhs, rhs = s
            seen = set()
            for x in lhs.subtrees:
                if x.subtrees or x.root.kind in ['function'] or x.root in seen: break
                seen.add(x.root)
            else:
                # all ok - return plain DeltaReduction.Transformer instance
                return DeltaReduction.Transformer(self, definition)
            # broken from loop - return an ExtendedRewrite
            return self.ExtendedRewrite(FolScheme(lhs, placeholders=FolScheme.BY_ROLE).pattern,
                                        self.Substitution(self, rhs))
        else:
            raise ValueError, "not a definition: '%s'" % definition
            
    
        



if __name__ == '__main__':
    from logic.fol.syntax.parser import FolFormulaParser
    
    L = FolFormulaParser()
    s = FolScheme(L * "wp([;](s1,s2), Q)", placeholders=FolScheme.BY_ROLE)
    print s.placeholders
    for n in s.formula.nodes:
        print n.root, n.root.kind, n.root.tags 
    pat = s.pattern
    print pat.match(L * "wp([;]([x:=y](i,j), return(j)), [n*](i,j))")
    print pat.match(L * "wp([;]([x:=y](i,j), return(j)), [n*](i,j), K)")
    print pat.match(L * "wp([+]([x:=y](i,j), return(j)), [n*](i,j))")
    
    pdr = PatternDeltaReduction()
    L = pdr.SimpleRewrite._mkparser()
    pdr.transformers += [pdr.parse_definition(L * "wp([;](s1,s2), Q) := wp(s1, wp(s2, Q))"),
                         pdr.parse_definition(L * "wp(`skip, Q) := Q"),
                         pdr.parse_definition(L * "wp(return(x), Q) := dr(retval := x, Q)")]
    print pdr(L * "P -> wp([;]([x:=y](i,j), return(j)), [n*](i,j))")