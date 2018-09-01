
import os.path
import tempfile
import shutil



class Document(object):
    pass


class FileDocument(object):
    
    def __init__(self, filename):
        self.filename = filename
        
    def file(self, mode="r"):
        return file(self.filename, mode)
    
    def erase(self):
        if os.path.isfile(self.filename):
            os.unlink(self.filename)
    
    def save_as(self, new_filename):
        shutil.move(self.filename, new_filename)
        self.filename = new_filename
    
    @classmethod
    def temp(cls):
        fd, filename = tempfile.mkstemp()
        os.close(fd)
        return cls(filename)


class DirectoryDocument(object):
    
    def __init__(self, path, primary_filename=None):
        self.path = path
        self.primary_filename = primary_filename
        
    def file(self, filename=None, mode="r"):
        if filename is None:
            if self.primary_filename is None:
                raise ValueError, 'DirectoryDocument has no primary file; ' \
                    'filename must be specified'
            else:
                filename = self.primary_filename
        return file(os.path.join(self.path, filename), mode)

    def erase(self):
        for filename in os.listdir(self.path):
            if filename not in [".", ".."]:
                os.unlink(os.path.join(self.path, filename))
        os.rmdir(self.path)

    @classmethod
    def temp(cls):
        return cls(tempfile.mkdtemp())
    
    

if __name__ == "__main__":
    tempdoc = FileDocument.temp()
    print tempdoc.filename
    tempdoc.file("w").write("Temporary data")
    print tempdoc.file("r").read()
    print os.path.exists(tempdoc.filename) and "File still exists." or "File does not exist anymore."
    tempdoc.erase()
    print os.path.exists(tempdoc.filename) and "File still exists." or "File does not exist anymore."
    
    tempdoc = DirectoryDocument.temp()
    print tempdoc.path
    tempdoc.primary_filename = 'index.txt'
    tempdoc.file(mode="w")
    tempdoc.erase()
    
    