
from adt.graph import AbstractDigraph
from adt.graph.partition import Partition
from adt.graph.format import DigraphFormatter
from pattern.collection import Cabinet
from pattern.debug import trace
from pattern.lazy import Lazy



class TotalMatching(dict):

    def __init__(self, d=None):
        super(TotalMatching, self).__init__()
        if d is None:
            pass
        elif isinstance(d, dict):
            for k,v in d.iteritems(): self[k] = v
        else:
            for k,v in d: self[k] = v
    
    def __setitem__(self, key, value):
        super(TotalMatching, self).__setitem__(key, value)
        super(TotalMatching, self).__setitem__(value, key)


class MutualComponent(Partition.Component):
    """
    Two sets which "behave" as one. Union, intersection, and difference are
    done on both sets as well on their union.
    """
    
    def __init__(self, set1=None, set2=None):
        if set1 is None: set1 = set()
        if set2 is None: set2 = set()
        super(MutualComponent, self).__init__(set1 | set2)
        self.set1 = set1
        self.set2 = set2
        
    def __or__(self, other):
        if isinstance(other, MutualComponent):
            return MutualComponent(self.set1 | other.set1,
                                   self.set2 | other.set2)
        else:
            return NotImplemented
        
    def __and__(self, other):
        if isinstance(other, MutualComponent):
            return MutualComponent(self.set1 & other.set1,
                                   self.set2 & other.set2)
        else:
            return NotImplemented
        
    def __sub__(self, other):
        if isinstance(other, MutualComponent):
            return MutualComponent(self.set1 - other.set1,
                                   self.set2 - other.set2)
        else:
            return NotImplemented

    def __rmod__(self, formatter):
        return " / ".join(" ".join(formatter(x) for x in s)
                          for s in (self.set1,self.set2))
        
    def __repr__(self):
        return "%s([%s])" % (type(self).__name__, repr % self)
        
        
class MutualSubcomponent(MutualComponent):
    """
    A MutualComponent which also supports coherent addition of elements,
    provided that all elements added are members of a given super-component
    so that it can be inferred which of the two sets it belongs to.
    """

    def of(self, super_component):
        self.super = super_component
        return self
        
    def add(self, element):
        if element in self.super.set1:
            self.set1.add(element)
        elif element in self.super.set2:
            self.set2.add(element)
        else:
            raise ValueError, "%r not in super-component" % element
        super(MutualSubcomponent, self).add(element)


class DAGIsomorphism(object):
    """
    Computes a 1:1 function from the parts of one directed graph unto another.
    """
    
    def __init__(self, color_func=lambda x: x.label):
        self.color = color_func
        self.trace = trace.off
    
    def __call__(self, g1, g2):
        worklist = [(g1.roots, g2.roots)]
        partial_matching = Partition(g1)

        formatter = DigraphFormatter()

        while worklist:
            pass; self.trace(Lazy(__repr__=lambda: formatter % partial_matching))
            u1, u2 = worklist.pop()
            matching = self.match_set(u1, u2)
            if matching is None:
                return None
            else:
                for bucket in matching:
                    if partial_matching.refine(bucket):
                        v1, v2 = [set(e for part in bucket_set
                                      for e in self.get_incident_out(part))
                                  for bucket_set in (bucket.set1, bucket.set2)]
                        worklist.append((v1, v2))
                if not self.equilibrium(partial_matching):
                    return None
        
        while self.backtrace(partial_matching):
            pass; self.trace(Lazy(__repr__=lambda: formatter % partial_matching))
            if not self.equilibrium(partial_matching):
                return None
        
        # - convert partial matching into total matching
        return TotalMatching((c.set1.pop(), c.set2.pop()) 
                             for c in partial_matching.components
                             if len(c.set1) == 1)
            
    def get_incident_out(self, part):
        if isinstance(part, AbstractDigraph.Node):
            return part.get_incident_out()
        elif isinstance(part, AbstractDigraph.Edge):
            return [part.destination]
        else:
            raise TypeError, type(part)
    
    def equilibrium(self, partial_matching):
        """Verifies that all mutual components are of matching cardinality."""
        for component in partial_matching.components:
            if len(component.set1) != len(component.set2):
                return False
        return True
    
    def match_set(self, set1, set2):
        if (len(set1) != len(set2)):
            return None
        
        cab1 = Cabinet().with_key(lambda x: (self.color(x), x))
        cab2 = Cabinet().with_key(lambda x: (self.color(x), x))

        for e1 in set1: cab1.add(e1)
        for e2 in set2: cab2.add(e2)

        matching = []

        for clr in cab1.iterkeys():
            if clr in cab2:
                class1 = cab1[clr]
                class2 = cab2[clr]
                if len(class1) == len(class2):
                    matching.append(MutualComponent(class1, class2))
                else:
                    return None
            else:
                return None 
            
        assert sum(len(x) for x in matching) == len(set1) + len(set2)
        return matching
    
    def backtrace(self, partial_matching):
        refinery = []
        for component in partial_matching.components:
            if len(component.set1) > 1:
                c = Cabinet().of(lambda: MutualSubcomponent().of(component)) \
                        .with_key(lambda x: (partial_matching.
                                             find_component(x.destination), x))
                for s in (component.set1, component.set2):
                    for part in s: c.add(part)
                if len(c) > 1:
                    refinery.extend(c.itervalues())
        for refiner in refinery:
            partial_matching.refine(refiner)
            
        return len(refinery) > 0
    
 
 
if __name__ == "__main__":
    from adt.graph.build import FlowGraphTool
    from adt.graph.format import DEFAULT as formatter
    
    inputs = [((["o1"], lambda a: a),
               (["o2"], lambda a: a)),
               
              ((["1x", "2", "3", "4"],
                lambda a, b, c, d: a >> (b >> c >> "y" >> d | d)),
               (["1y", "2", "3", "4y"],
                lambda a, b, c, d: a >> (d | b >> c >> "y" >> d)))
             ]
    
    for (inx, iny) in inputs:
        gx = FlowGraphTool(inx)()
        gy = FlowGraphTool(iny)()
        
        formatter = DigraphFormatter()
        print formatter(gx)
        print '-' * 10
        print formatter(gy)
        print '-' * 10
    
        iso = DAGIsomorphism(color_func=lambda x: x.label and x.label[0])
        iso.trace = trace.out
        print iso(gx, gy)
        print '-' * 30
