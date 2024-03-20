from typing import Any
from construct import Struct, Int32ub, Int16ub, Container
from structures import *
from constants import *
from enum import Enum
from object_accessor import ObjectAccessor
from free_block_interface import FreeBlockInterface
from math import ceil

class FILE_TYPE(Enum):
    FILE = 0
    CHAR_DEVICE = 1
    DIRECTORY = 2
    BLOCK_DEVICE = 3

class Inode:
    """
    注意：每次增加或减少一个块之后，必须立刻更新文件大小
    """
    def __init__(self, data: Container[Any],
                 object_accessor: ObjectAccessor,
                 free_block_manager: FreeBlockInterface):
        self.data = data
        self.object_accessor = object_accessor
        self.free_block_manager = free_block_manager
        
    @classmethod
    def from_inode_number(cls, inode_number: int,
                 object_accessor: ObjectAccessor,
                 free_block_manager: FreeBlockInterface):
        """
        通过Inode号码构造Inode对象
        """
        inode_data: Container[Any] = object_accessor.inodes[inode_number]
        return cls(inode_data, object_accessor, free_block_manager)
    
    
    def get_indexes(self, block_index: int) -> list[int]:
        """
        获取一个索引块的索引列表
        """
        return self.object_accessor.file_index_blocks[block_index]
    
    def get_file_blocks_list(self) -> list[int]:
        """
        我们首先获取原始的混合索引表，
        根据列表的长度判断此文件是小型文件、大型文件，还是巨型文件。
        返回完整的文件块序号列表
        """
        compressed_list: list[int] = self.data.d_addr.copy()
        # 去掉末尾的0
        while compressed_list[-1] == 0:
            compressed_list.pop()
        
        # 将直接索引块的序号加进result
        result: list[int] = compressed_list[:INODE_SMALL_THRESHOLD]
        
        # 解压一次直接索引块（如果有的话）
        for index in compressed_list[INODE_SMALL_THRESHOLD:INODE_LARGE_THRESHOLD]:
            result += self.get_indexes(index)
            
        # 解压二次直接索引块（如果有的话）
        indexes: list[int] = []  # 存放一次间接索引块的序号
        for index in compressed_list[INODE_LARGE_THRESHOLD:]:
            indexes += self.get_indexes(index)
        for index in indexes:
            result += self.get_indexes(index)
        
        return result
    
    def _create_index_block(self) -> int:
        """
        创建一个新的索引块
        """
        block_index: int = self.free_block_manager.allocate()
        self.object_accessor.file_index_blocks[block_index] = [0] * FILE_INDEX_PER_BLOCK
        return block_index

    def _delete_index_block(self, index: int) -> None:
        """
        删除一个索引块
        """
        self.free_block_manager.deallocate(index)
    
    def add_index(self, index) -> None:
        """
        向索引列表中添加一个新的索引
        """
        length = ceil(self.data.d_size / BLOCK_BYTES)
        if length < FILE_INDEX_SMALL_THRESHOLD:
            # 直接索引表还没满，直接加进直接索引表
            self.data.d_addr[length] = index
        elif length < FILE_INDEX_LARGE_THRESHOLD:
            if (length - FILE_INDEX_SMALL_THRESHOLD) % FILE_INDEX_PER_BLOCK == 0:
                # 刚写满上一个索引，现在应该增加一个一次间接索引块
                # 增加一个一次间接索引块，然后把第一项设置为index
                new_index = self._create_index_block()
                self.get_indexes(new_index)[0] = index
                self.data.d_addr[length] = new_index
            else:
                # 直接加进一次间接索引块
                index_0 = (length - FILE_INDEX_SMALL_THRESHOLD) // FILE_INDEX_PER_BLOCK
                index_1 = (length - FILE_INDEX_SMALL_THRESHOLD) % FILE_INDEX_PER_BLOCK
                self.get_indexes(self.data.d_addr[index_0])[index_1] = index
    
    
    def set_file_blocks_list(self, index_list: list[int]) -> None:
        """
        将文件块序号列表压缩后写回Inode
        """
        