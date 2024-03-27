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
from utils import debug_print

from docopt import docopt
import constants as C

doc = """
Usage:
    mount.py <image_path> <mountpoint> [-h | --help | -d | --debug]

Options:
    -h, --help     Show this screen.
    -d, --debug    Show debug information (and run in foreground).
"""

class MyFS(Operations):
    def __init__(self, image_path, debug):
        self.image_path = image_path
        C.OUTPUT_LOG = debug
        assert os.path.exists(image_path)
        self.disk = Disk(image_path)
        self.disk.mount()

    # Filesystem methods
    # ==================

    def destroy(self, path = None):
        debug_print("Calling [bold green]fsdestroy[/bold green]")
        self.disk.unmount()
        
    def access(self, path, mode):
        debug_print("Calling [bold green]access[/bold green] with path:", path, "and mode:", mode)
        return 0

    def chmod(self, path, mode):
        debug_print("Calling [bold green]chmod[/bold green] with path:", path, "and mode:", mode)
        pass

    def chown(self, path, uid, gid):
        debug_print("Calling [bold green]chown[/bold green] with path:", path, "uid:", uid, "and gid:", gid)
        pass

    def getattr(self, path, fh=None):
        debug_print("Calling [bold green]getattr[/bold green] with path:", path)
        result = self.disk.get_attr(path)
        debug_print(result)
        return result

    def readdir(self, path, fh):
        debug_print("Calling [bold green]readdir[/bold green] with path:", path, "and fh:", fh)
        for e in self.disk.dir_list(path):
            yield e

    def readlink(self, path):
        debug_print("Calling [bold green]readlink[/bold green] with path:", path)
        raise NotImplementedError
    
    def mknod(self, path, mode, dev):
        debug_print("Calling [bold green]mknod[/bold green] with path:", path, "mode:", mode, "and dev:", dev)
        if mode & stat.S_IFREG:
            self.disk.create(path, FILE_TYPE.FILE)
        elif mode & stat.S_IFDIR:
            self.disk.create(path, FILE_TYPE.DIR)
        else:
            raise NotImplementedError

    def rmdir(self, path):
        debug_print("Calling [bold green]rmdir[/bold green] with path:", path)
        self.disk.unlink(path)

    def mkdir(self, path, mode):
        debug_print("Calling [bold green]mkdir[/bold green] with path:", path, "and mode:", mode)
        self.disk.create(path, FILE_TYPE.DIR)

    def statfs(self, path):
        debug_print("Calling [bold green]statfs[/bold green]")
        return self.disk.get_stats()

    def unlink(self, path):
        debug_print("Calling [bold green]unlink[/bold green] with path:", path)
        self.disk.unlink(path)

    def symlink(self, name, target):
        debug_print("Calling [bold green]symlink[/bold green] with name:", name, "and target:", target)
        raise NotImplementedError

    def rename(self, old, new):
        debug_print("Calling [bold green]rename[/bold green] with old:", old, "and new:", new)
        self.disk.rename(old, new)

    def link(self, target, name):
        debug_print("Calling [bold green]link[/bold green] with target:", target, "and name:", name)
        self.disk.link(target, name)

    def utimens(self, path, times=None):
        debug_print("Calling [bold green]utime[/bold green] with path:", path, "and times:", times)
        if times:
            atime, mtime = times
        else:
            atime = mtime = time.time()
            
        atime, mtime = int(atime), int(mtime)
        self.disk.modify_timestamp(path, atime, mtime)

    # File methods
    # ============

    def open(self, path, flags):
        debug_print("Calling [bold green]open[/bold green] with path:", path, "and flags:", flags)
        return 0

    def create(self, path, mode, fi=None):
        debug_print("Calling [bold green]create[/bold green] with path:", path, "and mode:", mode)
        if mode & stat.S_IFREG:
            return self.disk.create(path, FILE_TYPE.FILE).index
        elif mode & stat.S_IFDIR:
            return self.disk.create(path, FILE_TYPE.DIR).index
        else:
            raise NotImplementedError

    def read(self, path, length, offset, fh):
        debug_print("Calling [bold green]read[/bold green] with path:", path, "length:", length, "and offset:", offset)
        return self.disk.read_file(path, offset, length)

    def write(self, path, buf, offset, fh):
        debug_print("Calling [bold green]write[/bold green] with path:", path, "buf:", "(omitted for performance reason)", "and offset:", offset)
        length = len(buf)
        debug_print("buf length:", length)
        self.disk.write_file(path, offset, buf)
        return length

    def truncate(self, path, length, fh=None):
        debug_print("Calling [bold green]truncate[/bold green] with path:", path, "and length:", length, "and fh:", fh)
        self.disk.truncate(path, length)

    def flush(self, path, fh):
        debug_print("Calling [bold green]flush[/bold green] with path:", path, "and fh:", fh)
        # self.disk.flush()
        return 0

    def release(self, path, fh):
        debug_print("Calling [bold green]release[/bold green] with path:", path, "and fh:", fh)
        return 0

    def fsync(self, path, fdatasync, fh):
        debug_print("Calling [bold green]fsync[/bold green] with path:", path, "and fdatasync:", fdatasync, "and fh:", fh)
        self.disk.flush()


def main(mountpoint, image_path, debug):
    FUSE(MyFS(image_path, debug), mountpoint, nothreads=True, foreground=debug, allow_other=True)


if __name__ == '__main__':
    # main(sys.argv[2], sys.argv[1])
    args = docopt(doc)
    main(args['<mountpoint>'], args['<image_path>'], args['--debug'])
    