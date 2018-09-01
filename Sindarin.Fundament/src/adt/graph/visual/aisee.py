
from adt.graph import GraphScan, DFS
import os



class AiSeeVisitor(GraphScan.Visitor):

    def __init__(self, outfile, attributes=None):
        self.outfile = outfile
        print >> self.outfile, "graph: {"
        print >> self.outfile, """colorentry 35: 22 182 14
            colorentry 42 : 174 218 255
            colorentry 43 :   0 145 198
            colorentry 44 : 198 139 205
            colorentry 45 : 198 145   0
            display_edge_labels: yes"""
        if attributes is not None:
            print >> self.outfile, attributes

    def done(self):
        print >> self.outfile, "}"

    def visit_node(self, node):
        if hasattr(node, 'graph'):
            self.visit_subgraph(node, node.graph)
        else:
            print >> self.outfile, """node: {title:"%s" label:"%s" %s %s}""" \
                      % (self.node_id(node), self.node_label(node), 
                         self.node_info(node), self.node_color(node))

    def visit_edge(self, edge):
        print >> self.outfile, """edge: {source:"%s" target:"%s" %s}""" \
              % (self.node_id(edge.source), self.node_id(edge.destination),
                 self.edge_label(edge))

    def visit_subgraph(self, super_node, subgraph):
        att = """title: "%s" status: boxed %s""" \
            % (self.node_id(super_node), self.node_color(super_node, 42))
        DFS(subgraph).scan(type(self)(self.outfile, att))
        
    def node_id(self, node):
        return ("n%i" % id(node)).replace("-", "0")

    def node_label(self, node):
        if node.label is None:
            return ""
        else:
            return node.label

    def node_info(self, node):
        formatted_attrs = [("%s=%r" % (key, value)).replace("\n","\\n")
                           for key, value in node.get_attributes().iteritems()]
        return 'info1: "%s"' % "\n".join(formatted_attrs)

    def node_color(self, node, default=None):
        if hasattr(node, "color"):
            return "color: %i" % node.color
        elif default is not None:
            return "color: %i" % default
        else:
            return ""

    def edge_label(self, edge):
        if hasattr(edge, 'label') and edge.label is not None:
            return 'label: "%s"' % (edge.label,)
        else:
            return ""


class AiSee(object):

    def __init__(self, graph, root=None, visitor_class=AiSeeVisitor):
        self.graph = graph
        if root is None:
            self.root = graph.roots
        else:
            self.root = root
        self.visitor = visitor_class

    def show(self, pic=None):
        dfs = DFS(self.graph, self.root)
        dot_file = file("/tmp/viz.gdl","w")
        dfs.scan(self.visitor(dot_file))
        dot_file.close()
        if os.uname()[0] == "Darwin":
            self.aisee_mac()
        else:
            self.aisee_linux()
        
    def aisee_mac(self):
        os.system("open /tmp/viz.gdl")

    def aisee_linux(self):
        import commands, signal
        EXE = "/opt/aiSee/bin/aisee"
        pid_s = commands.getoutput("pidof " + EXE + ".bin")
        instances = [int(pid) for pid in pid_s.split()
                     if "\x00/tmp/viz.gdl\x00" in open("/proc/%s/cmdline"%pid).read()]
        if instances:
            os.kill(instances[0], signal.SIGUSR1)
        else:
            os.system(EXE + " /tmp/viz.gdl &")
                      

