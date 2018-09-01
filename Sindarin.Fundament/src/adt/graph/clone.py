from adt import graph
import copy


class ClonedNodes(dict):
    
    def __getitem__(self, node):
        try:
            return super(ClonedNodes, self).__getitem__(node)
        except KeyError:
            c = self.clone(node)
            super(ClonedNodes, self).__setitem__(node, c) 
            return c
    
    def clone(self, node):
        new_node = copy.copy(node)
        new_node.incident_out = []
        return new_node


class ClonedEdges(ClonedNodes):
    
    def __init__(self, cloned_nodes):
        super(ClonedEdges, self).__init__()
        self.cloned_nodes = cloned_nodes
    
    def clone(self, edge):
        u, v = edge.source, edge.destination
        e = self.cloned_nodes[u].connect(self.cloned_nodes[v])
        e.__dict__.update(edge.get_attributes())
        return e
    


class SelectiveCloneVisitor(graph.GraphScan.Visitor):
    """
    Clones nodes and edges that match a certain predicate.
    """
    
    def __init__(self, predicate):
        self.predicate = predicate
        self.cloned_nodes = ClonedNodes()
        self.cloned_edges = ClonedEdges(self.cloned_nodes)
        self.cloned_roots = set()
         
    def visit_node(self, node):
        if self.predicate(node):
            self.cloned_roots.add(self.cloned_nodes[node])
            
    def visit_edge(self, edge):
        if self.predicate(edge):
            self.cloned_edges[edge]
            
    def clone_roots(self, roots):
        return self.cloned_roots


class CloneVisitor(SelectiveCloneVisitor):
    """
    Clones all of a digraph's nodes and edges, except those specified
    in an exclude list.
    """

    def __init__(self, without=set()):
        """
        @param without a set of nodes and arcs to exclude from the cloned
          digraph
        """
        super(CloneVisitor, self).__init__(lambda x: x not in without)
        
    def clone_roots(self, roots):
        return [self.cloned_nodes[r] for r in roots]


class SelectiveCloneVisitorForConnectedComponent(SelectiveCloneVisitor):
    """
    Same as SelectiveCloneVisitor, but the resulting root set is
    limited to the the intersection of the original root set and the
    subset selected by the predicate.
    """

    def clone_roots(self, roots):
        root_shadows = [self.cloned_nodes.get(r) for r in roots
                        if r in self.cloned_nodes]
        return self.cloned_roots.intersection(root_shadows)


class SubgraphCloneVisitor(SelectiveCloneVisitorForConnectedComponent):
    
    def visit_edge(self, edge):
        if self.predicate(edge) or \
           (self.predicate(edge.source) and self.predicate(edge.destination)):
            self.cloned_edges.clone(edge)


class AttributesClone(object):

    def clone_attributes_from(self, other, node_mapping):
        pass


class DigraphCloning:

    @classmethod
    def clone(cls, g, roots=None, without=set(), visitor=None):
        cloned, visitor = cls.clone_with_visitor(g, roots, without, visitor)
        return cloned
    
    @classmethod
    def clone_mapped(cls, g, roots=None, without=set(), visitor=None):
        cloned, visitor = cls.clone_with_visitor(g, roots, without, visitor)
        cloned.shadow_nodes = visitor.cloned_nodes
        cloned.shadow_edges = visitor.cloned_edges
        return cloned

    @classmethod
    def clone_with_visitor(cls, g, roots=None, without=set(), visitor=None):
        cloned = copy.copy(g)
        if roots is None: roots = g.roots
        scan = graph.DFS(g, roots)
        if visitor is None:
            visitor = CloneVisitor(without=without)
        scan.scan(visitor)
        cloned.roots = visitor.clone_roots(roots)
        if isinstance(g, AttributesClone):
            cloned.clone_attributes_from(g, visitor.cloned_nodes)
        return cloned, visitor

