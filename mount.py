#!/usr/bin/env python

from __future__ import with_statement

import os
import sys
import errno
import time
import stat

from fuse import FUSE, FuseOSError, Operations, fuse_get_context

from disk import Disk
from inode import FILE_TYPE


class Passthrough(Operations):
    def __init__(self, image_path):
        self.image_path = image_path
        assert os.path.exists(image_path)
        self.disk = Disk(image_path)
        self.disk.mount()

    # Filesystem methods
    # ==================

    def destroy(self, path = None):
        print("\nCalling fsdestroy")
        self.disk.unmount()
        
    def access(self, path, mode):
        print("\nCalling access with path:", path, "and mode:", mode)
        return 0

    def chmod(self, path, mode):
        print("\nCalling chmod with path:", path, "and mode:", mode)
        pass

    def chown(self, path, uid, gid):
        print("\nCalling chown with path:", path, "uid:", uid, "and gid:", gid)
        pass

    def getattr(self, path, fh=None):
        print("\nCalling getattr with path:", path)
        result = self.disk.get_attr(path)
        print(result)
        return result

    def readdir(self, path, fh):
        print("\nCalling readdir with path:", path, "and fh:", fh)
        for e in self.disk.dir_list(path):
            yield e

    def readlink(self, path):
        print("\nCalling readlink with path:", path)
        raise NotImplementedError
    
    def mknod(self, path, mode, dev):
        print("\nCalling mknod with path:", path, "mode:", mode, "and dev:", dev)
        if mode & stat.S_IFREG:
            self.disk.create(path, FILE_TYPE.FILE)
        elif mode & stat.S_IFDIR:
            self.disk.create(path, FILE_TYPE.DIR)
        else:
            raise NotImplementedError

    def rmdir(self, path):
        print("\nCalling rmdir with path:", path)
        self.disk.unlink(path)

    def mkdir(self, path, mode):
        print("\nCalling mkdir with path:", path, "and mode:", mode)
        self.disk.create(path, FILE_TYPE.DIR)

    def statfs(self, path):
        print("\nCalling statfs")
        return self.disk.get_stats()

    def unlink(self, path):
        print("\nCalling unlink with path:", path)
        self.disk.unlink(path)

    def symlink(self, name, target):
        print("\nCalling symlink with name:", name, "and target:", target)
        raise NotImplementedError

    def rename(self, old, new):
        print("\nCalling rename with old:", old, "and new:", new)
        self.disk.rename(old, new)

    def link(self, target, name):
        print("\nCalling link with target:", target, "and name:", name)
        self.disk.link(target, name)

    def utimens(self, path, times=None):
        print("\nCalling utime with path:", path, "and times:", times)
        if times:
            atime, mtime = times
        else:
            atime = mtime = time.time()
            
        atime, mtime = int(atime), int(mtime)
        self.disk.modify_timestamp(path, atime, mtime)

    # File methods
    # ============

    def open(self, path, flags):
        print("\nCalling open with path:", path, "and flags:", flags)
        return 0

    def create(self, path, mode, fi=None):
        print("\nCalling create with path:", path, "and mode:", mode)
        if mode & stat.S_IFREG:
            return self.disk.create(path, FILE_TYPE.FILE).index
        elif mode & stat.S_IFDIR:
            return self.disk.create(path, FILE_TYPE.DIR).index
        else:
            raise NotImplementedError

    def read(self, path, length, offset, fh):
        print("\nCalling read with path:", path, "length:", length, "and offset:", offset)
        return self.disk.read_file(path, offset, length)

    def write(self, path, buf, offset, fh):
        print("\nCalling write with path:", path, "buf:", "(omitted for performance reason)", "and offset:", offset)
        length = len(buf)
        print("buf length:", length)
        self.disk.write_file(path, offset, buf)
        return length

    def truncate(self, path, length, fh=None):
        print("\nCalling truncate with path:", path, "and length:", length, "and fh:", fh)
        self.disk.truncate(path, length)

    def flush(self, path, fh):
        print("\nCalling flush with path:", path, "and fh:", fh)
        # self.disk.flush()
        return 0

    def release(self, path, fh):
        print("\nCalling release with path:", path, "and fh:", fh)
        return 0

    def fsync(self, path, fdatasync, fh):
        print("\nCalling fsync with path:", path, "and fdatasync:", fdatasync, "and fh:", fh)
        self.disk.flush()


def main(mountpoint, image_path):
    FUSE(Passthrough(image_path), mountpoint, nothreads=True, foreground=True, allow_other=True)


if __name__ == '__main__':
    main(sys.argv[2], sys.argv[1])
