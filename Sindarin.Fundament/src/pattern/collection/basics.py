
import sys
import copy
import collections



class OneToMany(dict):

    container = list
    aggregate = lambda x,y: x+y

    def of(self, container_factory):
        """e.g.   c = OneToMany().of(set)"""
        self.container = container_factory
        if isinstance(self.container, type):
            if issubclass(self.container, set):
                self.aggregate = lambda x,y: x|y
            elif issubclass(self.container, dict):
                def join(d1, d2): d1.update(d2); return d1
                self.aggregate = join
        else:
            def notimp(d1, d2): raise NotImplementedError
            self.aggregate = notimp # you're on your own, pal
        return self

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            self[key] = n = self.container()
            return n

    def update(self, other):
        for key, vals in other.iteritems():
            try:
                c = self.aggregate(dict.__getitem__(self, key), vals)
            except KeyError:
                c = vals
            self[key] = c

    def fill(self, values, category_func, join_func=list.append):
        for value in values:
            join_func(self[category_func(value)], value)
            
    def cleanup(self):
        none = self.container()
        obvious = [key for (key,val) in self.iteritems() if val == none]
        for o in obvious:
            del self[o]
        return self

    def iterelements(self):
        for vs in self.itervalues():
            for v in vs:
                yield v
                
    def iterelementitems(self):
        for k,vs in self.iteritems():
            for v in vs:
                yield k,v
        
    @classmethod        
    def promote(cls, o):
        if not isinstance(o, cls): o = cls(o)
        return o


class OneToOne(dict):
    
    image = lambda x: x
    
    def of(self, image_func):
        self.image = image_func
        return self

    def updated(self, other_mapping):
        self.update(other_mapping)
        return self

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            self[key] = n = self.image(key)
            return n


class Histogram(dict):

    def __getitem__(self, key):
        try:
            return dict.__getitem__(self, key)
        except KeyError:
            self[key] = n = 0
            return n
    

class NamedSet(set):
    
    def with_name(self, name):
        self.name = name
        return self
    
    def __repr__(self):
        return "%s: %s" % (self.name, super(NamedSet, self).__repr__(self))


class NaiveOrderedSet(list):
    
    def update(self, iterable):
        for item in iterable: self.add(item)
    
    def add(self, item):
        if item not in self:
            self.append(item)
            

class OrderedSet(collections.OrderedDict, collections.MutableSet):
    """
    Based on an implementation from StackOverflow.
    @see: http://stackoverflow.com/questions/1653970/does-python-have-an-ordered-set
    """
    
    def __init__(self, iterable=()):
        super(OrderedSet, self).__init__()
        self.update(iterable)

    def update(self, *args, **kwargs):
        if kwargs:
            raise TypeError("update() takes no keyword arguments")

        for s in args:
            for e in s:
                self.add(e)

    def updated(self, *args, **kwargs):
        self.update(*args, **kwargs)
        return self

    def add(self, elem):
        self.setdefault(elem, len(self))

    def discard(self, elem):
        self.pop(elem, None)
        
    def index(self, elem):
        try:
            return self[elem]
        except KeyError:
            raise ValueError, '%r not in OrderedSet' % (elem,)

    def __le__(self, other):
        return all(e in other for e in self)

    def __lt__(self, other):
        return self <= other and self != other

    def __ge__(self, other):
        return all(e in self for e in other)

    def __gt__(self, other):
        return self >= other and self != other

    def __repr__(self):
        return 'OrderedSet([%s])' % (', '.join(map(repr, self.keys())))

    def __str__(self):
        return '{%s}' % (', '.join(map(repr, self.keys())))

    difference = property(lambda self: self.__sub__)
    difference_update = property(lambda self: self.__isub__)
    intersection = property(lambda self: self.__and__)
    intersection_update = property(lambda self: self.__iand__)
    issubset = property(lambda self: self.__le__)
    issuperset = property(lambda self: self.__ge__)
    symmetric_difference = property(lambda self: self.__xor__)
    symmetric_difference_update = property(lambda self: self.__ixor__)
    union = property(lambda self: self.__or__)

    # This is my addition
    def iteritems(self):
        """Iterates over pairs of (i, self[i])"""
        return ((i, self[i]) for i in xrange(len(self)))



