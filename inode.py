from construct import Struct, Int32ub, Int16ub
from typing import Callable
from structures import *
from enum import Enum
from utils import *

class FILE_TYPE(Enum):
    FILE = 0
    DIRECTORY = 1
    LINK = 2
    DEVICE = 3

class Inode:
    def __init__(self, read_block: Callable[[int], bytes], write_block: Callable[[int, bytes], None]):
        self.d_mode = None
        self.d_nlink = None
        self.d_uid = None
        self.d_gid = None
        
        self.d_size = None
        self.d_addr = [None] * 10
        
        self.d_atime = None
        self.d_mtime = None

    def parse_from_bytes(self, data):
        inode_struct = InodeStruct.parse(data)
        self.__dict__.update(inode_struct)

    def to_bytes(self):
        return InodeStruct.build(self.__dict__)
    
    def get_file_blocks_list(self):
        def expand_list()
        return self.d_addr