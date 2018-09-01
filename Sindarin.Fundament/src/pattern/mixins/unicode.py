

class UnicodeMixIn(object):
    """
    Assumes __unicode__, and fills in __str__ and __repr__.
    """
    
    use_encoding = "utf8"
    
    def __str__(self):
        return self.__unicode__().encode(self.use_encoding)
    
    __repr__ = __str__
