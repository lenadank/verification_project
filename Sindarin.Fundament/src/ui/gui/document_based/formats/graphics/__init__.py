
import os.path



class ImageGallery(object):
    def __init__(self, dir="img"):
        self.dir = dir
        os.system("mkdir -p " + dir)
        self.index = 0
    def import_file(self, pic_filename):
        _, pic_ext = os.path.splitext(pic_filename)
        imported = os.path.join(self.dir, "img%03d%s" % (self.index, pic_ext))
        open(imported, "wb").write(open(pic_filename, "rb").read())
        self.index += 1
        return imported
