# encoding=utf-8

import copy
import random
from pattern.mixins.promote import SimplisticPromoteMixIn



class PickableSpace(object):
    """
    An interface for spaces which know how to generate a random element.
    TODO: Actually, this interface shouldn't go here. Put in in collection perhaps.
    """
    def pick(self):
        raise NotImplementedError

    @staticmethod
    def pick_with_fallback(space, fallback=random.choice):
        if isinstance(space, PickableSpace):
            return space.pick()
        else:
            return fallback(space)



class MuxSpaceCore(PickableSpace):

    container = dict

    def using(self, container):
        self.container = container
        return self

    def __iter__(self):
        cursor = [(x, [iter(self._range_of(x))]) for x in self.domain]
        start = True
        fin = False
        d = self._container(self.domain)
        if len(cursor) == 0:
            yield self._copy(d)
            return
        while not fin:
            for x,y in cursor:
                try:
                    d[x] = y[0].next()
                    fin = False
                    if not start: break
                except StopIteration:
                    y[0] = iter(self._range_of(x))
                    d[x] = y[0].next()
                    fin = True
            else:
                start = False
            if not fin:
                yield self._copy(d)
    
    def pick(self):
        """
        Picks one of the elements at random.
        """
        d = self._container(self.domain)
        for x in self.domain:
            d[x] = PickableSpace.pick_with_fallback(self._range_of(x))
        return self._copy(d)
    
    def _container(self, domain):
        return self.container()
    
    def _range_of(self, domain_element):
        raise NotImplementedError
    
    def _copy(self, d):
        return copy.copy(d)


class FunctionSpace(MuxSpaceCore):
    """
    Provides an exhaustive search of all possible total mappings from a given
    domain to a given range.
    """
    
    def __init__(self, domain, range):  #@ReservedAssignment
        self.domain = domain
        self.range = range
        
    def _range_of(self, domain_element):
        return self.range
    
    
class SplitSpace(MuxSpaceCore):

    def __init__(self, domain_enumerations={}):
        self.domain = domain_enumerations.keys()
        self.ranges = domain_enumerations
        
    def _range_of(self, domain_element):
        return self.ranges[domain_element]


class CartesianProduct(MuxSpaceCore):
    """
    """
    
    container = tuple
    
    def __init__(self, *factors):
        """
        @param elements: element domain (D)
        @param power: power rank (r)
        """
        self.factors = factors
        self.domain = xrange(len(factors))
        
    def _range_of(self, domain_element):
        return self.factors[domain_element]
    
    def _container(self, domain):
        return [None] * len(domain)
    
    def _copy(self, d):
        return self.container(d)


class CartesianPower(MuxSpaceCore):
    """
    Goes over all combinations of (d₁, d₂, d₃, ... , dᵣ)
    where dᵢ∈D for all 1≤i≤r
    """
    
    container = tuple
    
    def __init__(self, elements, power):
        """
        @param elements: element domain (D)
        @param power: power rank (r)
        """
        self.elements = elements
        self.domain = xrange(power)
        
    def _range_of(self, domain_element):
        return self.elements
    
    def _container(self, domain):
        return [None] * len(domain)
    
    def _copy(self, d):
        return self.container(d)
    

class Domain(PickableSpace):

    def __init__(self, iterable):
        self.iterable = iterable
    
    def __repr__(self):
        return u"{%s}" % ", ".join(`x` for x in self.iterable)
    
    def __len__(self):
        return len(self.iterable)
    
    def __iter__(self):
        return iter(self.iterable)
    
    def pick(self):
        return random.choice(self.iterable)
    
    def __mul__(self, other):
        if not isinstance(other, Domain):
            return NotImplemented
        else:
            return type(self)(CartesianProduct(self.iterable,
                                               other.iterable))
    
    def __xor__(self, rank):
        if rank == 0:
            return ((),)
        else:
            return CartesianPower(self, rank)
    
    def __pow__(self, rank):
        if rank == 0:
            return ((),)
        elif rank == 1:
            return self
        else:
            return CartesianPower(self, rank)


class MultiDomain(dict, PickableSpace, SimplisticPromoteMixIn):
    
    def __init__(self, iterable_or_mapping):
        if not isinstance(iterable_or_mapping, dict):
            iterable_or_mapping = {'V': iterable_or_mapping}
        super(MultiDomain, self).__init__(iterable_or_mapping)

    def __iter__(self):
        return self.iterelements()

    def iterelements(self):
        for subset in self.itervalues():
            for x in subset:
                yield x
    
    def __contains__(self, element):
        return element in iter(self)
    
    def __getitem__(self, factors):
        sd = self.get(factors, None)
        if sd is not None:
            return sd
        else:
            sd = tuple(self.get(factor, ()) for factor in factors)
            return CartesianProduct(*sd)
    
    def pick(self):
        return random.choice(iter(self))



if __name__ == '__main__':
    abc_12 = FunctionSpace([1,2], ['a','b','c'])
    io3 = CartesianPower('io', 3).using(lambda x: "".join(x))

    for y in abc_12:
        print y
    print "->", abc_12.pick()
        
    for h in io3:
        print h
    print "->", io3.pick()
    
    print SplitSpace({'y': abc_12, 'h': io3}).pick()
    