class OrderedDict(dict):
    """
    An associative array which also keeps record of the order in which keys
    have been inserted. 
    """
    
    class ValueList(object):
        def __init__(self, ordered_dict):
            self.dict = ordered_dict
        def __len__(self):
            return len(self.dict.order)
        def __getitem__(self, i):
            return self.dict[self.dict.order[i]]
        def __iter__(self):
            return self.dict.itervalues()
        def __repr__(self):
            return "/%s/" % `list(self)`
        def __add__(self, other):
            return list(self) + list(other)
        def __radd__(self, other):
            return list(other) + list(self)
    
    def __init__(self, items=[]):
        super(OrderedDict, self).__init__()
        self.order = []
        for key, value in items:
            self[key] = value
            
    def __setitem__(self, key, value):
        if key not in self:
            self.order.append(key)
        super(OrderedDict, self).__setitem__(key, value)

    def __delitem__(self, key):
        if key in self:
            self.order = [x for x in self.order if x != key]
        super(OrderedDict, self).__delitem__(key)
        
    def update(self, other_dict):
        for k,v in other_dict.iteritems():
            self[k] = v
        
    def iteritems(self):
        return ((key, self[key]) for key in self)
    
    def itervalues(self):
        return (self[key] for key in self)
    
    def items(self):
        return list(self.iteritems())
    
    def values(self):
        return self.ValueList(self)
    
    def keys(self):
        return self.order
    
    def __iter__(self):
        return iter(self.order)
    
    def __repr__(self):
        return "/{%s}/" % ", ".join("%r: %r" % (k,v) for (k,v) in self.iteritems())



class OrderedMultiDict(collections.MutableMapping):
    """
    Same as OrderedDict, but a key can occur more than once in the ordering.
    When iterating, a key is visited as many times as it has been assigned a
    value. Hence, a key can have more than one value; normal lookup will 
    return only one value, but iterating items() will produce all of them.
    
    @note: d.keys() is a list rather than a set, preserves the order of 
      insertion and the repetitions.
    @note: This is a naive implementation using a list of pairs. It's not so
      efficient.
    """
    
    def __init__(self, mapping_or_pairs=()):
        if isinstance(mapping_or_pairs, collections.Mapping):
            self._items = list(mapping_or_pairs.iteritems())
        elif isinstance(mapping_or_pairs, collections.Iterable):
            self._items = list(mapping_or_pairs)
        else:
            raise TypeError, "need mapping or iterable, got '%s'" % type(mapping_or_pairs)
        
    def __getitem__(self, key):
        for k,v in self._items:
            if k == key: return v
        raise KeyError, key
    
    def __setitem__(self, key, value):
        self._items.append((key, value))

    def __delitem__(self, key):
        self._items = [(k,v) for k,v in self._items if not k == key]

    def __len__(self):
        return len(self._items)
    
    def __iter__(self):
        return self.iterkeys()

    def __repr__(self):
        return "/{%s}/" % ", ".join("%r: %r" % (k,v) for k,v in self.iteritems())

    def keys(self):          return list(self.iterkeys())
    def iterkeys(self):      return (k for k,_ in self._items)
    def values(self):        return list(self.itervalues())
    def itervalues(self):    return (v for _,v in self._items)
    def items(self):         return self._items
    def iteritems(self):     return iter(self._items)
    


class ListWithAdd(list):
    """A list with an add() method so it's compatible with set and OrderedSet."""
    
    def add(self, item):
        self.append(item)

    
class DictionaryWithAdd(dict):
    """A dict with a + operator which combines dictionaries using update()."""
    def __add__(self, other):
        if isinstance(other, dict):
            c = copy.copy(self)
            c.update(other)
            return c
        else:
            return NotImplemented


class KeyedSet(dict):
    """
    Basically like a dictionary, but iteration is done on values instead
    of keys.
    """
    
    def __iter__(self):
        return self.itervalues()

    def __contains__(self, value):
        return value in self.itervalues()
    
    def index(self, value):
        i = 0
        for val in self.itervalues():
            if val == value:
                return i
            i += 1
        else:
            raise ValueError, '%r not in KeyedSet' % value


class UnorderedHashingMixin(object):
    """
    A set's hash value is computed by applying a commutative-associative
    function to hash values of members.
    """
    commut_assoc_func = staticmethod(lambda x, y: (x + y) % sys.maxint)

    def __hash__(self):
        elements = self.hash_elements
        return reduce(self.commut_assoc_func, (hash(x) for x in elements), 1)
    
    @property
    def hash_elements(self):
        return self


class UnorderedDictHashingMixin(UnorderedHashingMixin):

    @property
    def hash_elements(self):
        return self.iteritems()


