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
        print("\nCalling fsinit")
        self.disk.mount()
        
    def getattr(self, path):
        print("\nCalling getattr with path:", path)
        result = self.disk.get_attr(path)
        print(result)
        return result

    def readlink(self, path):
        print("\nCalling readlink with path:", path)
        raise NotImplementedError

    def readdir(self, path, offset):
        print("\nCalling readdir with path:", path, "and offset:", offset)
        for e in self.disk.dir_list(path):
            yield fuse.Direntry(e)

    def unlink(self, path):
        print("\nCalling unlink with path:", path)
        self.disk.unlink(path)

    def rmdir(self, path):
        print("\nCalling rmdir with path:", path)
        self.disk.unlink(path)

    def symlink(self, path, path1):
        print("\nCalling symlink with path:", path, "and path1:", path1)
        raise NotImplementedError

    def rename(self, path, path1):
        print("\nCalling rename with path:", path, "and path1:", path1)
        self.disk.rename(path, path1)

    def link(self, path, path1):
        print("\nCalling link with path:", path, "and path1:", path1)
        self.disk.link(path, path1)
        
    def chmod(self, path, mode):
        print("\nCalling chmod with path:", path, "and mode:", mode)
        pass

    def chown(self, path, user, group):
        print("\nCalling chown with path:", path, "user:", user, "and group:", group)
        pass

    def create(self, path, flags, mode):
        print("\nCalling create with path:", path, "flags:", flags, "and mode:", mode)
        if mode & S_IFREG:
            self.disk.create(path, FILE_TYPE.FILE)
        elif mode & S_IFDIR:
            self.disk.create(path, FILE_TYPE.DIR)
        else:
            raise NotImplementedError
        
    def mknod(self, path, mode, dev):
        print("\nCalling mknod with path:", path, "mode:", mode, "and dev:", dev)
        if mode & S_IFREG:
            self.disk.create(path, FILE_TYPE.FILE)
        elif mode & S_IFDIR:
            self.disk.create(path, FILE_TYPE.DIR)
        else:
            raise NotImplementedError

    def mkdir(self, path, mode):
        print("\nCalling mkdir with path:", path, "and mode:", mode)
        self.disk.create(path, FILE_TYPE.DIR)

    def utime(self, path, times):
        print("\nCalling utime with path:", path, "and times:", times)
        atime, mtime = times
        self.disk.modify_timestamp(path, atime, mtime)

    def access(self, path, mode):
        print("\nCalling access with path:", path, "and mode:", mode)
        return 0

    def statfs(self):
        print("\nCalling statfs")
        return self.disk.get_stats()

    def read(self, path, size, offset):
        print("\nCalling read with path:", path, "size:", size, "and offset:", offset)
        return self.disk.read_file(path, offset, size)

    def write(self, path, buf, offset):
        print("\nCalling write with path:", path, "buf:", buf, "and offset:", offset)
        length = len(buf)
        print("\nbuf length:", length)
        self.disk.write_file(path, buf, offset)
        return length

    def release(self, path, flags):
        return 0

    def open(self, path, flags):
        print("\nCalling open with path:", path, "and flags:", flags)
        return 0

    def truncate(self, path, size):
        print("\nCalling truncate with path:", path, "and size:", size)
        self.disk.truncate(path, size)

    def fsync(self, path, isfsyncfile):
        print("\nCalling fsync with path:", path, "and isfsyncfile:", isfsyncfile)
        self.disk.flush()

    def flush(self, path):
        print("\nCalling flush with path:", path)
        self.disk.flush()

    def fsdestroy(self, data = None):
        print("\nCalling fsdestroy")
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
