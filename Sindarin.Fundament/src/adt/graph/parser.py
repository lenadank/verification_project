
from logic.smt.z3.output import LineParser # @@@
from adt.graph import Digraph
from pattern.collection import OneToOne



class GraphRepresentationFormat(object):
    
    ID = r"[a-z0-9_!'?]+"
    LBL = r"(\|" + ID + r"\|)?"
    COMMA_SEPD = ".*"

    RULES = [('incident-out', [(ID, 'source'), "->", (COMMA_SEPD, 'outgoing')]),
             ('knob', [(LBL, 'label'), (ID, 'destination')]),
             ]
    
    class LineByLine(object):
        def __init__(self, parser):
            self.nodes = OneToOne().of(Digraph.Node)
            self.parser = parser
            self.lines_processed = 0
        def __call__(self, line):
            symbol_name, elements = self.parser(line)
            if symbol_name == "incident-out":
                outgoing = elements['outgoing'].split(",")
                for o in outgoing:
                    symbol_name, oelements = self.parser(o)
                    if symbol_name == 'knob':
                        u = self.nodes[elements['source']]
                        v = self.nodes[oelements['destination']]
                        e = u.connect(v)
                        if oelements['label'] != '':
                            e.label = oelements['label'][1:-1]
                    else:
                        raise SyntaxError, "expected 'knob' here, but found '%s'" % (symbol_name,)
            else:
                raise SyntaxError, "unexpected '%s'" % (symbol_name,)
            
            self.lines_processed += 1
            
        @property
        def graph(self):
            g = Digraph()
            g.roots = self.nodes.values()
            return g
    
    def __init__(self):
        self.parser = LineParser(self.RULES, whitespace="\s*")
        
    def line_by_line(self):
        return self.LineByLine(self.parser)



class MixedGraphRepresentationsAndText(object):

    class LineByLine(object):
        def __init__(self, graph_format):
            self.graph_format = graph_format
            self.ll = None
            self.buffer = []
        def clean_cut(self):
            if self.ll is not None and self.ll.lines_processed > 0:
                g = self.ll.graph
                self.buffer.append(g)
                self.ll = None
        def __call__(self, line):
            if self.ll is None:
                self.ll = self.graph_format.line_by_line()
            try:
                self.ll(line)
            except SyntaxError:
                self.clean_cut()
                self.buffer.append(line)
    
    def __init__(self):
        self.grf = GraphRepresentationFormat()

    def __call__(self, lines):
        ll = self.LineByLine(self.grf)
        for line in lines:
            ll(line)
            for x in ll.buffer: yield x
            del ll.buffer[:]
        ll.clean_cut()
        for x in ll.buffer: yield x



from adt.graph.visual.dot import Dot
import sys


class MixedGraphsAndTextToHtml(object):
    
    def document(self, outfilename):
        tee = Tee(outfilename)
        return tee
    
    def __call__(self, mixed_elements, outfile=None):
        Dot.EXE = "/opt/local/bin/dot"
        
        from ui.gui.document_based.formats.graphics import ImageGallery
        
        gallery = ImageGallery()
        doc = outfile or sys.stdout
                
        print >>doc, '<html><head><meta http-equiv="Content-Type" content="text/html;charset=utf-8"/></head>'
        print >>doc, "<body>"
    
        for element in mixed_elements:
            if isinstance(element, str):
                element = element.decode("utf-8")
                lines = [element[i:i+80] for i in xrange(0, len(element), 80)] 
                print >>doc, "<pre>%s</pre>" % "\n".join(lines)
            else:
                dot = Dot(element)
                dot.format = "svg"
                p = dot.show(gallery.import_file)
                print >>doc, '<img src="%s"><br/>' % p
                
        print >>doc, "</body></html>"



if __name__ == '__main__':
    from filesystem import Tee

    input = ["This is my song:", #@ReservedAssignment
             "s -> |a| 1",
             "s -> 2",
             "2 -> s, 1",
             "-----------"] 
    
        
    mixed = MixedGraphRepresentationsAndText()(input)
    MixedGraphsAndTextToHtml()(mixed, outfile=Tee("parsed.html"))
    
    #showp(ll.graph)