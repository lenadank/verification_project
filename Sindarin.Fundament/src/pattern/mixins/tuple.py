

class TupleMixin(object):

    def __hash__(self):
        return hash(self.tuple())

    def __eq__(self, other):
        if isinstance(other, self.COMPAT):
            return self.tuple() == other.tuple()
        else:
            return NotImplemented
    
    def __lt__(self, other):
        if isinstance(other, self.COMPAT):
            return self.tuple() < other.tuple()
        else:
            return NotImplemented

    def __ne__(self, other):
        return not (self == other)

    def __iter__(self):
        return iter(self.tuple())


TupleMixin.COMPAT = TupleMixin
