
import copy



class TreeTransform(object):
    
    TOP_DOWN = 'top-down'
    BOTTOM_UP = 'bottom-up'
    IS_DESCENDING = False
    
    class Scalar(object): 
        def __init__(self, value): self.value = value
    
    def __init__(self, transformers=[], dir=TOP_DOWN, recurse=False): #@ReservedAssignment
        self.transformers = transformers[:]
        self.dir = dir
        self.recurse = recurse
        
    def __call__(self, tree):
        """
        Applies transformations to all the subtrees which match the
        transformers' criteria.
        @param tree: a Tree instance
        @return a new Tree with the transformed nodes
        """
        def at_root(tree, cont):
            root = tree.root
            for transformer in self.transformers:
                tree_tag = transformer(tree)
                if tree_tag is not None:
                    if isinstance(tree_tag, self.Scalar):
                        root = tree_tag.value
                        break
                    else:
                        tree_tag = self._in_your_place(tree.root, tree_tag)
                        return self._reapply(tree_tag, transformer)
            else:
                root = self.scalar_transform(root) or root
                
            return cont(root, tree.subtrees)
        
        def descend(root, subtrees):    
            return \
             type(tree)(root, self.flatten([self(s) for s in tree.subtrees]))
            
        if self.dir == self.TOP_DOWN:
            t = at_root(tree, cont=descend)
        else:
            t = at_root(descend(tree.root, tree.subtrees), cont=type(tree))
        return self._in_your_place(tree.root, t)
        
    def inplace(self, tree, out_diff=None, descent=True):
        """
        Applies transformations in-place to all the subtrees which match the
        transformers' criteria.
        @param tree: a Tree instance
        @param out_diff: [output] filled with tuples of 
          (original_subtree, new_subtree) for transformed locations
        @return the same tree, if the root is unchanged; otherwise it's a new
          tree. In the former case, inner nodes of the original instance are
          transformed as specified.
        """
        dif = out_diff.append if out_diff is not None else lambda x: None
        def at_root(tree):
            for transformer in self.transformers:
                tree_tag = transformer(tree)
                if tree_tag is not None:
                    if isinstance(tree_tag, self.Scalar):
                        dif((tree.root, tree_tag.value))
                        tree.root = self._in_your_place(tree.root, tree_tag.value)
                        break
                    else:
                        tree_tag = self._in_your_place(tree.root, tree_tag)
                        dif((tree, tree_tag))
                        return self._reapply(tree_tag, transformer, inplace=True)
            else:
                new_root = self.scalar_transform(tree.root)
                if new_root is not None:
                    tree.root = new_root
        # descend
        def descend(tree):
            if descent:
                for i in xrange(len(tree.subtrees)):
                    s = tree.subtrees[i]
                    s_tag = self.inplace(s, out_diff)
                    if s_tag is not s:
                        tree.subtrees[i] = s_tag
            self.flatten(tree.subtrees)
            return tree
        
        if self.dir == self.TOP_DOWN:
            x = at_root(tree)
            if x is not None: return x
            return descend(tree)
        else:
            x = descend(tree)
            x = at_root(x)
            if x is None:
                return tree
            else:
                return x

    def flatten(self, ltrees):
        i = 0
        while i < len(ltrees):
            if ltrees[i].root == []:
                ltrees[i:i+1] = ltrees[i].subtrees
            else:
                i += 1
        return ltrees

    def scalar_transform(self, scalar):
        """
        Optionally applies transformations to the value in the
        root.
        """
        return None

    def _reapply(self, tree, last_transformer, inplace=False):
        if self.IS_DESCENDING or self.recurse:
            rerun = lambda x, tree, descent=True: x.inplace(tree, descent=descent) if inplace else x(tree)
            if self.recurse:
                tree = rerun(self, tree, descent=True)
            else:
                # continue by applying other transformers
                tree.subtrees = [rerun(self, x) for x in tree.subtrees]
                tree = rerun(self._except(last_transformer), tree, descent=False)
        return tree

    def _except(self, transformer):
        tx = copy.copy(self)
        tx.transformers = [x for x in self.transformers if x is not transformer]
        return tx

    def _in_your_place(self, original, newer):
        """ (internal) This is an experimental aspect-oriented mechanism.
        The root of the tree is given the power to affect the result of a
        transformation when a new value is placed in its stead. This it
        does by implementing the method _aspect_TreeTransform_in_your_place.
        """
        try:
            f = original._aspect_TreeTransform_in_your_place
        except AttributeError:
            return newer
        return f(newer)