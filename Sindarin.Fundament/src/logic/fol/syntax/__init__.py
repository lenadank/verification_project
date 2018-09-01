# encoding=utf-8
import copy


class Identifier(object):

    tags = [] # to be extended by subclasses

    def __init__(self, literal, kind, mnemonic=None, ns=None):
        """
        @param literal: symbolic literal for identifier
        @param kind: quantifier, connective, function, predicate, or variable
        @param mnemonic: another name; the mnemonic is used as an alias in 
            contexts where the literal is illegal as an identifier (e.g. some
            programming languages or mark-up languages) 
        @param ns: used internally to avoid name collisions
        """
        self.literal = literal
        self.kind = kind
        self.ns = ns
        if mnemonic is None:
            self.mnemonic = literal
        else:
            self.mnemonic = mnemonic

    def __repr__(self):
        if isinstance(self.literal, unicode):
            return u"'%s'" % self.literal
        else:
            return `self.literal`

    def __str__(self):
        return unicode(self.literal).encode("utf-8")

    def __unicode__(self):
        return unicode(self.literal)

    def __hash__(self):
        return hash(self.literal)

    def __eq__(self, other):
        if isinstance(other, Identifier):
            if self.kind == '?' or other.kind == '?': # wildcard
                return (self.literal, self.ns) == (other.literal, other.ns)
            else:
                return (self.literal, self.kind, self.ns) == (other.literal, other.kind, other.ns)
        elif isinstance(other, bool):
            return self.literal is other # patch -- since in Python, True == 1
        else:
            return self.literal == other

    def __ne__(self, other):
        return not self == other
    
    @classmethod
    def promote(cls, obj, kind='?'):
        if isinstance(obj, cls):
            return obj
        else:
            return cls(obj, kind)
        
    @classmethod
    def lift(cls, operation_on_literal):
        """
        @param operation_on_literal: a function on the literal type 
            (str->str, unicode->unicode, etc.)
        @return a corresponding Lifted instance 
        """
        return cls.Lifted(operation_on_literal, cls, ['literal', 'mnemonic'])

    class Lifted(object):
        def __init__(self, functor, class_type, attr_names):
            self.functor, self.class_type, self.attr_names = functor, class_type, attr_names
        def __call__(self, obj):
            if isinstance(obj, self.class_type):
                c = copy.copy(obj)
                for at in self.attr_names:
                    val = getattr(obj, at)
                    if val is not None: setattr(c, at, self.functor(val))
                return c
            else:
                return self.functor(obj)



class RepresentationForm(Identifier):
    
    def repr(self, elements):
        return "%r'%s'" % (self, ", ".join(`r` for r in elements))
