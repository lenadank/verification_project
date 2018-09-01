import pygtk #@UnresolvedImport
pygtk.require("2.0")



class GtkProcess(object):
    
    def __init__(self, main_window, **init_kwargs):
        self.main_window = main_window
        self.init_kwargs = init_kwargs
        self.on_load = lambda x: x
        
    def mainloop(self):
        import gtk #@UnresolvedImport
        mw = self.main_window(**self.init_kwargs)
        mw.window.connect("destroy", gtk.main_quit)
        mw = self.on_load(mw) or mw
        mw.window.show()
        gtk.main()
        
    def spawn(self):
        import os
        if os.fork() == 0:
            try:
                os.setpgrp()
                self.mainloop()
            except:
                import traceback
                traceback.print_exc()
            os._exit(0)
        # hmm... don't want to wait for child... sighandler?


