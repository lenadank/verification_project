


class ConfluentRewriteSystem(object):
    """
    A rewrite system is confluent iff the result of rewriting an expression
    does not depend on the order in which rewrite rules are applied.
    (the length of the rewrite, however, may)
    """
    
    def __init__(self, rules):
        self.rules = rules

    def __call__(self, expression, out_derivation=None):
        return self.asnew(expression, out_derivation)

    def inplace(self, expression, out_derivation=None):
        o = (out_derivation is not None)
        any_change = True
        while any_change:
            any_change = False
            for rule in self.rules:
                d = rule.inplace(expression)
                if d and o: out_derivation.append((rule, `expression`))
                any_change = any_change or d
                    
        return expression
    
    def asnew(self, expression, out_derivation=None):
        import copy
        expression = copy.deepcopy(expression)
        return self.inplace(expression, out_derivation)

    
    
class ConfluentConstrainedRewriteSystem(ConfluentRewriteSystem):
    
    def inplace(self, expression, out_derivation=None):
        o = (out_derivation is not None)
        any_change = True
        while any_change:
            any_change = False
            locations = [(l, rule) for rule in self.rules 
                                     for l in rule.dryrun(expression)]
            c_locations = self.constrain(expression, locations)
            for l, rule in c_locations:
                d = rule.inplace(l)
                if d and o: out_derivation.append((rule, `expression`))
                any_change = any_change or d
                    
        return expression

    def constrain(self, expression, locations):
        return locations
