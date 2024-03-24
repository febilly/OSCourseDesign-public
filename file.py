from inode import Inode

class File:
    def __init__(self, path: str, inode: Inode):
        self.path = path
        self.inode = inode