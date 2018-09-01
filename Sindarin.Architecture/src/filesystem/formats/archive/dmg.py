
import os
from ui.gui.document_based import FileDocument



class Dmg(FileDocument):
    
    volname = "Volume"
    number_of_sectors = 1280
    mounted_at = None
    
    def mount(self):
        if self.mounted_at is None:
            self._create()
            mountpoint = "/Volumes/%s" % self.volname
            self._unmount(mountpoint)
            self._mount(self.filename)
            self.mounted_at = mountpoint
        return self.mounted_at
        
    def unmount(self):
        if self.mounted_at is not None:
            self._unmount(self.mounted_at)
            self.mounted_at = None
        
    def is_created(self):
        return os.path.exists(self.filename) and \
               os.stat(self.filename).st_size > 0

    def compress(self):
        self.unmount()
        self._create()
        new_filename = self.filename.replace(".dmg", "-udzo.dmg")
        cmd = "hdiutil convert %s -format UDZO -ov -o %s" % (self.filename, new_filename)
        if os.system(cmd): raise SystemError, cmd
        self.filename = new_filename
        return self

    def _create(self):
        if self.is_created(): return
        if not self.filename.endswith(".dmg"):
            self.save_as(self.filename + ".dmg")
        cmd = "hdiutil create %s -sectors %d -fs HFS+ -ov -type UDIF -volname '%s'" \
            % (self.filename, self.number_of_sectors, self.volname)
        if os.system(cmd):
            raise SystemError, cmd
        return self
    
    def _mount(self, filename):
        cmd = "hdiutil mount %s" % filename
        if os.system(cmd): raise SystemError, cmd
        
    def _unmount(self, mountpoint):
        if os.path.exists(mountpoint):
            cmd = "hdiutil eject %s" % mountpoint
            if os.system(cmd): raise SystemError, cmd



if __name__ == '__main__':
    t = Dmg.temp()
    print t.mount()
    print t.filename
    t.unmount()
    t.compress()
    print t.filename