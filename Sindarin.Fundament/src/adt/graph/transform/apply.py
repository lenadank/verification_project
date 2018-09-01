
from adt.graph import GraphScan, DFS
from adt.graph.clone import DigraphCloning


class ApplyTo(GraphScan.Visitor):
    
    def __init__(self, nodes=lambda x: x, edges=lambda x: x):
        self.noperation = nodes
        self.eoperation = edges
        self.skip_none = True
        
    def inplace(self, g):
        DFS(g).scan(self)
        return g
    
    def as_new(self, g):
        g = DigraphCloning.clone(g)
        return self.inplace(g)

    def visit_node(self, node):
        if self._filter(node):
            node.label = self.noperation(node.label)

    def visit_edge(self, edge):
        if self._filter(edge):
            edge.label = self.eoperation(edge.label)

    def _filter(self, o):
        return o.label is not None or not self.skip_none