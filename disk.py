from block_device import *
from constants import *
from structures import *
from construct import Container

class Disk:
    def __init__(self, path: str):
        self.block_device = BlockDevice(path)
        
    def mount(self):
        self.super_block = self._read_super_block()
        
    def unmount(self):
        pass

    def format(self):
        pass
        
    def _read_super_block(self) -> Container:
        return SuperBlockStruct.parse(self.block_device.read_block_full(0) + self.block_device.read_block_full(1))
    
    @property
    def inode_size(self) -> int:
        return self.super_block.s_isize
    
    @property
    def block_size(self) -> int:
        return self.super_block.s_fsize