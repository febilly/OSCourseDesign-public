import unittest
from disk import Disk
from inode import FILE_TYPE
import shutil

IMG = 'temp.img'

DIR = '/unittestdir'
FILE = '/unittestdir/unittestfile'

D1 = '/unittestdir/newdir1'
D2 = '/unittestdir/newdir2'

F1 = '/unittestdir/newfile1'
F2 = '/unittestdir/newfile2'

D1F1 = '/unittestdir/newdir1/newfile1'
D1F2 = '/unittestdir/newdir1/newfile2'

D1D2 = '/unittestdir/newdir1/newdir2'
D1D2F1 = '/unittestdir/newdir1/newdir2/newfile1'
D1D2F2 = '/unittestdir/newdir1/newdir2/newfile2'

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
        self.assertTrue(self.disk.exists(F1))
        self.disk.remove_file(F1)
        self.assertFalse(self.disk.exists(F1))

    def test_remove_dir(self):
        self.disk.create_file(D1, FILE_TYPE.DIR)
        self.assertTrue(self.disk.exists(D1))
        self.disk.create_file(D1F1, FILE_TYPE.FILE)
        self.assertTrue(self.disk.exists(D1F1))
        self.disk.create_file(D1D2, FILE_TYPE.DIR)
        self.assertTrue(self.disk.exists(D1D2))
        self.disk.create_file(D1D2F1, FILE_TYPE.FILE)
        self.assertTrue(self.disk.exists(D1D2F1))
        
        self.disk.remove_file(D1)
        self.assertFalse(self.disk.exists(D1))
        self.assertFalse(self.disk.exists(D1F1))
        self.assertFalse(self.disk.exists(D1D2))
        self.assertFalse(self.disk.exists(D1D2F1))
        
    def test_truncate_file(self):
        self.disk.write_file(FILE, 0, b'This is a test file')
        self.disk.truncate(FILE, 10)
        data = self.disk.read_file(FILE, 0, -1)
        self.assertEqual(data, b'This is a ')
        self.disk.truncate(FILE, 12)
        data = self.disk.read_file(FILE, 0, -1)
        self.assertEqual(data, b'This is a \0\0')

    def test_write_and_read_large_file(self):
        content = b''
        for i in range(100000):
            content += f'{i:0>5}'.encode()

        self.disk.write_file(FILE, -1, content)
        data = self.disk.read_file(FILE, -1, -1)
        self.assertEqual(data, content)

if __name__ == '__main__':
    unittest.main()