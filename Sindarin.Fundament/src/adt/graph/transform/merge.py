
from pattern.collection.basics import OneToOne
from pattern.quantifier import exists



class MergeIntoDigraph(object):
    
    class Introduced(set):
        def member(self, generator):
            def gen(*a):
                new_obj = generator(*a)
                self.add(new_obj)
                return new_obj
            return gen
    
    def __init__(self, base_graph):
        self.base_graph = base_graph
        self.key_func = lambda node: node.label
        
    def inplace(self, g):
        G = self.base_graph
        introduced = self.Introduced()
        nodes_bykey = OneToOne({self.key_func(x): x
                                for x in G.nodes}) \
                        .of(introduced.member(G.Node))
        
        for edge in g.edges:
            s, t = [nodes_bykey[self.key_func(x)] for x in edge.ends]
            if not self._already_connected(s, t, edge.label):
                s.connect(t).label = edge.label
        
        # Compute rootset
        nodeset = set(G.nodes)
        for n in introduced:
            if n not in nodeset:
                G.roots.append(n)
        
        return G

    def _already_connected(self, s, t, label):
        return exists(s.get_incident_out(),
                      lambda e: e.destination is t and e.label == label)
