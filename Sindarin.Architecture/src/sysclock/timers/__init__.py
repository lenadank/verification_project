from threading import Timer



class StaggerTimer(object):
    """
    Wraps a Timer thread, adding the rewind() and stagger() methods.
    rewind():  recreates the timer using the same parameters as were given
               at construction.
    stagger(): if the timer has not fired yet, rewinds.
    """
    
    def __init__(self, *a, **kw):
        self._a, self._kw = a, kw
        self._create_timer()
        
    def _create_timer(self):
        self.timer = Timer(*self._a, **self._kw)
    
    def start(self):
        self.timer.start()
        
    def cancel(self):
        self.timer.cancel()
    
    def rewind(self):
        """ Pushes the timer back to t=0 and starts counting again
        from the beginning.
        """
        self.timer.cancel()
        self._create_timer()
        self.timer.start()
    
    def stagger(self):
        if self.is_alive(): self.rewind()
    
    def is_alive(self):
        return self.timer.is_alive()
    
    def is_finished(self):
        return self.timer.finished.is_set() and not self.is_alive()
    
    def join(self, timeout=None):
        return self.timer.join(timeout)
        
