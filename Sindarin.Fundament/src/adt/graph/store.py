from adt import graph


class Store(object):

    class StoreVisitor(graph.GraphScan.Visitor):

        def __init__(self):
            self.nodes = []
            self.edges = []

        def visit_node(self, node):
            self.nodes.append( (id(node), node.get_attributes()) )

        def visit_edge(self, edge):
            self.edges.append( (id(edge.source), id(edge.destination),
                                edge.get_attributes()) )

        def done(self):
            return self.nodes, self.edges


    @classmethod
    def dump(cls, g):
        roots = [id(node) for node in g.roots]
        return (roots,) + graph.DFS(g).scan(cls.StoreVisitor())

    @classmethod
    def load(cls, t):
        roots, nodes, edges = t
        nodemap = { }
        for node_id, node_attributes in nodes:
            nodemap[node_id] = node = graph.Digraph.Node()
            node.__dict__.update(node_attributes)
        for edge_from, edge_to, edge_attributes in edges:
            edge = nodemap[edge_from].connect(nodemap[edge_to])
            edge.__dict__.update(edge_attributes)
        g = graph.Digraph()
        g.roots = [nodemap[i] for i in roots]
        g.n_nodes = len(nodes)
        g.n_edges = len(edges)
        return g

    @classmethod
    def copy(cls, g):
        return cls.load(cls.dump(g))
