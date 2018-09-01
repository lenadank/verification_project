

class TreePattern(object):

    class MatchObject(object):
        def __init__(self, at, groups):
            self.at = at
            self.groups = groups
        def groupdict(self):
            return self.groups
        def __repr__(self):
            return "matched %r" % self.groups

    def match(self, tree):
        raise NotImplementedError
    

class TreeRootPattern(TreePattern):
    
    def __init__(self, root_symbol, fan=None):
        self.symbol = root_symbol
        self.fan = fan
    
    def match(self, tree):
        r = tree.root
        s = tree.subtrees
        if r == self.symbol and (self.fan is None or self.fan == len(s)):
            numeral = lambda i: ("$%d"%(i+1))
            children = dict((numeral(i), s[i]) for i in xrange(len(s)))
            return self.MatchObject(tree, children)


class TreeRootCriterion(TreePattern):
    
    def __init__(self, root_criterion, fan=None):
        self.criterion = root_criterion
        self.fan = fan
    
    def match(self, tree):
        r = tree.root
        s = tree.subtrees
        if self.criterion(r) and (self.fan is None or self.fan == len(s)):
            numeral = lambda i: ("$%d"%(i+1))
            children = dict((numeral(i), s[i]) for i in xrange(len(s)))
            children["$0"] = r
            return self.MatchObject(tree, children)


class TreeTopPattern(TreePattern):
    
    def __init__(self, tree_template):
        self.template = tree_template
        
    def match(self, tree):
        comp = self._match(self.template, tree)
        if comp is None:
            return None
        else:
            return self.MatchObject(tree, comp)
    
    def _match(self, pattern, text):
        pr = pattern.root
        tr = text.root
        if self._is_subtree_placeholder(pr):
            return {pr: text}
        elif self._is_node_placeholder(pr):
            return self._rematch_subtrees(pattern, text, {pr: text.root})
        else:
            rmo = self.scalar_match(pr, tr)
            if rmo is not None:
                return self._rematch_subtrees(pattern, text, rmo.groups)
            else:
                return None
        
    def __repr__(self):
        return `self.template`
        
    def scalar_match(self, pattern, text):
        if pattern == text:
            return self.MatchObject(text, {})
        else:
            return None
        
    def _rematch_subtrees(self, pattern, text, acc):
        ps = pattern.subtrees
        ts = text.subtrees
        ellipsis = [i for i in xrange(len(ps)) 
                    if self._is_subtrees_placeholder(ps[i].root)] 
        if not ellipsis and len(ps) == len(ts):
            for i in xrange(len(ps)):
                mo = self._match(ps[i], ts[i])
                if mo is None: return None
                acc.update(mo)
            return acc
        elif ellipsis and len(ps) <= len(ts) + len(ellipsis):
            if len(ellipsis) > 1: raise NotImplementedError, "more than one ellipsis child"
            for i in xrange(ellipsis[0]):
                mo = self._match(ps[i], ts[i])
                if mo is None: return None
                acc.update(mo)
            for i in xrange(len(ps) - ellipsis[0] - 1):
                mo = self._match(ps[-1-i], ts[-1-i])
                if mo is None: return None
                acc.update(mo)
            acc[ps[ellipsis[0]].root] = ts[ellipsis[0]:ellipsis[0]+len(ts)-len(ps)+1]
            return acc
        else:
            return None
        
    def _is_text(self, s):
        return isinstance(s, str) or isinstance(s, unicode)
        
    def _is_node_placeholder(self, node_value):
        return self._is_text(node_value) and node_value.startswith("?")

    def _is_subtree_placeholder(self, node_value):
        return self._is_text(node_value) and node_value.startswith("$")
    
    def _is_subtrees_placeholder(self, node_value):
        return self._is_text(node_value) and node_value.startswith("$") and node_value.endswith("...")
    

class ConditionalPattern(TreePattern):
    """
    Allows to enforce a criterion atop an existing formula. The criterion
    is applied to the match object, and if it is satisfied, the match is
    accepted; otherwise it is rejected.
    """

    def __init__(self, pattern, condition):
        self.pattern = pattern
        self.condition = condition

    def match(self, expression):
        if self.pattern:
            g = self.pattern.match(expression)
        else:
            g = {}
        if g is not None and self.condition(g.groups):
            return g
        else:
            return None

    def __repr__(self):
        return "%r if %r" % (self.pattern or "_", self.condition)

    class Condition(object):
        """
        Extend to define condition classes.
        """
        def __rand__(self, scheme):
            if isinstance(scheme, TreePattern):
                return ConditionalPattern(scheme, self)
            elif hasattr(scheme, 'pattern'):
                c = ConditionalPattern.Condition()
                c.pattern = scheme.pattern & self
                return c
            else:
                return NotImplemented
        def __invert__(self):
            return ConditionalPattern.ConditionComplement(self)
            
    class ConditionComplement(Condition):
        def __init__(self, condition):
            self.condition = condition
        def __call__(self, groups):
            return not self.condition(groups)
        def __repr__(self):
            return u"not %r" % self.condition
            
    class FunctorCondition(Condition):
        def __init__(self, functor):
            self.functor = functor
        def __call__(self, groups):
            return self.functor(groups)
        def __repr__(self):
            return `self.functor`



# Snippet
if __name__ == '__main__':
    from adt.tree.build import TreeAssistant as TA
    pat = TA.build(('a', [('?', ['$1...']), ('c', ['$', '$2...'])]))
    txt = TA.build(('a', ['b', ('c', [('d', ['e', 'f']), 'k','j'])]))
    print "pattern:", pat
    print "text:   ", txt
    print TreeTopPattern(pat).match(txt)