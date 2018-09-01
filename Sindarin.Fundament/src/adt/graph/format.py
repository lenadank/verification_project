"""
Text Output Formatter
"""

from adt.graph import AbstractDigraph, DFS, CollectNodesVisitor
from pattern.collection import OrderedSet


class DigraphFormatter(object):
    """
    Creates a human-readable textual representation of the graph
    """
    
    default_label = lambda x: x.label
    
    def __init__(self, node_caption_func=default_label, edge_caption_func=default_label):
        self.node_caption_func = node_caption_func
        self.edge_caption_func = edge_caption_func

    def __call__(self, element, container=None):
        if isinstance(element, AbstractDigraph):
            return self.format_graph(element)
        elif isinstance(element, AbstractDigraph.Node):
            return self.format_node(element, g=container)
        elif isinstance(element, AbstractDigraph.Edge):
            return self.format_edge(element, g=container)
        else:
            raise TypeError, "expected graph, node, or edge, '%s' found" % type(element).__name__
        
    def format_graph(self, g):
        _n = lambda x: self._format_node(x, g)
        _e = lambda x: self._format_incident_out(x, g)
        nodes = DFS(g).scan(CollectNodesVisitor(OrderedSet()))
        es = ["%s -> %s" % (_n(node), ", ".join(_e(node)))
              for node in nodes if node.get_incident_out()]
        if len(nodes) == 1: # special case for singleton
            es += [_n(n) for n in nodes]
        return "\n".join(es)

    def format_edge(self, edge, g):
        return "%s -> %s" % (self._format_node(edge.source, g), 
                             self._format_outgoing_edge(edge, g))

    def format_path(self, edges, g):
        tail = None
        o = []
        for edge in edges:
            if edge.source is not tail:
                o.append(self(edge.source))
            if edge.label is None:
                o.append("->")
            else:
                o.append("-|%s|->" % self.edge_caption_func(edge))
            o.append(self(edge.destination))
            tail = edge.destination
        if o:
            return " ".join(o)
        else:
            return getattr(edges, 'source', ".")
        
    def format_node(self, node, g=None):
        return self._format_node(node, g)

    def _format_node(self, node, g):
        return "%s" % (self.node_caption_func(node),)

    def _format_outgoing_edge(self, edge, g):
        r = self._format_node(edge.destination, g)
        if edge.label is None:
            return r
        else:
            return "|%s| %s" % (self.edge_caption_func(edge), r)

    def _format_incident_out(self, node, g):
        return [self._format_outgoing_edge(edge, g) 
                for edge in node.get_incident_out()]


DEFAULT = DigraphFormatter()
