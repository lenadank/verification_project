

class NamingConvention(object):
    """
    An interface for implementing custom name-escaping schemes for
    non-alphanumeric variables.
    """
    def escape(self, name):
        return name
    def unescape(self, name):
        return name
    def check(self, name):
        pass

    class NamingError(NameError):
        pass

    def _check(self, v, literal):
        if literal and not v.match(literal):
            raise self.NamingError(literal)
        
    def escape_safe(self, name):
        e = self.escape(name)
        self.check(e)   # raises an exception if malformed
        return e

