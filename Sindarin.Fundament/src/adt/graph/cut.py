from adt import graph


class CutVisitor(graph.GraphScan.Visitor):

    def __init__(self, cut):
        self.cut = cut
        self.crossing = set()

    def visit_edge(self, edge):
        if (edge.source in self.cut) != (edge.destination in self.cut):
            self.crossing.add(edge)


class Cut(set):

    def get_crossing_edges(self, g):
        scan = graph.DFS(g)
        visitor = CutVisitor(self)
        scan.scan(visitor)
        return visitor.crossing
