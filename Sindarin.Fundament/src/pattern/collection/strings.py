
import re



class MultiSubstitution(object):
    
    def __init__(self, substitutions={}):
        # - sort matched substrings from longest to shortest
        #   (this is to deal with e.g. {'a': '1', 'aa': '2'})
        keys = sorted(substitutions, key=len, reverse=True)
        self.rexp = re.compile('|'.join(re.escape(k) for k in keys))
        self.subst = substitutions
        
    def __call__(self, s):
        return self.rexp.sub(self._repl, s)
        
    def _repl(self, mo):
        return self.subst[mo.group()]
