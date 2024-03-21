from object_accessor import ObjectAccessor
from construct import Struct, Int32ub, Int16ub, Container
from constants import *
from free_block_interface import FreeBlockInterface


class Superblock(FreeBlockInterface):
    def __init__(self, data: Container, object_accessor: ObjectAccessor):
        self.data = data
        self.object_accessor = object_accessor
    
    def allocate(self, zero=False) -> int:
        self.data.s_nfree -= 1
        index = self.data.s_free[self.data.s_nfree]
        
        # 将下一个空闲块索引块读入superblock
        if self.data.s_nfree == 0:
            if self.data.s_free[0] == 0:
                raise Exception("No free block")
            next_block = self.object_accessor.free_index_blocks[self.data.s_free[0]]
            self.data.s_nfree = next_block.s_nfree
            self.data.s_free = next_block.s_free
            
        if zero:  # 是否清零
            self.object_accessor.clear_data_block(index)
            
        return index

    def deallocate(self, block_index: int) -> None:
        if self.data.s_nfree < FREE_INDEX_PER_BLOCK:
            self.data.s_free[self.data.s_nfree] = block_index
            self.data.s_nfree += 1
        else:
            # 写入下一个空闲块索引块
            new_block = Container(s_nfree=self.data.s_nfree, s_free=self.data.s_free)
            self.object_accessor.free_index_blocks[block_index] = new_block

            self.data.s_nfree = 1
            self.data.s_free = [0] * FREE_INDEX_PER_BLOCK
            self.data.s_free[0] = new_block.data_block_index