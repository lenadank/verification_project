
import time
from collections import OrderedDict

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from pattern.collection.basics import OneToMany
from sysclock.timers import StaggerTimer



class OrderedOneToMany(OneToMany, OrderedDict):
    pass



class MakingEventHandler(FileSystemEventHandler):
    
    COOLDOWN_TIME = 1 # sec
    
    def __init__(self):
        super(MakingEventHandler, self).__init__()
        self.operations = OrderedOneToMany().of(list)
        self.stag = {}
        
    def make_all(self):
        """Simply runs all the operations one by one according to the order
        through which they were inserted to self.operations."""
        for filename, op in self.operations.iterelementitems():
            self.run_op_func(filename, op)()
          
    def _operation_name(self, op):
        try:
            return op.__name__
        except AttributeError:
            try:
                return op.func.__name__
            except AttributeError:
                return '?'
    
    def run_op_func(self, filename, op):
        def run_op():
            print "Making ", filename, "--%s--> ..." % (self._operation_name(op))
            op()
        return run_op
    
    def on_any_event(self, event):
        super(MakingEventHandler, self).on_any_event(event)
        for filename, operation in self.operations.iterelementitems(): 
            if event.src_path.endswith(filename):
                key = (filename, operation)
                if key in self.stag:
                    self.stag[key].rewind()
                else:
                    to_do = self.run_op_func(filename, operation)
                    self.stag[key] = t = StaggerTimer(self.COOLDOWN_TIME, to_do)
                    t.start()
                
        self._sweep_clean()
        #print self.stag.keys()
                
    def _sweep_clean(self):
        """ Discards expired timers """
        def collect():
            for k, v in self.stag.iteritems():
                if v.is_finished():
                    v.join()
                else:
                    yield k, v
        self.stag = dict(collect())
        
    def shutdown(self):
        while self.stag:
            print self.stag
            self._sweep_clean()
            time.sleep(0.5)



class OnlineMake(Observer):
    
    def __init__(self, root_directory='.', recursive=True):
        super(OnlineMake, self).__init__()
        self.eh = MakingEventHandler()
        self.schedule(self.eh, root_directory, recursive=recursive)

    def __call__(self):
        self.eh.make_all()
        self.start()
        try:
            while True:
                time.sleep(1000)
        except KeyboardInterrupt:
            self.stop()
        self.eh.shutdown()
        self.join()
        

