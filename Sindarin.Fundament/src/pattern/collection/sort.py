

class SortBy(object):
    
    def __init__(self, sorting_key=lambda x: x):
        self.sorting_key = sorting_key
        
    def __call__(self, elements):
        tagged_elements = [Tagged(self.sorting_key(x)).with_(value=x)
                           for x in elements]
        return [x.value for x in sorted(tagged_elements)]


class Tagged(object):
    """
    Given a literal object, "behaves" just like that object in all aspects
    related to sorting (compare, hash), but allows additional attributes which
    do not affect this behavior.
    """
    
    def __init__(self, literal):
        self.literal = literal

    def with_(self, **kw):
        self.__dict__.update(kw)
        return self
        
    def __eq__(self, other):
        if isinstance(other, Tagged):
            return self.literal == other.literal
        else:
            return self.literal == other
        
    def __ne__(self, other):
        return not self == other
    
    def __gt__(self, other):
        if isinstance(other, Tagged):
            return self.literal > other.literal
        else:
            return self.literal > other
        
    def __lt__(self, other):
        if isinstance(other, Tagged):
            return self.literal < other.literal
        else:
            return self.literal < other
        
    def __hash__(self):
        return hash(self.literal)

    def __repr__(self):
        return `self.literal`
    
    def __str__(self):
        return str(self.literal)


if __name__ == "__main__":
    words = ["abbastanza", "pensare", "lo", "proprio", "c'e", "mi", "dire"]
    print SortBy(len)(words)
