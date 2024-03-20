from block_device import *
from constants import *
from structures import *
from construct import Container
import globals


class Disk:
    def __init__(self, path: str):
        globals.block_device = BlockDevice(path)
        
    def mount(self):
        self.superblock = self._read_superblock()
        
    def unmount(self):
        pass

    def format(self):
        pass
        
    def _read_superblock(self) -> Container:
        return SuperBlockStruct.parse(globals.block_device.read_block_full(0) + globals.block_device.read_block_full(1))
    
    @property
    def inode_size(self) -> int:
        return self.superblock.s_isize
    
    @property
    def block_size(self) -> int:
        return self.superblock.s_fsize