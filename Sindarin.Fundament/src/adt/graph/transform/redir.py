
from adt.graph import clone


class Reverse(object):
    """
    Computes the reverse (transpose) of a digraph by exchanging the source and
    destination of each arc.
    """
    
    class AltClonedEdges(clone.ClonedEdges):
        def clone(self, edge):
            u, v = edge.source, edge.destination
            e = self.cloned_nodes[v].connect(self.cloned_nodes[u])
            e.__dict__.update(edge.get_attributes())
            return e


    def as_new(self, g):
        new_g, _ = self.as_new_with_visitor(g)
        return new_g

    def as_new_mapped(self, g):
        new_g, visitor = self.as_new_with_visitor(g)
        new_g.shadow_nodes = visitor.cloned_nodes
        new_g.shadow_edges = visitor.cloned_edges
        return new_g

    def as_new_with_visitor(self, g):
        v = clone.SelectiveCloneVisitor(predicate=lambda x: True)
        v.cloned_edges = self.AltClonedEdges(v.cloned_nodes)
        return clone.DigraphCloning.clone(g, visitor=v), v
        