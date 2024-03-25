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

    def getattr(self, path):
        return self.disk.get_attr(path)

    def readlink(self, path):
        raise NotImplementedError

    def readdir(self, path, offset):
        for e in self.disk.dir_list(path):
            yield fuse.Direntry(e)

    def unlink(self, path):
        self.disk.unlink(path)

    def rmdir(self, path):
        self.disk.unlink(path)

    def symlink(self, path, path1):
        raise NotImplementedError

    def rename(self, path, path1):
        self.disk.rename(path, path1)

    def link(self, path, path1):
        self.disk.link(path, path1)

    def chmod(self, path, mode):
        pass

    def chown(self, path, user, group):
        pass

    def mknod(self, path, mode, dev):
        raise NotImplementedError

    def mkdir(self, path, mode):
        self.disk.create(path, FILE_TYPE.DIR)

    def utime(self, path, times):
        atime, mtime = times
        self.disk.modify_timestamp(path, atime, mtime)

    def access(self, path, mode):
        pass

    def statfs(self):
        return self.disk.get_stats()

    def fsinit(self):
        self.disk.mount()

    def read(self, path, size, offset):
        return self.disk.read_file(path, offset, size)

    def write(self, path, buf, offset):
        length = len(buf)
        self.disk.write_file(path, buf, offset)
        return length

    def release(self, path, flags):
        self.disk.unlink(path)

    def open(self, path, flags):
        return 0

    def truncate(self, path, size):
        self.disk.truncate(path, size)

    def fsync(self, path, isfsyncfile):
        self.disk.flush()

def main():

    usage = """
实现了一个UNIX V6++文件系统。

""" + Fuse.fusage

    server = Xmp(version="%prog " + fuse.__version__,
                 usage=usage, dash_s_do='setsingle')

    server.main()


if __name__ == '__main__':
    main()
