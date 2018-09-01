
from adt import graph
from pattern.collection import BuildupSets



class Path(list):
    """A path in the graph is basically a list of edges."""

    @property
    def source(self):
        if not self: raise ValueError, "empty path with unknown source"
        return self[0].source
    
    @property
    def destination(self):
        if not self: raise ValueError, "empty path with unknown destination"
        return self[-1].destination

    def node_at(self, index):
        """
        Returns the i'th node on the path.
        @param index: node index (i)
        @return: graph node
        """
        if index == 0:
            return self[0].source
        else:
            return self[index-1].destination

    def goes_through(self, node):
        """
        @param node: graph node
        @return: True if the paths goes through the given node
        """
        for edge in self:
            if node is edge.source or node is edge.destination:
                return True
        else:
            return False
        
    def __add__(self, other):
        return Path(super(Path, self).__add__(other))
    
    def __hash__(self):
        return hash(tuple(self))
    
    def __repr__(self):
        return graph.format.DEFAULT.format_path(self, g=None)
    
    
class EmptyPath(Path):
    
    def __init__(self, source):
        super(EmptyPath, self).__init__()
        self._source = source
        
    @property
    def source(self):
        return self._source
        
    @property
    def destination(self):
        return self.source
        
    def __repr__(self):
        return graph.format.DEFAULT.format_node(self.source)
    
    def __add__(self, other):
        if len(other) == 0:
            return self
        else:
            return super(EmptyPath, self).__add__(other)
    
    def __hash__(self):
        return hash(self.source)
    
    def __eq__(self, other):
        if isinstance(other, EmptyPath):
            return self.source is other.source
        else:
            return False
        
    def __ne__(self, other):
        return not (self == other)


class NaivePathFinder(object):

    class Visitor(graph.GraphScan.Visitor):

        def __init__(self, source):
            self.path_to = {source: Path([])}
            
        def visit_edge(self, edge):
            u, v = edge.source, edge.destination            
            if u in self.path_to and v not in self.path_to:
                self.path_to[v] = self.path_to[u] + [edge]
                

    def __init__(self, g, scan=None):
        """
        @param g the graph
        @param scan a GraphScan object; the scanning method may
          yield different path-finding algorithms. The default is DFS(g).
        """
        if scan is None: scan = graph.DFS(g)
        self.graph = g
        self.scan = scan

    def from_to(self, u, v):
        visitor = self.Visitor(u)
        while v not in visitor.path_to:
            self.scan.scan(visitor)
        return visitor.path_to[v]



class AllPaths(object):
    
    class PathBuilderVisitor(graph.GraphScan.Visitor):
        
        def __init__(self, origin_set, can_extend=lambda path: True):
            self.all_paths = BuildupSets()
            for s in origin_set:
                self.all_paths[s].add(EmptyPath(s))
            self.can_extend = can_extend
        
        def visit_edge(self, edge):
            u, v = edge.source, edge.destination

            paths_to = self.all_paths[u]

            self.all_paths[v].update( \
                [path + [edge] for path in paths_to if self.can_extend(path)])
            # note: iterator expression cannot be used since all_paths[v] and
            #  all_paths[u] may be the same if u==v, leading to iterator contract
            #  violation
                
        def done(self):
            return self.all_paths
            
    def __init__(self, g):
        self.graph = g
        self.length_limit = None
    
    def with_length_limit(self, limit):
        self.length_limit = limit
        return self
    
    def __call__(self):
        if self.length_limit is None:
            can_extend = self.is_acyclic
        else:
            can_extend = lambda path: len(path) < self.length_limit
        v = self.PathBuilderVisitor(self.graph.roots, can_extend=can_extend)
        r = graph.DFS(self.graph).scan(v)
        while r.dirty:
            r.accept()
            r = graph.DFS(self.graph).scan(v)
        return r

    def is_acyclic(self, path):
        if len(path) == 0: return True
        visited = set([path[0].source])
        for edge in path:
            if edge.destination in visited:
                return False
            visited.add(edge.destination)
        return True
            



class Emerge(object):
    """
    Used to compute directed paths from a given node outwards.
    """

    def __init__(self, g, container=set):
        self.g = g
        self.container = container
    
    def single_step_with_edges(self, nodes, tag):
        edges = [e for node in nodes 
                 for e in node.get_incident_out() if e.label == tag]
        return self.container(e.destination for e in edges), \
               set(edges)
    
    def single_step(self, nodes, tag):
        return self.container([e.destination for node in nodes
                               for e in node.get_incident_out()
                               if e.label == tag])
    

class ResidualNetwork(graph.Digraph):
    pass



if __name__ == "__main__":
    from adt.graph.build import FlowGraphTool
    from adt.graph.format import DEFAULT as formatter
    
    inputs = [([1,2,3,4,5], lambda a,b,c,d,e: a >> (b | c) >> d >> e),
              ([1,2,3,4], lambda a,b,c,d: a >> a >> b >> c >> d >> a),
              ([1,2,3,4], lambda a,b,c,d: a >> b >> c >> d >> a),
              ]
    
    for input in inputs: #@ReservedAssignment
        g = FlowGraphTool(input)()
        print formatter(g)
        
        paths = AllPaths(g).with_length_limit(6)()
        for k, v in paths.iteritems():
            print "  ", k.label, "    ", list(v)
            
        print "-" * 50