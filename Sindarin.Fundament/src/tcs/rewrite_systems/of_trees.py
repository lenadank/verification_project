
from adt.tree.paths import Path
from adt.tree.search import ScanFor 
from adt.tree.transform.substitute import TreePatternSubstitution

from rule import RewriteRuleBase
from confluence import ConfluentConstrainedRewriteSystem 



class TreeRewriteRule(RewriteRuleBase):
    
    TreePatternSubstitution = TreePatternSubstitution
    
    def __init__(self, premise, replacement):
        """
        @param premise: a TreePattern instance
        @param replacement: a Tree instance (with placeholders where matched
          values should go), or a TreePatternSubstitution.Substitution 
          instance.
        """
        super(TreeRewriteRule, self).__init__(premise, replacement)
    
    def inplace(self, expression):
        if isinstance(expression, Path): expression = expression.end
        tps = self.TreePatternSubstitution({self.premise: self.replacement})
        dl = []
        e = tps.inplace(expression, dl)
        OptimizeRewritesByVocab.maintain(expression, dl)
        if e is not expression:
            expression.root = e.root
            expression.subtrees = e.subtrees
        return dl != []
    
    def dryrun(self, expression):
        if not OptimizeRewritesByVocab._any_chance(self.premise, expression): return []
        return ScanFor(self.premise.match)(expression)



class InnermostRewriteSystem(ConfluentConstrainedRewriteSystem):
    
    def constrain(self, expression, locations):
        inners = set(p.node_at(i)
                     for p, _ in locations 
                       for i in xrange(p.nnodes-1))
        return [(l, rule) for l, rule in locations if l.end not in inners]




class OptimizeRewritesByVocab(object):
    """
    Accelerates matching of tree rewrite rules by storing the set of labels
    that each tree has, and dismissing such rules whose root symbol is not
    in the set without scanning.
    """
    
    def __init__(self, formulas): self.formulas = formulas
    def __enter__(self):          self.set_up(self.formulas); return self
    def __exit__(self, *a):       self.tear_down(self.formulas)
    
    @classmethod
    def set_up(cls, formulas):
        for phi in formulas: 
            vocab = set([n.root for n in phi.nodes])
            for n in phi.nodes: n._vocab = vocab

    @classmethod
    def tear_down(cls, formulas):
        for phi in formulas:
            for n in phi.nodes: #@UnusedVariable
                try:
                    n._vocab.clear()
                    del n._vocab
                except AttributeError:
                    # TODO: why is this happening?
                    pass
    
    @classmethod
    def maintain(cls, expression, differences):
        if hasattr(expression, '_vocab'):
            dl = differences
            expression._vocab.update(n.root for _,l in dl for n in l.nodes)
            for _,l in dl: 
                for n in l.nodes: n._vocab = expression._vocab 
    
    @classmethod
    def _any_chance(cls, scheme, expression):
        try:
            root = scheme.template.root
            vocab = expression._vocab
        except AttributeError:
            return True
        # - This should always hold (but is expensive to check):
        #assert set(n.root for n in expression.nodes) <= vocab:
        return root in vocab
