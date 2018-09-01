'''
GraphViz interop module

requires pygraphviz
'''

import os.path
import warnings
import pygraphviz as pgv
from pygraphviz.graphviz import agget, agset
from pattern.mixins.attributes import WithMixIn



class GraphvizGraphLayout(WithMixIn):
    
    class Template: pass
    
    def __init__(self):
        v = self.Template()
        v.node_attr = {'fixedsize': 'true',
                       'fontname': 'STIXGeneral'}
        v.edge_attr = {'fontname': 'STIXGeneral'}
        v.graph_attr = {'sep': "2", 'directed': True}
        self.template = v
        self.styles = {None: {'width': "0.2",
                              'height': "0.2"},
                       'mark': {'width': "0.2",
                                'height': "0.2",
                                'style': 'filled'},
                       'box': {'shape': 'box',
                               'width': "0.125",
                               'height': "0.125",
                               'fontcolor': 'white',
                               'style': 'filled', 'fillcolor': 'black'}}
        self.node_styler = lambda n, vn: None
        self.label_attr = 'label'
        self.algorithm = "neato"
        self.scale_factor = 2.0
        
        self.output_filename = "/tmp/v.pdf"
        self.auto_open = False
        
    def with_styler(self, node_styler):
        self.node_styler = node_styler
        return self

    @property
    def output_format(self):
        _, ext = os.path.splitext(self.output_filename)
        if ext.startswith('.'): ext = ext[1:]
        return ext
    
    @output_format.setter
    def output_format(self, fmt):
        t, _ = os.path.splitext(self.output_filename)
        ext = fmt if fmt.startswith('.') else '.' + fmt
        self.output_filename = t + ext

    def __call__(self, g):
        v = pgv.AGraph(directed=True)
        v.graph_attr.update(self.template.graph_attr)
        v.node_attr.update(self.template.node_attr)
        v.edge_attr.update(self.template.edge_attr)
        for n in g.nodes:
            v.add_node(n.label)
            vn = v.get_node(n.label)
            self.apply_styler(n, vn)
                
        for e in g.edges:
            s, t = e.source.label, e.destination.label
            v.add_edge(s, t)
            if e.label is not None:
                v.get_edge(s, t).attr[self.label_attr] = str(e.label)
    
        # Invoke pygraphviz's external layout program
        os.environ["PATH"] = "/opt/local/bin:" + os.environ["PATH"]  # @@@

        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)            
            v.layout(self.algorithm)
            self.post_transform_scale(v, self.scale_factor)
            v.draw(self.output_filename)

        if self.auto_open:
            os.system("open " + self.output_filename)
            
        return self.output_filename
        
    def apply_style(self, vn, style=None):
        vn.attr.update(self.styles[style])
        
    def apply_styler(self, n, vn):
        self.apply_style(vn, self.node_styler(n, vn))

    def post_transform_scale(self, v, factor):
        # Adjust node positions
        def xform(s, sep, func):
            vals = [func(r) for r in s.split(sep)]
            return sep.join(str(r) for r in vals)
        def scale(s):
            if s.startswith("e,"):
                prefix, s = "e,", s[2:]  #@UnusedVariable
                # seems like 'prefix' is not even needed, but I may be wrong
            return xform(s, ' ',
                         lambda s: xform(s, ',', lambda r: float(r)*factor))
        
        for vn in v.nodes():
            vn.attr["pos"] = scale(vn.attr["pos"])
            vn.attr['width'] = scale(vn.attr["width"])
            vn.attr['height'] = scale(vn.attr["height"])
        for ve in v.edges():
            ve.attr["pos"] = scale(ve.attr["pos"])
            if ve.attr["lp"]:
                ve.attr["lp"] = scale(ve.attr["lp"])
            if ve.attr["head_lp"]:
                ve.attr["head_lp"] = scale(ve.attr["head_lp"])
        
        bb = agget(v.handle, 'bb')
        agset(v.handle, 'bb', scale(bb))


