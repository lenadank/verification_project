
import copy
from pattern.meta.event_driven import EventBox
from pattern.mixins.promote import SimplisticPromoteMixIn



class AttentiveMonotoneList(list):
    
    on_add = lambda *a, **kw: 0 # patch for copy.copy()
    
    def __init__(self, *a):
        super(AttentiveMonotoneList, self).__init__(*a)
        self.on_add = self._event_box_factory()
        
    def append(self, item):
        self.on_add(len(self), item)
        super(AttentiveMonotoneList, self).append(item)
    
    def extend(self, other):
        for item in other: self.append(item)

    def __iadd__(self, other):
        self.extend(other)
        return self
    
    def _event_box_factory(self):
        e = AttentiveEventBox()
        e.on_add += [self._redispatch]
        return e
    
    def _redispatch(self, _, event_handler):
        for index, item in enumerate(self):
            event_handler(index, item)
    
    def insert(self, index, item):         raise NotImplementedError
    def remove(self, item):                raise NotImplementedError
    def __setitem__(self, index, value):   raise NotImplementedError
    def __delitem__(self, index):          raise NotImplementedError


class AttentiveEventBox(AttentiveMonotoneList, EventBox):

    def _event_box_factory(self):
        return EventBox()




class AttentiveMatrix(list):
    """
    A matrix represented by a list of lists. When rows or cells are modified,
    an event is triggered.
    """
    
    class Row(SimplisticPromoteMixIn, list):
        owner = None
        index = None
        def __setitem__(self, column_index, item):
            if item != self[column_index]:
                super(AttentiveMatrix.Row, self).__setitem__(column_index, item)
                if self.owner is not None:
                    self.owner.on_set_cell(self.index, column_index)
    
    def __init__(self, iterable=()):
        super(AttentiveMatrix, self).__init__()
        self.on_add_row = EventBox()     # on_add_row(row_index)
        self.on_set_cell = EventBox()    # on_set_cell(row_index, column_index)
        self.extend(iterable)
        
    def _myrow(self, index, item):
        item = self.Row.promote(item)
        if item.owner: item = copy.copy(item)
        item.owner = self; item.index = index
        return item
        
    def __setitem__(self, index, row):
        row = self._myrow(index, row)
        super(AttentiveMatrix, self).__setitem__(index, row)
        for column_index in xrange(len(row)):
            self.on_set_cell(index, column_index)
            
    def __setslice__(self, i, j, rows):
        j = min(len(self), j)
        if j - i != len(rows):
            raise NotImplementedError
        for k, row in enumerate(rows):
            self[i+k] = row
            
    def append(self, row):
        row = self._myrow(len(self), row)
        super(AttentiveMatrix, self).append(row)
        self.on_add_row(row.index)
    
    def insert(self, index, row):
        row = self._myrow(index, row)
        super(AttentiveMatrix, self).insert(index, row)
        for i in xrange(index+1, len(self)):
            self[i].index = i
        self.on_add_row(row.index)
    
    def extend(self, iterable):
        for row in iterable:
            self.append(row)  # not surprisingly

    def __iadd__(self, other):
        self.extend(other)
        return self



if __name__ == '__main__':
    def tracer(i, item): print "Added", item
    l = AttentiveMonotoneList()
    l += [8]
    l.on_add += [tracer]
    l += [1]