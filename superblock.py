from typing import Any
from structures import *
from block_device import CachedBlockDevice
from construct import Struct, Int32ub, Int16ub, Container
from free_block_interface import FreeBlockInterface


class Superblock(FreeBlockInterface):
    def __init__(self, data: Container[Any], block_device: CachedBlockDevice):
        self.data = data
        self.block_device = block_device
        
    def allocate(self) -> int:
        pass

    def deallocate(self, block_index: int) -> None:
        pass
