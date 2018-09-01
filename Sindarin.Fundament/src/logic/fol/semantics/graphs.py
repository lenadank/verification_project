
from adt.graph import Digraph
from adt.graph.build import RootSetTool
from logic.fol import Identifier, FolSignature, FolStructure
from pattern.functor import Labeled
from pattern.infinity import INF
import collections
from pattern.quantifier.mux import CartesianPower
from pattern.collection.basics import Cabinet



class AlgebraicStructureGraphTool(object):
    
    def __init__(self, logic_structure, binary_preds):
        self.structure = logic_structure
        self.signature = FolSignature(preds=[(p,2) for p in binary_preds])
        self.root_consts = []
        self.individual_types = [int, str]
        
    def is_individual(self, value):
        for tpe in self.individual_types:
            if isinstance(value, tpe): return True
        else:
            return False
        
    def __call__(self):
        I = self.structure.interpretation \
            if isinstance(self.structure, FolStructure) else self.structure
        iq = self.is_individual
        
        binary_preds = [p for (p,arity) in self.signature.preds 
                        if arity == 2 and p in I]
        unary_funcs = [f for (f,arity) in self.signature.funcs
                       if arity == 1 and f in I]
        
        elements = set(self.structure.domain) \
           if isinstance(self.structure, FolStructure) else \
           set([x for r in binary_preds for v in I[r] for x in v if v != 'else'])
        constants = dict((k,v) for k,v in I.iteritems() if iq(v))
        #unary_funcs = set([k for k,v in I.iteritems()
        #                   if isinstance(v, dict) and
        #                   [e for e in v.iterkeys() if not iq(e)] == [] and
        #                   [e for e in v.itervalues() if not iq(e)] == []]
        #                   )

        elements.update(constants.itervalues())
        elements.update(v for f in unary_funcs
                           for xy in I[f].iteritems()
                            for v in xy if v != 'else')
        
        nodes = dict((x, Digraph.Node(x)) for x in elements)
        
        for p in binary_preds:
            if p in I:
                if isinstance(I[p], collections.Mapping):
                    for (uv,b) in I[p].iteritems():
                        if uv != 'else' and b:
                            u, v = uv
                            nodes[u].connect(nodes[v]).label = p
                else:
                    r = I[p]
                    for u,v in CartesianPower(elements, 2):
                        if r(u, v):
                            nodes[u].connect(nodes[v]).label = p
                        
        for f in unary_funcs:
            for x,y in I[f].iteritems():
                if x != 'else':
                    nodes[x].connect(nodes[y]).label = f
                    
        # Label nodes more meaningfully using constant names from the 
        # structure where available
        names_by_consts = Cabinet() \
            .with_key(lambda u: u) \
            .updated((v,k) for k,v in sorted(constants.items())
                     if unicode(k) != unicode(v))

        for name, consts in names_by_consts.iteritems():
            nodes[name].label = ' '.join(map(unicode, consts)) 

        # Determine the root set
        if self.root_consts:
            g = Digraph()
            g.roots = [nodes[constants[c]] for c in self.root_consts]
        else:
            g = RootSetTool()(nodes.values())
        return g




class GraphStructure(object):
    
    E = Identifier('E', 'predicate')
    w = Identifier('w', 'function')
    
    def __init__(self, g, weighted=False):
        self.g = g
        self.weighted = weighted
        
    def structure(self):
        has_edge = Labeled("has_edge", lambda u,v: v in u.get_adjacent_out())
        interpretation = {self.E: has_edge}
        if self.weighted:
            get_weight = Labeled("weight", lambda u,v: has_edge(u,v) and 
                                 min(e.label for e in u.get_edges_to(v)) or INF)
            interpretation[self.w] = get_weight
        m = FolStructure(self.g.nodes, interpretation)
        return m
