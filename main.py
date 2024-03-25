from disk import Disk
from inode import FILE_TYPE
import shutil

temp_img_file = "temp.img"
shutil.copyfile("disk.img", temp_img_file)

disk = Disk(temp_img_file)
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

disk.mount()
NEW_FILE_PATH_2 = '/testdir/newfile2'
disk.create_file(NEW_FILE_PATH_2, FILE_TYPE.FILE)
disk.write_file(NEW_FILE_PATH_2, -1, b'hello222')
disk.flush()

data = disk.read_file(NEW_FILE_PATH, -1, -1)
print(data)
data = disk.read_file(NEW_FILE_PATH_2, -1, -1)
print(data)

disk.unmount()
disk.mount()

BIG_FILE = '/testdir/bigfile'
disk.create_file(BIG_FILE, FILE_TYPE.FILE)
content = b''
for i in range(100000):
    content += f'{i:0>5}'.encode()
    
disk.write_file(BIG_FILE, -1, content)

disk.unmount()
disk.mount()

data = disk.read_file(BIG_FILE, -1, -1)

if data == content:
    print('Test passed')

disk.unmount()
