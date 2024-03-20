from typing import Any, Callable
from construct import Struct, Int32ub, Int16ub, Container
from structures import *
from constants import *
from enum import Enum
from object_accessor import ObjectAccessor
from free_block_interface import FreeBlockInterface

class IndexBlock:
    def __init__(self, index: int, indexes: list[int], object_accessor: ObjectAccessor):
        self.index = index
        self.indexes = indexes
        self.object_accessor = object_accessor
        if 0 in self.indexes:
            self.pointer = self.indexes.index(0)
        else:
            self.pointer = FILE_INDEX_PER_BLOCK

    @classmethod
    def from_index(cls, index: int, object_accessor: ObjectAccessor):
        """
        通过块号构造索引对象
        """
        index_data = object_accessor.file_index_blocks[index]
        return cls(index, index_data, object_accessor)
    
    @classmethod
    def new(cls, index: int, object_accessor: ObjectAccessor):
        """
        创建一个新的索引块
        """
        return cls(index, [0] * FILE_INDEX_PER_BLOCK, object_accessor)
    
    def __getitem__(self, index: int) -> int:
        return self.indexes[index]

    def __setitem__(self, index: int, value: int) -> None:
        self.indexes[index] = value
        self.flush()

    def flush(self) -> None:
        self.object_accessor.file_index_blocks[self.index] = self.indexes        
 
    def to_list(self) -> list[int]:
        return self.indexes.copy()
    
    def is_full(self) -> bool:
        return self.pointer == FILE_INDEX_PER_BLOCK
    
    def is_empty(self) -> bool:
        return self.pointer == 0
