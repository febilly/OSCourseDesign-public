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

    def flush(self) -> None:
        self.object_accessor.free_index_blocks[self.data_block_index] = self.data        

    