import unittest
from disk import Disk
from inode import FILE_TYPE
import shutil

class DiskTestCase(unittest.TestCase):
    def setUp(self):
        self.temp_img_file = "temp.img"
        shutil.copyfile("disk.img", self.temp_img_file)
        self.disk = Disk(self.temp_img_file)
        self.disk.mount()

    def tearDown(self):
        self.disk.unmount()

    def test_create_directory(self):
        NEW_DIR_PATH = '/unittestdir'
        self.disk.create_file(NEW_DIR_PATH, FILE_TYPE.DIR)
        self.assertTrue(self.disk.exists(NEW_DIR_PATH))

    def test_create_file(self):
        NEW_FILE_PATH = '/unittestdir/newfile1'
        self.disk.create_file(NEW_FILE_PATH, FILE_TYPE.FILE)
        self.assertTrue(self.disk.exists(NEW_FILE_PATH))

    def test_remove_file(self):
        FILE_PATH = '/unittestdir/newfile1'
        self.disk.create_file(FILE_PATH, FILE_TYPE.FILE)
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