
import collections
import copy
from pattern.mixins.promote import SimplisticPromoteMixIn



class Subsequence(collections.MutableSequence):
    """
    Transient reference to a part of a sequence, which forwards any updates
    performed on it to the original sequence. 
    Effective when you have a function that modifies a list in-place, and you
    want to run it on a part of a larger list.
    """
    
    def __init__(self, master_sequence, ref_slice):
        self.master = master_sequence
        self.slice = slice(*ref_slice.indices(len(self.master)))
    
    def __len__(self):
        return (self.slice.stop - self.slice.start) // self.slice.step
    
    def __getitem__(self, index):
        mindex = self.slice.start + index * self.slice.step
        if mindex >= self.slice.stop:
            raise IndexError, 'subsequence index out of range'
        return self.master[mindex]
        
    def __setitem__(self, index, item):
        mindex = self.slice.start + index * self.slice.step
        if mindex >= self.slice.stop:
            raise IndexError, 'subsequence index out of range'
        self.master[mindex] = item
        
    def __delitem__(self, index):
        if self.slice.step != 1:
            raise NotImplementedError
        mindex = self.slice.start + index
        if mindex >= self.slice.stop:
            raise IndexError, 'subsequence index out of range'
        del self.master[mindex]
        self.slice = slice(self.slice.start, self.slice.stop - 1, self.slice.step)

    def insert(self, index, item):
        if self.slice.step != 1:
            raise NotImplementedError
        mindex = self.slice.start + index
        if mindex > self.slice.stop:   # @note  not ">="
            raise IndexError, 'subsequence index out of range'
        self.master.insert(mindex, item)
        self.slice = slice(self.slice.start, self.slice.stop + 1, self.slice.step)



class GluedSupersequence(collections.MutableSequence):
    """
    Chains two or more sequences to a longer sequence. Changes to the super-
    sequence are reflected in the parts composing it.
    """

    def __init__(self, components):
        self.components = components
        
    def __len__(self):
        return sum(len(c) for c in self.components)
        
    def __getitem__(self, index):
        component, cindex = self._index(index)
        return component[cindex]
    
    def __setitem__(self, index, item):
        component, cindex = self._index(index)
        component[cindex] = item
        
    def __delitem__(self, index):
        component, cindex = self._index(index)
        del component[cindex]
        
    def insert(self, index, item):
        component, cindex = self._index(index, allow_end=True)
        component.insert(cindex, item)
        
    def _index(self, index, allow_end=False):
        for component in self.components:
            sz = len(component)
            if index < sz or (allow_end and index==sz):
                return component, index
            else:
                index -= sz
        raise IndexError, 'supersequence index out of range'
            


class SegmentedList(SimplisticPromoteMixIn, list):
    
    def __init__(self, iterable=[]):
        super(SegmentedList, self).__init__(iterable)
        if isinstance(iterable, SegmentedList):
            self.labels = iterable.labels.copy()
        else:
            self.labels = {}
        
    def extend(self, other):
        other = self.promote(other)
        self.labels.update(self._shift(other.labels, len(self)))
        super(SegmentedList, self).extend(other)
        
    def __iadd__(self, other):
        self.extend(other)
        return self
    
    def __add__(self, other):
        c = copy.copy(self)
        c += other
        return c
    
    def __radd__(self, other):
        return self.promote(other) + self
    
    def labeled(self, label):
        """
        Convenience method.
        Assigns given 'label' to the first item (position 0) and
        returns self.
        """
        self.labels[label] = 0
        return self
    
    def _shift(self, labels, offset, criterion=lambda k,v: True):
        return {k: v + (offset if criterion(k,v) else 0)
                for k,v in labels.iteritems()}

    # Other list manipulations, reprogrammed to preserve labeling

    def __setitem__(self, index, item):
        if isinstance(index, slice):
            raise NotImplementedError
        super(SegmentedList, self).__setitem__(index, slice)
    def __delitem__(self, index):
        raise NotImplemented
    def __imul__(self, times):
        raise NotImplementedError
    def insert(self, index, item):
        raise NotImplementedError
    def remove(self, item):
        raise NotImplementedError
    def sort(self):
        raise NotImplementedError  # Not even supported!


