from object_accessor import ObjectAccessor
from construct import Struct, Int32ub, Int16ub, Container
from free_block_interface import FreeBlockInterface


class Superblock(FreeBlockInterface):
    def __init__(self, data: Container, object_accessor: ObjectAccessor):
        self.data = data
        self.object_accessor = object_accessor
    
    def allocate(self) -> int:
        pass

    def load_next_free_block_index(self) -> int:
        assert self.data.s_nfree == 1
        assert self.data.s_free[0] != 0


    def deallocate(self, block_index: int) -> None:
        pass
