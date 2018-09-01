
import copy

from adt.tree import Tree
from adt.tree.build import TreeAssistant
from adt.tree.transform import TreeTransform

from pattern.meta.oop import nest, nested

from logic.fol.syntax import Identifier



@nest
class CompositeIdentifier(Identifier):

    @nested
    class InternalStructure(Tree):
        def __repr__(self):
            if isinstance(self.root, CompositeIdentifier.Monad):
                return self.root.repr(*tuple(self.subtrees))
            elif not self.subtrees:
                return unicode(self.root)
            else:
                return super(CompositeIdentifier.InternalStructure, self).__repr__()
        @property
        def kind(self):
            if isinstance(self.root, CompositeIdentifier.Monad):
                return self.root.kind(*tuple(self.subtrees))
            elif not self.subtrees:
                return self.root.kind
            else:
                return 'composite'
        @property
        def mnemonic(self):
            if isinstance(self.root, CompositeIdentifier.Monad):
                return self.root.mnemonic(*tuple(self.subtrees))
            elif not self.subtrees:
                return self.root.mnemonic
            else:
                return unicode(self)
        def normalize(self):
            def transformer(self):
                if isinstance(self.root, Identifier) and \
                   isinstance(self.root.literal, type(self)) and \
                   not self.subtrees:
                    return self.root.literal
            return TreeTransform([transformer])(self)
          
    @nested  
    class Monad(object):
        """
        An identifier Monad modifies an identifier in some way, when used in
        an internal node of CompositeIdentifier.InternalStructure.
        """
        def kind(self, *substructure):
            return 'composite'
        def repr(self, *substructure):
            raise NotImplementedError
        def mnemonic(self, *substructure):
            raise NotImplementedError
        def __call__(self, *substructure):
            ta = TreeAssistant().of(CompositeIdentifier.InternalStructure)
            return CompositeIdentifier(ta((self, substructure)).normalize(),
                                       None)
        # A Monad is never cloned (makes sure '==' works)
        def __copy__(self):
            return self
        def __deepcopy__(self, memo):
            return self

    def _kind(self):
        return self.literal.kind

    def _mnemonic(self):
        return self.literal.mnemonic

    kind = property(_kind, lambda self, x: None)
    mnemonic = property(_mnemonic, lambda self, x: None)


class QuickMonad(CompositeIdentifier.Monad):
    """
    A convenience class for defining Monads quickly.
    """
    
    def __init__(self, name=None, kind=None, fmt=None, mnemonic_fmt=None):
        self.name = name
        self._kind_override = kind
        if name is None:
            self.fmt = fmt or '%r'
            self.mnemonic_fmt = mnemonic_fmt or fmt.replace("%r", "%s")
        else:
            self.fmt = fmt or '%s[%%r]' % name
            self.mnemonic_fmt = mnemonic_fmt or '%s_%%s' % name
            
    def kind(self, symbol):     return self._kind_override or symbol.kind
    def repr(self, symbol):     return self.fmt % symbol
    def mnemonic(self, symbol): return self.mnemonic_fmt % symbol.mnemonic



class Modifier(Identifier):
    
    def __init__(self, symbol, modifier, kind=None, modifier_mnemonic=None):
        self.symbol = symbol
        self.modifier = modifier
        super(Modifier, self).__init__(unicode(self), symbol.kind)
        self._kind_override = kind
        if modifier_mnemonic is not None:
            self.modifier_mnemonic = modifier_mnemonic
        else:
            self.modifier_mnemonic = modifier
        
    def tuple(self):
        return self.symbol, self.modifier
    
    def __repr__(self):
        return self.__unicode__()
    
    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return u"%s%s" % self.tuple()
    
    def _kind(self):
        return self._kind_override or self.symbol.kind
    
    def _mnemonic(self):
        return u"%s%s" % (self.modifier_mnemonic, self.symbol.mnemonic)
    
    kind = property(_kind, lambda self, x: None)
    literal = property(__unicode__, lambda self, x: None)
    mnemonic = property(_mnemonic, lambda self, x: None)
    

class SpecificModifier(Modifier):
    
    SPECIFIC = ""
    KIND = None
    MNEMONIC = None
    
    def __init__(self, symbol):
        super(SpecificModifier, self).__init__(symbol, self.SPECIFIC, 
                                               self.KIND, self.MNEMONIC)



class IdentifierTag(Identifier):
    
    def __init__(self, symbol, tags=[], markup=""):
        self.symbol = symbol
        super(IdentifierTag, self).__init__(symbol.literal, symbol.kind, mnemonic=None)
        # TODO: Make tags a property
        self.tags = tags + symbol.tags
        self.markup = markup

    def __repr__(self):
        return self.__unicode__()
    
    def __str__(self):
        return self.__unicode__()

    def __unicode__(self):
        return u"%s%s" % (self.markup, super(IdentifierTag, self).__unicode__())

    def _literal(self):
        return self.symbol.literal

    def _set_literal(self, literal):
        # 'copy-on-write'
        if literal is not self.symbol.literal:
            self.symbol = copy.copy(self.symbol)
            self.symbol.literal = literal

    def _kind(self):
        return self.symbol.kind

    def _mnemonic(self):
        return self.symbol.mnemonic

    literal = property(_literal, _set_literal)
    kind = property(_kind, lambda self, x: None)
    mnemonic = property(_mnemonic, lambda self, x: None)


class SpecificIdentifierTag(IdentifierTag):
    
    SPECIFIC = ""
    MARKER = ""
    
    def __init__(self, symbol):
        super(SpecificIdentifierTag, self).__init__(symbol, [self.SPECIFIC], self.MARKER)


class QuickTag(object):
    
    def __init__(self, tag_name, marker=""):
        self.tags = [tag_name]
        self.marker = marker
        
    def __call__(self, symbol):
        return IdentifierTag(symbol, self.tags, self.marker)
