
class Trace(object):
    def __call__(self, *objects):
        raise NotImplemented
    def write(self, text):
        raise NotImplemented
    def flush(self):
        pass


class TraceOff(Trace):
    def __call__(self, *objects):
        pass
    def write(self, text):
        pass
    

class TracePrint(Trace):
    def __init__(self, outfile):
        self.outfile = outfile
    def __call__(self, *objects):
        if objects:
            for o in objects[:-1]:
                print >>self.outfile, o,
            print >>self.outfile, objects[-1]
    def write(self, text):
        self.outfile.write(text)


import sys

off = TraceOff()
out = TracePrint(sys.stdout)
err = TracePrint(sys.stderr)