class HashableSet(set, UnorderedHashingMixin):
    __hash__ = UnorderedHashingMixin.__hash__


class HashableDict(dict, UnorderedDictHashingMixin):
    __hash__ = UnorderedDictHashingMixin.__hash__



class Cabinet(OneToMany):
    """
    A type of container which holds elements sorted into buckets according
    to predefined drawer (category) functors.
    """
    
    container = set
    
    SINGULAR = 'singular'
    DOUBLE = 'double'
    
    def __init__(self, *a, **kw):
        super(Cabinet, self).__init__(*a, **kw)
        self.sorting_key = lambda x: (0, x)
        
    def with_key(self, sorting_key, role=DOUBLE):
        """
        @param sorting_key: a function from an object to the corresponding
          key
        @param role: if role==SINGULAR, then sorting_key(o) is a single value
          used as the drawer key; if role==DOUBLE (the default) then it is a
          tuple (key, value) where 'value' is the item stored in the cabinet
          instead of 'o'.
        @note If role==DOUBLE but sorting_key(o) is not a 2-tuple, the cabinet
          falls back to the behaviour of role==SINGULAR.
        """
        if role == self.SINGULAR:
            self.sorting_key = lambda x: (sorting_key(x), x)
        else:
            self.sorting_key = sorting_key
        return self
        
    def add(self, item):
        try:
            drawer, element = self._item_pair(item)
            self[drawer].add(element)
        except self.Excluded:
            pass
        
    def remove(self, item):
        try:
            drawer, element = self._item_pair(item)
            self[drawer].remove(element)
        except self.Excluded:
            raise ValueError, "'%r' not in cabinet" % (item,)

    def has_item(self, item):
        try:
            drawer, element = self._item_pair(item)
            return element in self.get(drawer, ())
        except self.Excluded:
            return False

    def _item_pair(self, item):
        sk = self.sorting_key(item)
        try:
            drawer, element = sk
        except TypeError:
            drawer, element = sk, item
        return drawer, element

    def updated(self, iterable):
        self.update(iterable)
        return self
        
    def update(self, iterable):
        for item in iterable:
            self.add(item)
        return self
    
    class Excluded: pass



class IdSet(collections.Set, Cabinet):
    """
    Behaves just like a set, but items are keyed according to some other
    criterion, not the keys' __hash__ and == operations.
    The default is storing the objects according to their native id().
    """
    
    def __init__(self, iterable=()):
        super(IdSet, self).__init__()
        self.with_key(id, role=Cabinet.SINGULAR).of(ListWithAdd).update(iterable)
    
    def __contains__(self, item):
        return self.has_key(id(item))
    
    def __iter__(self):
        return self.iterelements()
    
    __len__ = Cabinet.__len__  # collections.Set defines __len__ -> 0

    def __repr__(self):
        return '%s(%s)' % (type(self).__name__, list(self))
    


class WorksetGenerator(object):
    """
    A generator (as in 'from __future__ import generators') which yields one
    item from the work-set at each iteration, removing it from the work-set.
    
    @note: it's a Python "generator"; it does not, as may be implied, generate
    work-sets. 
    """

    def __init__(self, workset=None):
        if workset is None:
            self.workset = OrderedSet()
        else:
            self.workset = workset

    def __iter__(self):
        while len(self.workset) > 0:
            node = self.workset.pop()
            yield node
            
    def push(self, work_item):
        # - workset must be a list subclass (not set)
        self.workset.insert(0, work_item)



class Traverse(object):
    
    def __call__(self, collection):
        yield collection
        if isinstance(collection, dict):
            it = collection.itervalues()
        else:
            try:
                it = iter(collection)
            except:
                it = []
        for v in it:
            for x in self(v):
                yield x


class BuildupSet(set):
    """
    (auxiliary) A set with a 'dirty' flag which is set whenever a new element
    is added.
    """
    
    def __init__(self, *a, **kw):
        super(BuildupSet, self).__init__(*a, **kw)
        self.dirty = not not self
    
    def add(self, item):
        if item not in self:
            super(BuildupSet, self).add(item)
            self.dirty = True
            
    def update(self, iterable):
        for item in iterable:
            self.add(item)
    
    def accept(self):
        self.dirty = False
        return self
    
    
class BuildupSets(OneToMany):
    
    container = BuildupSet
    
    @property
    def dirty(self):
        for s in self.itervalues():
            if s.dirty: return True
        else:
            return False
        
    def accept(self):
        for s in self.itervalues():
            s.accept()

