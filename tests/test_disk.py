import unittest
from disk import Disk
from inode import FILE_TYPE
import shutil

IMG = 'temp.img'

DIR = '/unittestdir'
FILE = '/unittestdir/newfile1'

D1 = '/unittestdir/newdir1'
D2 = '/unittestdir/newdir2'
D3 = '/unittestdir/newdir3'

F1 = '/unittestdir/newfile1'
F2 = '/unittestdir/newfile2'
F3 = '/unittestdir/newfile3'


class NewDiskTestCase(unittest.TestCase):
    def setUp(self):
        self.disk = Disk.new(IMG)
        self.disk.mount()
        self.disk.create_file(DIR, FILE_TYPE.DIR)
        self.disk.create_file(FILE, FILE_TYPE.FILE)

    def tearDown(self):
        self.disk.unmount()

    def test_create_directory(self):
        self.disk.create_file(D1, FILE_TYPE.DIR)
        self.assertTrue(self.disk.exists(D1))

    def test_create_file(self):
        self.disk.create_file(F1, FILE_TYPE.FILE)
        self.assertTrue(self.disk.exists(F1))

    def test_remove_file(self):
        self.disk.create_file(F1, FILE_TYPE.FILE)
        self.assertTrue(self.disk.exists(FILE_PATH))
        self.disk.remove_file(FILE_PATH)
        self.assertFalse(self.disk.exists(FILE_PATH))

    def test_truncate_file(self):
        FILE_PATH = '/unittestdir/newfile1'
        self.disk.create_file(FILE_PATH, FILE_TYPE.FILE)
        self.disk.write_file(FILE_PATH, 0, b'This is a test file')
        self.disk.truncate(FILE_PATH, 10)
        data = self.disk.read_file(FILE_PATH, 0, -1)
        self.assertEqual(data, b'This is a ')

    def test_write_and_read_large_file(self):
        BIG_FILE = '/unittestdir/bigfile'
        content = b''
        for i in range(100000):
            content += f'{i:0>5}'.encode()

        self.disk.write_file(BIG_FILE, -1, content)
        data = self.disk.read_file(BIG_FILE, -1, -1)
        self.assertEqual(data, content)

if __name__ == '__main__':
    unittest.main()