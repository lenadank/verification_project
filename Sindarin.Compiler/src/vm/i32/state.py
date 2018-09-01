

class MachineState(object):
    
    class Buffers(dict):
        def __init__(self, *a, **kw):
            super(MachineState.Buffers, self).__init__(*a, **kw)
            self.uid = 0
        def allocate(self, size):
            self.uid += 1
            self[self.uid] = [0] * size
            return self.uid
    
    def __init__(self):
        self.buffers = self.Buffers({ })
        self.pointers = { }

    def __repr__(self):
        return "%s\n%s" % ("\n".join("%s: %r" % (name, contents)
                                     for name, contents in self.buffers.iteritems()),
                           "\n".join("%s -> %r" % (name, address)
                                     for name, address in self.pointers.iteritems()))
