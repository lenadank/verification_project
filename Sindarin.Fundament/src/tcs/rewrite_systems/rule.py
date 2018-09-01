

class RewriteRule(object):
    
    def inplace(self, expression):
        raise NotImplementedError

    def dryrun(self, expression):
        """expression -> [l1,l2,...] list of locations"""
        raise NotImplementedError
    
    
    
class RewriteRuleBase(RewriteRule):
    
    def __init__(self, premise, replacement):
        self.premise = premise
        self.replacement = replacement
        
    def __repr__(self):
        sup = unicode(self.premise)
        sdn = unicode(self.replacement)
        sep = '-' * max(len(sup), len(sdn))
        return u"\n".join([sup, sep, sdn])
