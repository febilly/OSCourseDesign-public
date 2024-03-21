from typing import Any
from construct import Struct, Int32ub, Int16ub, Container
from structures import *
from constants import *
from enum import Enum
from object_accessor import ObjectAccessor
from free_block_interface import FreeBlockInterface
from index_block import IndexBlock
from math import ceil

class FILE_TYPE(Enum):
    FILE = 0
    CHAR_DEVICE = 1
    DIRECTORY = 2
    BLOCK_DEVICE = 3

class Inode:
    """
    注意：
    每次增加或减少一个块之后，必须立刻更新文件大小;
    如果一个文件索引块是空的，就必须被移除;
    不论是增加文件大小还是减小，都要先操作一个索引块，再操作文件大小;
    （因为文件大小被用来定位需要操作的索引块）
    """
    def __init__(self, index: int,
                 data: Container[Any],
                 object_accessor: ObjectAccessor,
                 free_block_manager: FreeBlockInterface):
        self.index = index
        self.data = data
        self.object_accessor = object_accessor
        self.free_block_manager = free_block_manager
        
    @classmethod
    def from_inode_number(cls, index: int,
                 object_accessor: ObjectAccessor,
                 free_block_manager: FreeBlockInterface):
        """
        通过Inode号码构造Inode对象
        """
        inode_data: Container[Any] = object_accessor.inodes[index]
        return cls(index, inode_data, object_accessor, free_block_manager)
    
    def flush(self) -> None:
        self.object_accessor.inodes[self.index] = self.data
    
    def get_index_length(self) -> int:
        if 0 in self.data.d_addr:
            return self.data.d_addr.index(0)
        return len(self.data.d_addr)
    
    def get_index_block(self, block_index: int) -> IndexBlock:
        return IndexBlock.from_index(block_index, self.object_accessor)
    
    def get_self_block(self, index: int) -> IndexBlock:
        return self.get_index_block(self.data.d_addr[index])
    
    def get_index_list(self, block_index: int) -> list[int]:
        list = self.get_index_block(block_index).to_list()
        while list[-1] == 0:
            list.pop()
        return list
    
    def get_file_blocks_list(self) -> list[int]:
        """
        我们首先获取原始的混合索引表，
        根据列表的长度判断此文件是小型文件、大型文件，还是巨型文件。
        返回完整的文件块序号列表
        """
        compressed_list: list[int] = self.data.d_addr.copy()
        while compressed_list[-1] == 0:  # 去掉末尾的0
            compressed_list.pop()
        
        # 将直接索引块的序号加进result
        result: list[int] = compressed_list[:INODE_SMALL_THRESHOLD]
        
        # 解压一次直接索引块（如果有的话）
        for index in compressed_list[INODE_SMALL_THRESHOLD:INODE_LARGE_THRESHOLD]:
            result += self.get_index_list(index)
            
        # 解压二次直接索引块（如果有的话）
        indexes: list[int] = []  # 存放一次间接索引块的序号
        for index in compressed_list[INODE_LARGE_THRESHOLD:]:
            indexes += self.get_index_list(index)
        for index in indexes:
            result += self.get_index_list(index)
        
        return result
    
    def new_block_index(self) -> int:
        return self.free_block_manager.allocate(zero=True)

    def delete_index(self, index: int) -> None:
        self.free_block_manager.deallocate(index)
    
    def add_index(self, index) -> None:
        """
        向索引列表中添加一个新的索引
        """
        block_count: int = ceil(self.data.d_size / BLOCK_BYTES)

        # 小型文件
        if block_count < FILE_INDEX_SMALL_THRESHOLD:
            self.data.d_addr[block_count] = index
            return
        
        # 大型文件
        if FILE_INDEX_SMALL_THRESHOLD <= block_count < FILE_INDEX_LARGE_THRESHOLD:
            index_big = block_count - FILE_INDEX_SMALL_THRESHOLD
            index_1 = index_big // FILE_INDEX_PER_BLOCK
            index_0 = index_big % FILE_INDEX_PER_BLOCK

            # 是否应新增一级索引块
            if index_0 == 0:
                self.data.d_addr[index_1] = self.new_block_index()
            
            # 在计算出的位置设置索引
            index_block = self.get_self_block(index_1)
            index_block[index_0] = index
            return
        
        # 巨型文件
        if FILE_INDEX_LARGE_THRESHOLD <= block_count < FILE_INDEX_HUGE_THRESHOLD:
            index_huge = block_count - FILE_INDEX_LARGE_THRESHOLD
            index_2 = index_huge // (FILE_INDEX_PER_BLOCK ** 2)
            index_1 = (index_huge % (FILE_INDEX_PER_BLOCK ** 2)) // FILE_INDEX_PER_BLOCK
            index_0 = index_huge % FILE_INDEX_PER_BLOCK
            
            # 是否应新增二级索引块
            if index_1 == 0 and index_0 == 0:
                self.data.d_addr[index_2] = self.new_block_index()
            # 是否应新增一级索引块
            if index_0 == 0:
                index_block_1 = self.get_self_block(index_2)
                index_block_1[index_1] = self.new_block_index()
            
            # 在计算出的位置设置索引
            index_block_2 = self.get_self_block(index_2)
            index_block_1 = index_block_2.subblock(index_1)
            index_block_1[index_0] = index
            return
        
        raise Exception("文件已达最大大小，无法增加索引块")
    
    def remove_index(self) -> None:
        block_count: int = ceil(self.data.d_size / BLOCK_BYTES)
        
        # 小型文件
        if 0 < block_count <= FILE_INDEX_SMALL_THRESHOLD:
            self.data.d_addr[block_count] = 0
            return
        
        # 大型文件
        if FILE_INDEX_SMALL_THRESHOLD < block_count <= FILE_INDEX_LARGE_THRESHOLD:
            index_big = block_count - FILE_INDEX_SMALL_THRESHOLD
            index_1 = index_big // FILE_INDEX_PER_BLOCK
            index_0 = index_big % FILE_INDEX_PER_BLOCK
            
            # 在计算出的位置清除索引
            index_block = self.get_self_block(index_1)
            index_block[index_0] = 0

            # 是否应删除一级索引块
            if index_0 == 0:
                self.delete_index(self.data.d_addr[index_1])
                self.data.d_addr[index_1] = 0
            return
        
        # 巨型文件
        if FILE_INDEX_LARGE_THRESHOLD < block_count <= FILE_INDEX_HUGE_THRESHOLD:
            index_huge = block_count - FILE_INDEX_LARGE_THRESHOLD
            index_2 = index_huge // (FILE_INDEX_PER_BLOCK ** 2)
            index_1 = (index_huge % (FILE_INDEX_PER_BLOCK ** 2)) // FILE_INDEX_PER_BLOCK
            index_0 = index_huge % FILE_INDEX_PER_BLOCK
            
            # 在计算出的位置清除索引
            index_block_2 = self.get_self_block(index_2)
            index_block_1 = index_block_2.subblock(index_1)
            index_block_1[index_0] = 0
            
            # 是否应删除一级索引块
            if index_0 == 0:
                self.delete_index(self.data.d_addr[index_2])
                self.data.d_addr[index_2] = 0
            # 是否应删除二级索引块
            if index_1 == 0:
                self.delete_index(self.data.d_addr[index_2])
                self.data.d_addr[index_2] = 0
            return

        raise Exception("文件为空，无法删除索引块")
