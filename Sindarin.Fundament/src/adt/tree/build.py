from adt.tree import Tree 



class TreeAssistant(object):

    Tree = Tree

    @classmethod
    def build(cls, spec):
        return cls()(spec)
    
    def __call__(self, spec):
        if isinstance(spec, tuple):
            root, sub = spec
            return self.Tree(root, [self(x) for x in sub])
        elif isinstance(spec, self.Tree):
            return spec
        else:
            return self.Tree(spec)

    def of(self, tree_type):
        self.Tree = tree_type
        return self
