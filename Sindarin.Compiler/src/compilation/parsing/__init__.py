


class Tagged(unicode):
    """A string with additional attributes ('tags')."""

    def with_(self, **tags):
        self.__dict__.update(tags)
        return self

    def __repr__(self):
        r = super(Tagged, self).__repr__()
        if self.__dict__:
            return r + self.attrs_fmtd()
        else:
            return r
        
    def attrs_fmtd(self):
        return "[%s]" % (", ".join('%s=%r' % (k,v) for k,v in self.__dict__.iteritems()))
