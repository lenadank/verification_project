

class SimplisticPromoteMixIn(object):

    @classmethod
    def promote(cls, obj):
        if isinstance(obj, cls):
            return obj
        else:
            return cls(obj)
    

class TuplePromoteMixIn(object):

    @classmethod
    def promote(cls, obj):
        if isinstance(obj, cls):
            return obj
        elif isinstance(obj, tuple):
            return cls(*obj)
        else:
            return cls(obj)



class DownCastMixIn(object):
    
    @classmethod
    def downcast(cls, obj):
        if isinstance(obj, cls):
            return obj
        elif issubclass(cls, type(obj)):
            return cls(obj)
        return obj