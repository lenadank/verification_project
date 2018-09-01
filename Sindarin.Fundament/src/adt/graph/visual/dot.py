from adt.graph import GraphScan, DFS
import os
import re


#############
# Graphviz stuff
#

class GraphvizVisitor(GraphScan.Visitor):

    def __init__(self, outfile, title=None):
        self.outfile = outfile
        print >> self.outfile, "digraph G {"
        if title is not None:
            print >> self.outfile, "graph", self._lbl(title)

    def done(self):
        print >> self.outfile, "}"
        self.outfile.close()

    def visit_node(self, node):
        print >> self.outfile, self.node_id(node), \
              self.node_label(node), ";"

    def visit_edge(self, edge):
        print >> self.outfile, self.edge_id(edge), \
              self.edge_label(edge), ";"

    def node_id(self, node):
        return ("n%i" % id(node)).replace("-", "0")
    
    def edge_id(self, edge):
        return "%s -> %s" % (self.node_id(edge.source),
                             self.node_id(edge.destination))

    def node_label(self, node):
        return self._lbl(node.label)

    def edge_label(self, edge):
        return self._lbl(edge.label)
        
    def _lbl(self, value):
        if value is None:
            return ""
        else:
            return '[label="%s"]' % value


class Dot(object):

    EXE = "dot"
    DEFAULT_FORMAT = "gif"

    def __init__(self, graph, root=None, visitor_class=GraphvizVisitor):
        self.graph = graph
        if root is None:
            self.root = graph.roots
        else:
            self.root = root
        self.visitor = visitor_class
        self.format = self.DEFAULT_FORMAT

    def show(self, pic=None, title=None):
        dfs = DFS(self.graph, self.root)
        dot_file = file("/tmp/gviz.dot","w")
        dfs.scan(self.visitor(dot_file, title=title))
        dot_file.close()
        outfilename = "/tmp/gviz.%s" % self.format
        os.system(self.EXE + " -T%s -o %s /tmp/gviz.dot" % (self.format,
                                                            outfilename))
        if pic is not None:
            return pic(outfilename)


class DotOutputParser(object):

    STRING_LITERAL = '"[^"]*"'
    IDENTIFIER = '[a-zA-Z_][a-zA-Z0-9_]*'
    KEY_VALUE = "(?P<key>" + IDENTIFIER + ")" + "=" + \
                "(?P<value>" + STRING_LITERAL + ")"
    ATTRIBUTES = r"\[" + "(?P<attributes>" + \
                 "(?P<attribute>" + KEY_VALUE + r",?\s*" + \
                 ")*)" + r"\]"
    POSITION = r'"?(?P<x>\d+),(?P<y>\d+)"?'
    NODE_STATEMENT = r"\s*" + "(?P<name>" + IDENTIFIER + ")" + r"\s*" + \
                     ATTRIBUTES + r"\s*;\s*";
    ARC_STATEMENT  = r"\s*" + "(?P<from>" + IDENTIFIER + ")" + r"\s*" + \
                     "->" + \
                     r"\s*" + "(?P<to>" + IDENTIFIER + ")" + r"\s*" + \
                     ATTRIBUTES + r"\s*;\s*";


    class Statement(object):
        pass

    class Layout(object):
        pass


    def parse_attributes(self, stmt):
        attributes = { }
        mo = re.search("^" + self.KEY_VALUE + r",?\s*", stmt)
        while mo:
            attributes[mo.group("key")] = mo.group("value")
            stmt = stmt[len(mo.group(0)):]
            mo = re.search("^" + self.KEY_VALUE + r",?\s*", stmt)
        return attributes
            
    def parse_statement(self, stmt):
        mo = re.match(self.NODE_STATEMENT, stmt.strip())
        if mo:
            s = self.Statement()
            s.name = mo.group("name")
            s.attributes = self.parse_attributes(mo.group("attributes"))
            return s
        mo = re.match(self.ARC_STATEMENT, stmt.strip())
        if mo:
            s = self.Statement()
            s.source = mo.group("from")
            s.destination = mo.group("to")
            s.attributes = self.parse_attributes(mo.group("attributes"))
            return s

    def parse_position(self, pos):
        mo = re.match(self.POSITION, pos)
        if mo is not None:
            return int(mo.group("x")), int(mo.group("y"))
        else:
            raise SyntaxError, "invalid position " + pos

    def parse_polygon(self, poly):
        return [self.parse_position(vert) \
                for vert in poly.replace('e,', "").split()]            

    def parse_file(self, dotfile):
        l = self.Layout()
        l.nodes = []
        for line in dotfile:
            stmt = self.parse_statement(line)
            if stmt is not None:
                print stmt.attributes
                l.nodes.append(stmt)
        return l

    def lay_out(self, dotfile):
        import layoutwin #@UnresolvedImport
        l = self.parse_file(dotfile)
        w = layoutwin.LayoutWindow()
        for node in l.nodes:
            if "pos" in node.attributes and hasattr(node, 'name'):
                x, y = self.parse_position(node.attributes["pos"])
                shape = layoutwin.Layout.Rectangle(x-25, y-25, 50, 50)
                w.shapes.append(shape)
                att = w.attachments["top-left"]
                topleft = layoutwin.Layout.ConnectionPoint(shape, att)
                w.shapes.append(topleft)
                text = eval(node.attributes["label"])
                label = layoutwin.Layout.Label(topleft, text, att)
                w.shapes.append(label)
            elif "pos" in node.attributes and hasattr(node, 'source'):
                vertices = self.parse_polygon(node.attributes["pos"])
                shape = layoutwin.Layout.FreeFormConnector(vertices)
                w.shapes.append(shape)
        return w



class PictureWindowSingleton:

    instance = None

    @classmethod
    def show(cls, g):
        if cls.instance is None:
            import gtk #@UnresolvedImport
            import ui.gui.showpic
            cls.instance = ui.gui.showpic.PictureWindow()
            cls.instance.window.connect("destroy", gtk.main_quit)

        dot = Dot(g)
        dot.show(cls.instance.image.add_image)
        cls.instance.window.show()
        
    @classmethod
    def show_in_process(cls, g):
        from ui.gui.toolkits.gtk import GtkProcess
        
        class LazyPictureWindow(object):
            def __new__(self):
                from ui.gui.showpic import PictureWindow
                return PictureWindow()
        
        p = GtkProcess(LazyPictureWindow)
        def on_load(w):
            graphs = [[g], g][isinstance(g, list)]
            for s in graphs:
                Dot(s).show(w.image.add_image, 
                            title=getattr(s, 'title', None))
        p.on_load = on_load
        p.spawn()



def t():
    w = DotOutputParser().lay_out(open("gviz.dot"))
    import layoutwin #@UnresolvedImport
    layoutwin.lw = w
    import gtk #@UnresolvedImport
    gtk.main()


show = PictureWindowSingleton.show
showp = PictureWindowSingleton.show_in_process
