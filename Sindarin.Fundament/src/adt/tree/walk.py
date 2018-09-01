"""
Traditional tree walks:
- Pre-order walk
- Post-order walk [not implemented yet]
- In-order walk - for binary trees [not implemented yet]
"""


class TreeWalk(object):
    
    class Visitor(object):
        def visit_node(self, tree_node):
            pass
        def done(self):
            return None
    
    def __init__(self, tree):
        self.tree = tree
    
    def __call__(self, visitor):
        for x in self:
            visitor.visit_node(x)
        return visitor.done()
    
    def __iter__(self):
        raise NotImplementedError
    

class PreorderWalk(TreeWalk):
    
    def __iter__(self):
        stack = [self.tree]
        while stack:
            top = stack[0]
            yield top
            stack[:1] = top.subtrees


class PostorderWalk(TreeWalk):
    
    def __iter__(self):
        DOWN, UP = 0, 1
        stack = [(DOWN, self.tree)]
        while stack:
            direction, top = stack.pop()
            if direction == UP:
                yield top
            else:
                stack += [(UP, top)] + [(DOWN, x) for x in top.subtrees]


class RichTreeWalk(object):
    """
    Provides advanced tree traversal by calling the visitor not only for each 
    node, but also when entering and when leaving a subtree.
    @todo: The interface of RichTreeWalk does not match that of TreeWalk; 
    should unify. 
    """
    
    class Visitor(object):
        SKIP = ('skip',)  # return this from enter() to prune
        def enter(self, subtree, prune=lambda:None):
            pass
        def leave(self, subtree):
            pass
        def join(self, node, prefix, infix, postfix):
            return None
        def done(self, root, final):
            return final

    def __init__(self, visitor):
        self.visitor = visitor
    
    def __call__(self, tree):
        final = self._traverse(tree)
        return self.visitor.done(tree, final)
    
    def _traverse(self, tree):
        descend = [1]
        prefix = self.visitor.enter(tree, descend.pop)
        if prefix is self.Visitor.SKIP:
            return prefix
        elif descend:
            infix = self._descend(tree)
        else:
            infix = []
        postfix = self.visitor.leave(tree)
        return self.visitor.join(tree, prefix, infix, postfix)

    def _descend(self, tree):
        return [self._traverse(sub) for sub in tree.subtrees]



class CollectVisitor(RichTreeWalk.Visitor):

    container = set

    def __init__(self, container=None):
        if container is None:
            self.collection = self.container()
        else:
            self.collection = container

    def done(self):
        return self.collection
    


if __name__ == '__main__':
    from adt.tree.build import TreeAssistant
    
    inputs = [(1, [(2, [3, 4, 5]), (6, [(7, [8]), 9])])]
    
    for input in inputs: #@ReservedAssignment
        tree = TreeAssistant.build(input)
        print tree
        print [x.root for x in PreorderWalk(tree)]
