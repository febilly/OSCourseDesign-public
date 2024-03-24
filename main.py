from disk import Disk
from inode import FILE_TYPE

disk = Disk("disk_test2.img")
disk.mount()

FILEPATH = '/testfilename123'

inode = disk._get_inode(FILEPATH)
print(inode.data.d_size)
data = disk.read_file(FILEPATH, -1, -1)
print(data)

disk.write_file(FILEPATH, -1, b'hello')
data = disk.read_file(FILEPATH, -1, -1)
print(data)

NEW_DIR_PATH = '/testdir'
disk.create_file(NEW_DIR_PATH, FILE_TYPE.DIR)

NEW_FILE_PATH = '/testdir/newfile1'
disk.create_file(NEW_FILE_PATH, FILE_TYPE.FILE)
disk.write_file(NEW_FILE_PATH, -1, b'hello')
disk.flush()
data = disk.read_file(NEW_FILE_PATH, -1, -1)
print(data)

disk.unmount()