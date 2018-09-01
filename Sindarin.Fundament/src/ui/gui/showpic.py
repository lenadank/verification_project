import pygtk #@UnresolvedImport
pygtk.require("2.0")

import gtk #@UnresolvedImport



class BoxOfImages(gtk.HBox):

    def add_image(self, filename):
        image = gtk.Image()
        image.set_from_file(filename)
        image.show()
        self.add(image)
        

class PictureWindow(object):

    def __init__(self, filename=None):
        self.window = gtk.Window()
        self.sw = gtk.ScrolledWindow()
        self.sw.set_size_request(850, 600)
        self.image = BoxOfImages()
        if filename is not None:
            self.image.add_image(filename)
        self.sw.add_with_viewport(self.image)
        self.window.add(self.sw)
        self.window.show_all()
        
        
if __name__ == '__main__':
    import sys
    pw = PictureWindow(sys.argv[1])
    gtk.main()
