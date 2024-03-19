from block_device import CachedBlockDevice
from constants import *
from structures import *
from construct import Container
from typing import Callable, TypeVar, Generic
import globals

ItemType = TypeVar('ItemType')
class LazyArray(Generic[ItemType]):
    def __init__(self, length: int, getter: Callable[[int], ItemType], setter: Callable[[int, ItemType], None]):
        self.length = length
        self.getter = getter
        self.setter = setter
        
    def __getitem__(self, index):
        assert 0 <= index < self.length
        return self.getter(index)
    
    def __setitem__(self, index, value):
        assert 0 <= index < self.length
        self.setter(index, value)
        
    def __len__(self):
        return self.length
    
    def __iter__(self):
        for i in range(self.length):
            yield self[i]


class BlockTool:
    """
    提供访问数据结构的接口，向已经实现缓存了的磁盘发出读写指令
    """
    def __init__(self, block_device: CachedBlockDevice):
        self.block_device = block_device
    
    # 超级块的读写接口
    @property
    def super_block(self) -> Container:
        return SuperBlockStruct.parse(self.block_device.read_block_range(0, 2))
    
    @super_block.setter
    def super_block(self, value: Container):
        self.block_device.write_block_range(0, SuperBlockStruct.build(value))
    
    # inode的读写接口
    @property
    def inodes(self) -> LazyArray[Container]:
        def getter(index) -> Container:
            block_index = INODE_START + index // INODE_PER_BLOCK
            inode_index = index % INODE_PER_BLOCK
            
            block_bytes = self.block_device.read_block(block_index)
            return InodeBlockStruct.parse(block_bytes)[inode_index]
        
        def setter(index, value: Container) -> None:
            block_index = INODE_START + index // INODE_PER_BLOCK
            inode_index = index % INODE_PER_BLOCK
            
            block_bytes = self.block_device.read_block(block_index)
            inode_block = InodeBlockStruct.parse(block_bytes)
            
            inode_block[inode_index] = value
            block_bytes = InodeBlockStruct.build(inode_block)
            self.block_device.write_block(block_index, block_bytes)
            
        return LazyArray[Container](INODE_LENGTH, getter, setter)
    
    # 数据块分为文件数据块、目录数据块、文件索引块，以及空白块索引块
    # 文件数据块
    @property
    def file_blocks(self) -> LazyArray[bytes]:
        def getter(index) -> bytes:
            return self.block_device.read_block(index)
        
        def setter(index, value: bytes) -> None:
            self.block_device.write_block(index, value)
        
        return LazyArray[bytes](DATA_START, getter, setter)
    
    # 目录数据块
    @property
    def dir_blocks(self) -> LazyArray[list[Container]]:
        def getter(index) -> list[Container]:
            block_index = DATA_START + index
            block_bytes = self.block_device.read_block(block_index)
            return DirectoryBlockStruct.parse(block_bytes)
        
        def setter(index, value: list[Container]) -> None:
            block_index = DATA_START + index
            block_bytes = DirectoryBlockStruct.build(value)
            self.block_device.write_block(block_index, block_bytes)
        
        return LazyArray[list[Container]](DATA_START, getter, setter)
    
    # 文件索引块