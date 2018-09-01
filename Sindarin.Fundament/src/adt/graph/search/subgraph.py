
from pattern.collection.basics import DictionaryWithAdd
from pattern.quantifier import exists
import re



class SubgraphPattern(object):
    
    class MatchObject(object):
        
        def __init__(self, edges=set(), groupdict={}):
            self.edges = set(edges)
            self._groupdict = DictionaryWithAdd(groupdict)
        
        def groupdict(self):
            return self._groupdict
        
        def __repr__(self):
            return "%r | %r" % (self.edges, self._groupdict)
        
        def __add__(self, other):
            if isinstance(other, SubgraphPattern.MatchObject):
                return type(self)(self.edges | other.edges,
                                  self._groupdict + other._groupdict)
            else:
                return NotImplemented
            
        def conflicts(self, other):
            d1 = self._groupdict
            d2 = other._groupdict
            return exists(set(d1) & set(d2),
                          lambda k: d1[k] != d2[k])
    
    def __init__(self, template):
        self.template = template
        self.label_matcher = re.match
    
    def match_edge(self, pedge, tedge):
        match = self.label_matcher
        mo_s = match(pedge.source.label, tedge.source.label)
        mo_t = match(pedge.destination.label, tedge.destination.label)
        mo_l = self.match_edge_label(pedge.label, tedge.label)
        if mo_s and mo_t and mo_l:
            d = DictionaryWithAdd(mo_s.groupdict()) + mo_t.groupdict() + mo_l.groupdict()
            return self.MatchObject([tedge], d)
        else:
            return None

    def match_edge_label(self, plabel, tlabel):
        if plabel == tlabel:
            return self.MatchObject()
        elif plabel is None or tlabel is None:
            return None
        else:
            return self.label_matcher(plabel, tlabel)

    def match(self, text):
        pattern = self.template
        layer = [self.MatchObject()]
        
        # Match edge by edge all-to-all
        for pedge in pattern.edges:
            next_layer = []
            for tedge in text.edges:
                mo = self.match_edge(pedge, tedge)
                if mo:
                    for state in layer:
                        if not mo.conflicts(state):
                            next_layer.append(state + mo)
            layer = next_layer
            
        # Get MatchObjects where all pattern edges have been matched
        num_pedges = len(set(pattern.edges))
        return [leaf for leaf in layer
                if len(leaf.edges) == num_pedges]
