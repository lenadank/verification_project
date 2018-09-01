
import copy



class SpecializeListMixIn(object):
    """
    Allows subclassing of list while preserving the derived class across
    list operations.
    E.g. if you just subclass naively via "class A(list)" you will get
      A + A ---> list
      A[i:j] ---> list
    Using this mix-in creates the expected behavior
      A + A ---> A
      A[i:j] ---> A 
    """
    
    def singletons(self):
        return (self[i:i+1] for i in xrange(len(self)))

    def __getitem__(self, item):
        s = super(SpecializeListMixIn, self).__getitem__(item)
        if isinstance(item, slice):
            s = type(self)(s)
        return s

    def __getslice__(self, i, j): 
        return self.__getitem__(slice(i,j))

    def __add__(self, other):
        c = copy.copy(self)
        c.extend(other)
        return c
    
    def __iadd__(self, other):
        self.extend(other)

