from typing import Any, Callable
from construct import Struct, Int32ub, Int16ub, Container
from constants import *
from object_accessor import ObjectAccessor
from free_block_interface import FreeBlockInterface

class FreeIndexBlock:
    def __init__(self, data_block_index: int, data: Container, object_accessor: ObjectAccessor):
        self.data_block_index = data_block_index
        self.data = data
        self.object_accessor = object_accessor

    @classmethod
    def from_index(cls, index: int, object_accessor: ObjectAccessor):
        """
        通过块号构造索引对象
        """
        index_data = object_accessor.free_index_blocks[index]
        return cls(index, index_data, object_accessor)
    
    @property
    def length(self) -> int:
        return self.data.s_nfree
    @length.setter
    def length(self, value: int) -> None:
        self.data.s_nfree = value
    
    def __getitem__(self, index: int) -> int:
        return self.data.s_free[index]

    def __setitem__(self, index: int, value: int) -> None:
        self.data.s_free[index] = value
        
    def is_empty(self) -> bool:
        return self.length == 0
    
    def is_full(self) -> bool:
        return self.length == FREE_INDEX_PER_BLOCK
    
    def try_push_flush(self, value: int) -> bool:
        if self.is_full():
            return False
        self[self.length] = value
        self.length += 1
        self.flush()
        return True
        
    def try_pop_flush(self) -> bool:
        if self.is_empty():
            return False
        self.length -= 1
        self[self.length] = 0
        self.flush()
        return True

    def flush(self) -> None:
        self.object_accessor.free_index_blocks[self.data_block_index] = self.data        
 
    def to_list(self) -> list[int]:
        return self.data.s_free.copy()
    
    def has_subblock(self) -> bool:
        return self.data.s_free[0] != 0
    
    def subblock(self) -> 'FreeIndexBlock':
        assert self.has_subblock()
        return FreeIndexBlock.from_index(self[0], self.object_accessor)
    