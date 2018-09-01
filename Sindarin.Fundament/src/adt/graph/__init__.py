from pattern.collection.basics import OrderedSet



#--------------------------------------------------------
###                 UNDIRECTED GRAPHS
#--------------------------------------------------------

class AbstractGraph(object):
    class Node(object):
        def get_incident(self): return []
    class Edge(object):
        pass
    
    
class UndirectedGraph(AbstractGraph):
    
    class Node(AbstractGraph.Node):
        def __init__(self, label=None):
            self.label = label
            self.incident = []
        def get_incident(self):
            return self.incident
        def __repr__(self):
            return "node: %s" % self.label
        
    class Edge(AbstractGraph.Edge):
        def __init__(self, ends, label=None):
            self.label = label
            self.ends = set(ends)
            if len(self.ends) not in [1, 2]:
                raise ValueError, "arc must have either 1 or 2 ends"
        def other_end(self, node):
            for n in self.ends:
                if n is not node:
                    return n
            else:
                # loop
                return node
        def __repr__(self):
            # @todo loop case
            ep1, ep2 = self.ends
            if self.label is None:
                return "arc: %s -- %s" % (ep1.label, ep2.label)
            else:
                return "arc: %s --|%s|-- %s" % (ep1.label, self.label, ep2.label)
        
            
    @classmethod
    def from_directed(cls, g):
        nodes = \
            {n: cls.Node(n.label) for n in g.nodes}
        roots = [nodes[r] for r in g.roots]
        for dinode in nodes.iterkeys():
            for edge in dinode.get_incident_out():
                e = cls.Edge([nodes[edge.source], 
                              nodes[edge.destination]], edge.label)
                for n in e.ends:
                    n.incident += [e]

        g = cls()
        g.roots = roots
        return g

    @property
    def nodes(self):
        return set(ep for e in self.edges
                   for ep in e.ends)

    @property
    def edges(self):
        return [e for e in BFS().scan(self)]




#--------------------------------------------------------
###                 DIRECTED GRAPHS
#--------------------------------------------------------

class AbstractDigraph(object):

    class Node(object):
        def get_incident_out(self):        pass

    class Edge(object):
        """attribute source
        attribute destination"""
        pass
    

class Digraph(AbstractDigraph):

    class Node(AbstractDigraph.Node):
        def __init__(self, label=None):
            self.incident_out = []
            self.label = label
        def __repr__(self):
            return "node: %s" % self.label
        def get_incident_out(self):
            return self.incident_out
        def get_adjacent_out(self):
            return [e.destination for e in self.incident_out]
        def get_edges_to(self, other):
            return [e for e in self.incident_out if e.destination is other]
        def get_attributes(self):
            d = self.__dict__.copy()
            del d['incident_out']
            return d
        def connect(self, other_node):
            e = Digraph.Edge(self, other_node)
            self.incident_out.append(e)
            return e
    
    class Edge(AbstractDigraph.Edge):
        def __init__(self, source, destination):
            self.source = source
            self.destination = destination
            self.label = None
        def get_incident(self):
            return (self.source, self.destination)
        def get_attributes(self):
            d = self.__dict__.copy()
            del d['source'], d['destination']
            return d
        def __repr__(self):
            if self.label is None:
                return "edge: %s -> %s" % (self.source.label, self.destination.label)
            else:
                return "edge: %s -|%s|-> %s" % (self.source.label, self.label, self.destination.label)
        @property
        def ends(self):
            return OrderedSet([self.source, self.destination])
        def other_end(self, u):
            if u is self.source:
                return self.destination
            elif u is self.destination:
                return self.source
            else:
                raise ValueError, "'%s' is neither end of '%s'" % (u, self)
        
    @property
    def nodes(self):
        return DFS(self).scan(CollectNodesVisitor())
    
    @property
    def edges(self):
        return DFS(self).scan(CollectEdgesVisitor())
    
    def __getstate__(self):
        from adt.graph.store import Store
        return Store.dump(self)
    
    def __setstate__(self, state):
        from adt.graph.store import Store
        g = Store.load(state)
        self.roots = g.roots
    
    
class GraphScan(object):

    class Visitor(object):
        def visit_edge(self, edge): pass
        def visit_node(self, node): pass
        def done(self): pass
        

class DFS(GraphScan):

    def __init__(self, graph, root=None):
        self.graph = graph        
        if root is None:
            self.roots = graph.roots
        elif isinstance(root, list) or isinstance(root, set):
            self.roots = root
        else:
            self.roots = [root]

    def _scan(self, start, scanned, visitor):
        if start not in scanned:
            visitor.visit_node(start)
            scanned.add(start)
            for edge in start.get_incident_out():
                visitor.visit_edge(edge)
                node = edge.destination
                self._scan(node, scanned, visitor)

    def scan(self, visitor):
        scanned = set()
        for root in self.roots:
            self._scan(root, scanned, visitor)
        return visitor.done()


class BFS(object):
    """
    @todo make it comply to interface of GraphScan
    """
    
    def __init__(self):
        self.travel_from = lambda u: u.get_incident_out()
        self.move_on = lambda u, e: e.other_end(u)
    
    def scan(self, g, rootset=None):
        if rootset is None: rootset = g.roots
        q = list(rootset)
        visited = set()
        while q:
            u = q[0]
            del q[0]
            for e in self.travel_from(u):
                if e not in visited:
                    yield e
                    visited.add(e)
                    q.append(self.move_on(u, e))


class PredeterminedScan(GraphScan):

    def __init__(self, order):
        self.order = order

    def scan(self, visitor):
        for node in self.order:
            visitor.visit_node(node)
        return visitor.done()


class CollectVisitor(GraphScan.Visitor):

    container = set

    def __init__(self, container=None):
        if container is None:
            self.collection = self.container()
        else:
            self.collection = container

    def done(self):
        return self.collection


class CollectNodesVisitor(CollectVisitor):

    def visit_node(self, node):
        self.collection.add(node)


class CollectEdgesVisitor(CollectVisitor):

    def visit_edge(self, edge):
        self.collection.add(edge)


class CollectNodesAndEdgesVisitor(CollectNodesVisitor, CollectEdgesVisitor):
    pass


class PredicateDecoratorVisitor(GraphScan.Visitor):

    def __init__(self, subordinate_visitor, predicate):
        self.predicate = predicate
        self.subordinate_visitor = subordinate_visitor

    def visit_node(self, node):
        if self.predicate(node):
            self.subordinate_visitor.visit_node(node)

    def visit_edge(self, edge):
        if self.predicate(edge):
            self.subordinate_visitor.visit_edge(edge)

    def done(self):
        return self.subordinate_visitor.done()


class NodePredicateDecoratorVisitor(GraphScan.Visitor):

    def __init__(self, subordinate_visitor, node_predicate):
        self.node_predicate = node_predicate
        self.subordinate_visitor = subordinate_visitor

    def visit_node(self, node):
        if self.node_predicate(node):
            self.subordinate_visitor.visit_node(node)

    def done(self):
        return self.subordinate_visitor.done()
        

# Serialization Patch
for name, cls in [("AbstractDigraph.Node", AbstractDigraph.Node),
                  ("AbstractDigraph.Edge", AbstractDigraph.Edge),
                  ("Digraph.Node", Digraph.Node),
                  ("Digraph.Edge", Digraph.Edge)]:
    globals()[name] = cls; cls.__name__ = name
