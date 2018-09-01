
class PosInf(object):
    def __lt__(self, other): return False
    def __gt__(self, other): return not self == other
    def __eq__(self, other): return isinstance(other, PosInf)
    def __neg__(self): return NegInf()
    def __add__(self, other): return self
    def __sub__(self, other): return self
    def __radd__(self, other): return self
    def __rsub__(self, other): return -self
    def __repr__(self): return "INF"

class NegInf(object):
    def __lt__(self, other): return not self == other
    def __gt__(self, other): return False
    def __eq__(self, other): return isinstance(other, NegInf)
    def __neg__(self): return INF
    def __add__(self, other): return self
    def __sub__(self, other): return self
    def __radd__(self, other): return self
    def __rsub__(self, other): return -self
    def __repr__(self): return "-INF"

INF = PosInf()

