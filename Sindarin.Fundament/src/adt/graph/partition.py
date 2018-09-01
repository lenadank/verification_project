from adt import graph
import pattern.collection


class Partition(object):
    """
    Partitioning of a graph.
    Supports adding components:
        c = p.Component()
        p.components.add(c)
    Supports modifying components:  * this currently violates variant
        c.add(node)
    Supports finding a component containing a node:
        p.find_component(node)
    Supports merging two existing components into one:
        p.merge_components(c1, c2)
    Supports refining using a separator set:
        p.refine(s)
    """

    class Component(set):
        def __hash__(self): return id(self)
        def __eq__(self, other): return self is other

    class ComponentSet(set):
        pass

    def __init__(self, g):
        self.graph = g
        self.components = self.ComponentSet()
        self._node2component = { }

    def add_component(self, component):
        for node in component:
            self._node2component[node] = component
        self.components.add(component)

    def find_component(self, node):
        try:
            return self._node2component[node]
        except KeyError:
            return None
        for component in self.components:
            if node in component:
                return component
        return None

    def merge_components(self, component_a, component_b):
        assert component_a in self.components
        if component_a is not component_b:
            self.components.remove(component_b)
            component_a.update(component_b)
            for node in component_b:
                self._node2component[node] = component_a

    def refine(self, separator):
        """
        Splits existing components so that items in S and items not in S
        reside in disjoint components.
        """
        old_components = self.components
        self.components = self.ComponentSet()
        changed = False
        for component in old_components:
            inside = component & separator
            outside = component - separator
            if inside and outside:
                for part in (inside, outside):
                    self.add_component(part)
                    changed = True
            else:
                self.components.add(component) # skip updating _node2component
            separator = separator - component
        if separator:
            self.add_component(separator)
            changed = True
        return changed
            
    def __rmod__(self, formatter):
        return "| %s |" % \
            " | ".join(formatter % component for component in self.components)


class ByNodeColorPartitioning(object):
    """
    Partitions the graph according to a given node coloring, which is a
    function assigning a color for each node. The colors may be any hashable,
    comparable objects. Resulting components are monochrome and differ in
    color pairwise.
    """

    class Visitor(graph.GraphScan.Visitor):
        def __init__(self, coloring):
            self.coloring = coloring
            self.colormap = pattern.collection.OneToMany().of(Partition.Component)
        def visit_node(self, node):
            color = self.coloring(node)
            self.colormap[color].add(node)
        def done(self):
            return self.colormap

    def __init__(self, g, coloring=lambda node: None):
        self.g = g
        self.coloring = coloring

    def __call__(self):
        colormap = graph.DFS(self.g).scan(self.Visitor(self.coloring))
        partition = Partition(self.g)
        for component in colormap.values():
            partition.add_component(component)
        return partition


class ByEdgePartitioning(object):
    """
    Partitions the graph into components comprising of connected nodes.
    Connectivity can be defined by all of the graph's edges or a subset of
    them given in the form of an edge predicate.
    """

    class Visitor(graph.GraphScan.Visitor):
        def __init__(self, g, connect_criterion):
            self.partition = Partition(g)
            self.connect_criterion = connect_criterion
        def visit_node(self, node):
            self.component_of(node)
        def component_of(self, node):
            c = self.partition.find_component(node)
            if c is None:
                c = self.partition.Component([node])
                self.partition.add_component(c)
            return c
        def visit_edge(self, edge):
            if self.connect_criterion(edge):
                self.partition.merge_components(
                    self.component_of(edge.source),
                    self.component_of(edge.destination))
        def done(self):
            return self.partition

    def __init__(self, g, connecting_edge_criterion=lambda edge: True):
        self.graph = g
        self.connect_criterion = connecting_edge_criterion

    def __call__(self):
        visitor = self.Visitor(self.graph, self.connect_criterion)
        return graph.DFS(self.graph).scan(visitor)
        

class ExplicitCollapsePartitioning(object):

    def __init__(self, g, collapsing=set()):
        self.graph = g
        self.collapsing = collapsing

    def __call__(self):
        nodes = graph.DFS(self.graph).scan(graph.CollectNodesVisitor())
        partition = Partition(self.graph)
        for component in self.collapsing:
            partition.add_component(Partition.Component(component))
            nodes.difference_update(component)
        for node in nodes:
            partition.add_component(Partition.Component([node]))
        return partition
    

class Structure(graph.AbstractDigraph):

    class ComponentNode(graph.AbstractDigraph.Node):
        def __init__(self, owner, component):
            self.owner = owner
            self.component = component
            if len(component) == 1:
                for n in component:
                    self.__dict__.update(n.get_attributes())
            self.label = "".join(str(x.label) for x in component)
        def get_attributes(self):
            d = self.__dict__.copy()
            del d['owner'], d['component']
            return d
        def get_incident_out(self):
            return list(self._out_edge_gen())
        def _out_edge_gen(self):
            for node in self.component:
                for out in node.get_incident_out():
                    other = self.owner.node_containing(out.destination)
                    if other is not self or self.owner.yield_self_loops:
                        e = graph.Digraph.Edge(self, other)
                        e.__dict__.update(out.get_attributes())
                        yield e
        def __repr__(self):
            if len(self.component) == 1:
                return repr(list(self.component)[0])
            else:
                return "nodes: %s" % self.label

    def __init__(self, g, partition, join=lambda supernode, nodeset: None):
        self.graph = graph
        self.partition = partition
        self.join = join
        self.known_nodes = {}
        self.roots = set(self.node_containing(x) for x in g.roots)
        self.yield_self_loops = False

    def node_of(self, component):
        try:
            return self.known_nodes[component]
        except KeyError:
            self.known_nodes[component] = n = self.ComponentNode(self, component)
            self.join(n, component)
            return n

    def node_containing(self, node):
        """
        @param node a node in the original graph
        """
        component = self.partition.find_component(node)
        if component is None:
            raise KeyError, "partition does not cover %r" % node
        else:
            return self.node_of(component)
        
    def remap(self, mapping):
        return dict((node, value) 
                    for key, value in mapping.iteritems()
                        for node in key.component)

    def remapped(self, g):
        g.shadow_nodes = self.remap(g.shadow_nodes)
        g.shadow_edges = None
        return g


class QuickPartition(object):
    """
    Uses InstantGraphTool and ByEdgePartitioning to partition a set of values
    into groups according to a binary predicate.
    If p(a,b) holds, 'a' and 'b' are guaranteed to reside in the same group.
    """

    def __init__(self, values, predicate, aggregator=set):
        self.values = values
        self.predicate = predicate
        self.aggregator = aggregator

    def __call__(self):
        from adt.graph.build import InstantGraphTool
        g = InstantGraphTool(self.values, self.predicate)()
        p = ByEdgePartitioning(g)()
        return [self.aggregator(node.label for node in component) \
                for component in p.components]
