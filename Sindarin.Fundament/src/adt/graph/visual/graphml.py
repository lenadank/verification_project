
from xml.etree import ElementTree as ET
from adt.graph.build import EdgeSetGraphTool



class GraphMLGraphLayout(object):
    
    XMLNS = "http://graphml.graphdrawing.org/xmlns"
    
    def __call__(self, g):
        root = ET.Element('graphml', xmlns=self.XMLNS)
        graph = ET.SubElement(root, 'graph', id="G", edgedefault="directed")
        nodes = {id(node): self.node_element(graph, i, node)
                 for i, node in enumerate(g.nodes)}
        for edge in g.edges:
            self.edge_element(graph, edge, nodes)
        return root 
            
    def node_element(self, root, index, node):
        e = ET.SubElement(root, 'node', id="node%d" % index, label=unicode(node.label))
        data = ET.SubElement(e, 'data', id="d0")
        data.text = unicode(node.label)
        return e
    
    def edge_element(self, root, edge, nodes_by_id):
        source = nodes_by_id[id(edge.source)].attrib['id']
        target = nodes_by_id[id(edge.destination)].attrib['id']
        return ET.SubElement(root, 'edge', source=source, target=target)
    
    

if __name__ == '__main__':
    E = [(1,2), (2,3), (1,4), (4,3)]
    g = EdgeSetGraphTool(E)()
    print >>open("/tmp/ad.graphml", "w"), \
        ET.tostring(GraphMLGraphLayout()(g))