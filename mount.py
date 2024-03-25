import os, sys
from errno import *
from stat import *
import fcntl
from threading import Lock

import fuse
from fuse import Fuse

from disk import Disk
from inode import FILE_TYPE

fuse.fuse_python_api = (0, 2)

fuse.feature_assert('stateful_files', 'has_init')


def flag2mode(flags):
    md = {os.O_RDONLY: 'rb', os.O_WRONLY: 'wb', os.O_RDWR: 'wb+'}
    m = md[flags & (os.O_RDONLY | os.O_WRONLY | os.O_RDWR)]

    if flags | os.O_APPEND:
        m = m.replace('w', 'a', 1)

    return m


class Xmp(Fuse):

    def __init__(self, *args, **kw):
        Fuse.__init__(self, *args, **kw)
        self.path = 'disk.img'
        self.disk = Disk("disk.img")

    def fsinit(self):
        print("Calling fsinit")
        self.disk.mount()
        
    def getattr(self, path):
        print("Calling getattr with path:", path)
        return self.disk.get_attr(path)

    def readlink(self, path):
        print("Calling readlink with path:", path)
        raise NotImplementedError

    def readdir(self, path, offset):
        print("Calling readdir with path:", path, "and offset:", offset)
        for e in self.disk.dir_list(path):
            yield fuse.Direntry(e)

    def unlink(self, path):
        print("Calling unlink with path:", path)
        self.disk.unlink(path)

    def rmdir(self, path):
        print("Calling rmdir with path:", path)
        self.disk.unlink(path)

    def symlink(self, path, path1):
        print("Calling symlink with path:", path, "and path1:", path1)
        raise NotImplementedError

    def rename(self, path, path1):
        print("Calling rename with path:", path, "and path1:", path1)
        self.disk.rename(path, path1)

    def link(self, path, path1):
        print("Calling link with path:", path, "and path1:", path1)
        self.disk.link(path, path1)
        
    def chmod(self, path, mode):
        print("Calling chmod with path:", path, "and mode:", mode)
        pass

    def chown(self, path, user, group):
        print("Calling chown with path:", path, "user:", user, "and group:", group)
        pass

    def create(self, path, flags, mode):
        print("Calling create with path:", path, "flags:", flags, "and mode:", mode)
        if mode & S_IFREG:
            self.disk.create(path, FILE_TYPE.FILE)
        elif mode & S_IFDIR:
            self.disk.create(path, FILE_TYPE.DIR)
        else:
            raise NotImplementedError
        
    def mknod(self, path, mode, dev):
        print("Calling mknod with path:", path, "mode:", mode, "and dev:", dev)
        if mode & S_IFREG:
            self.disk.create(path, FILE_TYPE.FILE)
        elif mode & S_IFDIR:
            self.disk.create(path, FILE_TYPE.DIR)
        else:
            raise NotImplementedError

    def mkdir(self, path, mode):
        print("Calling mkdir with path:", path, "and mode:", mode)
        self.disk.create(path, FILE_TYPE.DIR)

    def utime(self, path, times):
        print("Calling utime with path:", path, "and times:", times)
        atime, mtime = times
        self.disk.modify_timestamp(path, atime, mtime)

    def access(self, path, mode):
        print("Calling access with path:", path, "and mode:", mode)
        return 0

    def statfs(self):
        print("Calling statfs")
        return self.disk.get_stats()

    def read(self, path, size, offset):
        print("Calling read with path:", path, "size:", size, "and offset:", offset)
        return self.disk.read_file(path, offset, size)

    def write(self, path, buf, offset):
        print("Calling write with path:", path, "buf:", buf, "and offset:", offset)
        length = len(buf)
        self.disk.write_file(path, buf, offset)
        return length

    def release(self, path, flags):
        return 0

    def open(self, path, flags):
        print("Calling open with path:", path, "and flags:", flags)
        return 0

    def truncate(self, path, size):
        print("Calling truncate with path:", path, "and size:", size)
        self.disk.truncate(path, size)

    def fsync(self, path, isfsyncfile):
        print("Calling fsync with path:", path, "and isfsyncfile:", isfsyncfile)
        self.disk.flush()

    def fsdestroy(self, data = None):
        print("Calling fsdestroy")
        self.disk.unmount()

def main():

    usage = """
实现了一个UNIX V6++文件系统。

""" + Fuse.fusage

    server = Xmp(version="%prog " + fuse.__version__,
                 usage=usage, dash_s_do='setsingle')

    server.parse(values=server, errex=1)
    server.main()


if __name__ == '__main__':
    main()
