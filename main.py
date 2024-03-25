from disk import Disk
from inode import FILE_TYPE
import shutil

IMG = 'temp.img'

DIR = '/unittestdir'
FILE = '/unittestdir/newfile1'

D1 = '/unittestdir/newdir1'
D2 = '/unittestdir/newdir2'

F1 = '/unittestdir/newfile1'
F2 = '/unittestdir/newfile2'

D1F1 = '/unittestdir/newdir1/newfile1'
D1F2 = '/unittestdir/newdir1/newfile2'

D1D2 = '/unittestdir/newdir1/newdir2'
D1D2F1 = '/unittestdir/newdir1/newdir2/newfile1'
D1D2F2 = '/unittestdir/newdir1/newdir2/newfile2'

disk = Disk.new(IMG)
disk.mount()
disk.create(DIR, FILE_TYPE.DIR)
disk.create(FILE, FILE_TYPE.FILE)

disk.create(D1, FILE_TYPE.DIR)
assert(disk.exists(D1))
disk.create(D1F1, FILE_TYPE.FILE)
assert(disk.exists(D1F1))
disk.create(D1D2, FILE_TYPE.DIR)
assert(disk.exists(D1D2))
disk.create(D1D2F1, FILE_TYPE.FILE)
assert(disk.exists(D1D2F1))

disk.unlink(D1)
assert not (disk.exists(D1))
assert not (disk.exists(D1F1))
assert not (disk.exists(D1D2))
assert not (disk.exists(D1D2F1))

disk.unmount()