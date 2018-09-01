#encoding=utf-8
from collections import namedtuple
from adt.tree import Tree


class taggedtuple(object):
    """ Like taggedtuple, but different """
    def __init__(self, tag, field_names):
        self.tag = tag
        if isinstance(field_names, (str, unicode)):
            field_names = field_names.split()
        self.field_names = field_names
        
    def __call__(self, *a, **kw):
        return namedtuple("taggedtuple", self.field_names)(*a, **kw)
        
    
    
class ProgramAst(Tree):
    
    class KINDS:
        assign = taggedtuple("x=y", "x y")
        field_get = taggedtuple("x=y.f", "x y f")
        field_set = taggedtuple("x.f=y", "x f y")
        deref_get = taggedtuple("x=*y", "x y")
        deref_set = taggedtuple("*x=y", "x y")
        arr_get = taggedtuple("x=y[i]", "x y i")
        arr_set = taggedtuple("x[i]=y", "x i y")
        address_of = taggedtuple("x=&y", "x y")
        call = taggedtuple("x=f(args)", "x f args")
        call_void = taggedtuple("f(args)", "x f args")
        cast = taggedtuple("x=(type)y", "x type y")
        unop = taggedtuple(u"x=◇y", "x op y")
        binop = taggedtuple(u"x=y◇z", "x y op z")
        block = taggedtuple("{...}", "...")
        ifthen = taggedtuple("if (cond) cmd", "cond cmd")
        ifthenelse = taggedtuple("if (cond) yes else no", "cond yes no")
        by_tag = {}

    KINDS.by_tag = {a.tag: a for a in KINDS.__dict__.itervalues() if isinstance(a, taggedtuple)}

    @property
    def props(self):
        return self.root(*self.subtrees)

    @classmethod
    def reconstruct(cls, t):
        t = super(ProgramAst, cls).reconstruct(t)
        t.root = cls.KINDS.by_tag.get(t.root, t.root)
        return t
    