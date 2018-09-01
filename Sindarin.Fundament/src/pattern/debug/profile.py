
import time
import sys
from collections import OrderedDict



class TimeProfile(object):
    
    class Clock(object):
        def __init__(self):
            self.started_at = None
            self.elapsed = 0
        def start(self):
            if self.started_at is None:
                self.started_at = time.time()
        def stop(self):
            if self.started_at is not None:
                self.elapsed += time.time() - self.started_at 
                
    def __init__(self):
        self.clocks = OrderedDict()
        
    def with_clock(self, name, clock=None):
        if clock is None: clock = self.Clock()
        self.clocks[name] = clock
        return self
    
    def __str__(self):
        lines = ["%s: %.2fs" % (name, clock.elapsed) 
                 for name, clock in self.clocks.iteritems()]
        return "\n".join(lines)

    def stop(self):
        """Stops all clocks."""
        for clock in self.clocks.itervalues():
            clock.stop()




class Stopwatch(object):
    """
    An adapter for using Clock via a "with" statement
    """
    def __init__(self):              self.clock = TimeProfile.Clock()
    def __enter__(self):             self.clock.start()
    def __exit__(self, e, v, tb):    self.clock.stop()



class ProcessingPhases(object):
    
    def __init__(self, phases, title=None):
        """
        @param phases: a list of tuples of the form (function, description)
        """
        self.title = title
        phases = [t if isinstance(t, tuple) else (t, 'Phase #%d') for t in phases]
        self.phases = phases
        self.verbose = False
        
    def __call__(self, datum, out=sys.stderr):
        for f, desc in self.phases:
            if self.verbose: print "%s..." % desc,
            datum = f(datum)
            if self.verbose: print
        return datum



if __name__ == '__main__':
    p = TimeProfile().with_clock("overall")
    p.clocks["overall"].start()
    time.sleep(2)
    p.stop()
    print p
    