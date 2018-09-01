
from threading import Thread, Condition
from pattern.meta.event_driven import EventBox



class WorkerThread(Thread):
    
    def __init__(self):
        super(WorkerThread, self).__init__()
        self.condition = Condition()
        self.state = lambda: None
        self.on_process = EventBox()
    
    def state_changed(self):
        c = self.condition
        with c:
            c.notify()
    
    def run(self):
        c = self.condition
        last_state = None #self.state()
        while True:
            with c:
                state = self.state()
                while state == last_state:
                    c.wait()
                    state = self.state()
            
            try:
                self.on_process(state)
            except:
                import traceback
                traceback.print_exc()
            last_state = state
            
