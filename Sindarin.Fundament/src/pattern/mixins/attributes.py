


class WithMixIn(object):
    """
    Defines the with_(...) method, which serves as syntactic sugar to configure
    an object's attributes on-the-fly.
    """
    
    def with_(self, **kw):
        for k, v in kw.iteritems():
            setattr(self, k, v)
        return self
