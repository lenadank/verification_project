# encoding=utf8

import cPickle
from adt.graph import Digraph
from adt.graph.format import DigraphFormatter



class FileDocument(object):
    
    def __init__(self, filename):
        self.filename = filename
        
    def file(self, mode="r"): #@ReservedAssignment
        return file(self.filename, mode)


class InteractiveGraphEditor(object):
    
    class ph(str):
        def __repr__(self):
            return self
    
    def __init__(self, document=FileDocument("default.pickle")):
        self.formatter = DigraphFormatter()
        self.document = document
        self.parser = InteractiveGraphCommandParser()
        self.load()
        
    def __call__(self, input): #@ReservedAssignment
        for command in input:
            self.run_cmd(command)

    def load(self):
        self.data = cPickle.load(self.document.file("r"))
        self.graphs = []
        i = 0
        for datum in self.data:
            if isinstance(datum, Digraph):
                datum.title = i
                i += 1
                self.graphs.append(datum)
            elif isinstance(datum, tuple):
                for j in datum:
                    if isinstance(j, Digraph):
                        PH = self.ph("_")
                        j.title = "%d: %r" % (i, tuple([x,PH][x is j] for x in datum))
                        i += 1
                        self.graphs.append(j)
    
    def save(self):
        cPickle.dump(self.data, self.document.file("w"))
    
    def text_out(self, graphs=None):
        if graphs is None: graphs = self.graphs
        for g in graphs:
            print "[%s]" % g.title
            print self.formatter(g)
            print '-' * 30
            
    def dot_out(self, graphs=None):
        if graphs is None: graphs = self.graphs
        from adt.graph.visual.dot import Dot, showp
        Dot.EXE = "/opt/local/bin/dot"
        showp(graphs)
        
    def run_cmd(self, command):
        meaning = self.parser.parse(command)
        if meaning[0] == "error":
            print "Error in command '%s': %r" % (command, meaning[1:])
        else:
            return getattr(self, meaning[0])(*meaning[1:])

    def select(self, indices):
        if isinstance(indices, int):
            indices = [indices]
        self.selected = [self.graphs[i] for i in indices]
        self.text_out(self.selected)

    def select_all(self):
        self.selected = self.graphs
        
    def write(self):
        self.text_out(self.selected)
    
    def draw(self):
        self.dot_out(self.selected)
        
    def toc(self):
        for s in self.selected:
            print "%s     (%d nodes)" % (s.title, len(s.nodes))
            
    def connect(self, u_label, v_label, edge_label=None):
        for g in self.selected:
            nodes = g.nodes
            u_nodes = self._nodes(nodes, u_label)
            v_nodes = self._nodes(nodes, v_label)
            print "[%s] %r --> %r" % (g.title, u_nodes, v_nodes)
            for u in u_nodes:
                for v in v_nodes:
                    u.connect(v).label = edge_label
    
    def disconnect(self, u_label, v_label, edge_label=None):
        it_is = lambda e, v: e.destination is v and \
                (e.label == edge_label or edge_label is None)
        for g in self.selected:
            nodes = g.nodes
            u_nodes = self._nodes(nodes, u_label)
            v_nodes = self._nodes(nodes, v_label)
            print "[%s] %r -/-> %r" % (g.title, u_nodes, v_nodes)
            for u in u_nodes:
                for v in v_nodes:
                    u.incident_out = [e for e in u.get_incident_out()
                                      if not it_is(e, v)]
            
    def _nodes(self, nodes, node_label):
        return [x for x in nodes if str(x.label) == node_label]


class CommandParser(object):

    SYN = []
    
    class Syntax(object):
        
        def __init__(self, list_of_specs):
            self.compiled = []
            self += list_of_specs
            
        def __iadd__(self, list_of_specs):
            self.compiled += self._compile(list_of_specs)
            return self
            
        @classmethod
        def _compile(cls, list_of_specs):
            import re
            return [(re.compile(pattern+"$"), action) 
                    for pattern, action in list_of_specs]

    def __init__(self):
        self.syn = self.Syntax(self.SYN)

    def parse(self, command):
        for pattern, action in self.syn.compiled:
            mo = pattern.match(command)
            if mo:
                meaning = action(*mo.groups())
                break
        else:
            print "error in command:", command
            meaning = ("error",)
        return meaning

    
class InteractiveGraphCommandParser(CommandParser):
    
    SYN = [(r"(\d+)", lambda a: ("select", int(a))),
           (r"(\d+):(\d+)", lambda a,b: ("select",
                                         xrange(int(a), int(b)))),
           (r":", lambda: ("select_all",)),
           (r"", lambda: ("write",)),
           (r"/", lambda: ("draw",)),
           (r"\?", lambda: ("toc",)),
           (r"([^/-]+)--?([^/-]+)", lambda u, v: ("connect", u, v)),
           (r"([^/-]+)-([^/-]+)-([^/-]+)", lambda u, l, v: ("connect", u, v, l)),
           (r"([^/-]+)-/-?([^/-]+)", lambda u, v: ("disconnect", u, v)),
           (r"([^/-]+)-/([^/]+)-([^/-]+)", lambda u, l, v: ("disconnect", u, v, l)),
           (r"([^/-]+)-([^/]+)/-([^/-]+)", lambda u, l, v: ("disconnect", u, v, l)),
           (r"save", lambda: ("save",)),
            ]
    
    def interactive_commands(self):
        import readline #@UnusedImport
        while True:
            try:
                yield raw_input("> ")
            except EOFError:
                break
            

def sequentially(*iterables):
    for iterable in iterables:
        for item in iterable:
            yield item
            

if __name__ == "__main__":
    filename = "../../../../Mandarin.ShapeAnalysis/testdrive/treepp.pickle"
    e = InteractiveGraphEditor(FileDocument(filename))
    def stats():
        print "Total:"
        print sum([len(g.nodes) for g in e.selected])
    e.stats = stats
    e.parser.syn += [(r"%", lambda: ("stats",))]
    #input = [":", "?", "12", "s-/r-1", "2-/r-s", "2-r-1", "/", "save"]
    #input = ["12", "/"]
    input = ["13", "/"] #@ReservedAssignment
    input = sequentially(input, #@ReservedAssignment
                         e.parser.interactive_commands())
    e(input)
