from typing import Any, Callable
from construct import Struct, Int32ub, Int16ub, Container
from structures import *
from constants import *
from enum import Enum
from object_accessor import ObjectAccessor
from free_block_interface import FreeBlockInterface

class IndexBlock:
    def __init__(self, indexes: list[int], writer: Callable[[list[int]], None]):
        self.indexes = indexes
        self.writer = writer

    @classmethod
    def from_index(cls, index: int, object_accessor: ObjectAccessor):
        """
        通过块号构造索引对象
        """
        index_data = object_accessor.file_index_blocks[index]
        def writer(data: list[int]):
            object_accessor.file_index_blocks[index] = data
        return cls(index_data, writer)
    
    @classmethod
    def new(cls, index: int, object_accessor: ObjectAccessor):
        """
        创建一个新的索引块
        """
        def writer(data: list[int]):
            object_accessor.file_index_blocks[index] = data
        return cls([0] * FILE_INDEX_PER_BLOCK, writer)
    
    def flush(self) -> None:
        self.writer(self.indexes)
        
    def __getitem__(self, index: int) -> int:
        return self.indexes[index]

    def __setitem__(self, index: int, value: int) -> None:
        self.indexes[index] = value
        self.flush()
        
    def to_list(self) -> list[int]:
        return self.indexes
    