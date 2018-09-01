from adt.tree.walk import PreorderWalk


class ApplyTo(object):
    
    def __init__(self, nodes=lambda x: x):
        self.noperation = nodes
        
    def inplace(self, tree):
        for node in PreorderWalk(tree):
            node.root = self.noperation(node.root)
        return tree
    
    def asnew(self, tree):
        root = self.noperation(tree.root)
        subtrees = [self.asnew(s) for s in tree.subtrees]
        return type(tree)(root, subtrees)

    def __call__(self, tree):
        return self.asnew(tree)



class TreeNodeRename(ApplyTo):
    
    def __init__(self, renaming={}):
        super(TreeNodeRename, self).__init__(lambda label: renaming.get(label, label))
