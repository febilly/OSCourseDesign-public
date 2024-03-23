from typing import Any, Generator, NewType
from construct import Struct, Int32ul, Container
from constants import *
from enum import Enum
from object_accessor import ObjectAccessor
from free_block_interface import FreeBlockInterface
from file_index_block import FileIndexBlock
from math import ceil
from utils import timestamp
from structures import InodeMode, InodeStruct

class FILE_TYPE(Enum):
    FILE = 0
    CHAR_DEVICE = 1
    DIR = 2
    BLOCK_DEVICE = 3
    

class Inode:
    """
    注意：
    需要手动flush
    内部会维护一个块数，在init的时候根据文件大小进行初始化
    （所以要保证在init的时候文件大小和块数是能对上的）
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
        self.block_count = ceil(self.data.d_size / BLOCK_BYTES)
        
    @classmethod
    def from_index(cls, index: int,
                 object_accessor: ObjectAccessor,
                 free_block_manager: FreeBlockInterface):
        """
        通过Inode号码构造Inode对象
        """
        # inode_data: Container[Any] = object_accessor.inodes[index]._obj
        inode_data: Container[Any] = object_accessor.inodes[index]
        return cls(index, inode_data, object_accessor, free_block_manager)
    
    @classmethod
    def new(cls, index: int,
            file_type: FILE_TYPE,
            object_accessor: ObjectAccessor,
            free_block_manager: FreeBlockInterface):
        mode = 0b1_00_0000_111_111_111
        mode |= file_type.value << 13
        mode = mode.to_bytes(2, 'little')
        inode = mode + b'\x00' * (INODE_BYTES - 4)
        inode = InodeStruct.parse(inode)
        time = timestamp()
        inode.d_atime = time
        inode.d_mtime = time
        return cls(index, inode, object_accessor, free_block_manager)
    
    @property
    def file_type(self) -> FILE_TYPE:
        return FILE_TYPE(self.data.d_mode.IFMT)
    
    @property
    def size(self) -> int:
        return self.data.d_size
    @size.setter
    def size(self, value: int) -> None:
        self.data.d_size = value
    
    def flush(self) -> None:
        self.object_accessor.inodes[self.index] = self.data
    
    def _get_index_block(self, block_index: int) -> FileIndexBlock:
        return FileIndexBlock.from_index(block_index, self.object_accessor)
    
    def _get_index_list(self, block_index: int) -> list[int]:
        list = self._get_index_block(block_index).to_list()
        while list and list[-1] == 0:
            list.pop()
        return list
    
    def _get_block_index(self, index: int):
        if index < FILE_INDEX_SMALL_THRESHOLD:
            return index, -1, -1
        if index < FILE_INDEX_LARGE_THRESHOLD:
            index -= FILE_INDEX_SMALL_THRESHOLD
            index_1 = index // FILE_INDEX_PER_BLOCK + INODE_SMALL_THRESHOLD
            index_2 = index % FILE_INDEX_PER_BLOCK
            return index_1, index_2, -1
        if index < FILE_INDEX_HUGE_THRESHOLD:
            index -= FILE_INDEX_LARGE_THRESHOLD
            index_1 = index // (FILE_INDEX_PER_BLOCK ** 2) + INODE_LARGE_THRESHOLD
            index_2 = (index % (FILE_INDEX_PER_BLOCK ** 2)) // FILE_INDEX_PER_BLOCK
            index_3 = index % FILE_INDEX_PER_BLOCK
            return index_1, index_2, index_3
        return -1, -1, -1

    def _block_index_planner(self, start: int):
        index_1, index_2, index_3 = self._get_block_index(start)
        while index_1 < INODE_HUGE_THRESHOLD:
            yield index_1, index_2, index_3
            index_1 += 1
            index_2 = -1 if index_1 < INODE_SMALL_THRESHOLD else 0
            index_3 = -1 if index_1 < INODE_LARGE_THRESHOLD else 0
        raise StopIteration

    def _block_list(self, start_block: int = 0) -> Generator[int, None, None]:
        """
        返回完整的文件块序号列表
        """        
        compressed_list: list[int] = self.data.d_addr.copy()
        while compressed_list and compressed_list[-1] == 0:  # 去掉末尾的0
            compressed_list.pop()

        for start_index_1, start_index_2, start_index_3 in self._block_index_planner(start_block):
            if start_index_2 == -1:
                yield compressed_list[start_index_1]
                continue
            for index_2 in self._get_index_list(compressed_list[start_index_1])[start_index_2:]:
                if start_index_3 == -1:
                    yield index_2
                    continue
                for index_3 in self._get_index_list(index_2)[start_index_3:]:
                    yield index_3
                start_index_3 = 0
            start_index_2 = 0
    def block_list(self, start_block: int = 0, length: int = -1) -> Generator[int, None, None]:
        """
        获取文件的块序号列表
        """
        if length < 0:
            length = self.block_count - start_block
        else:
            length = min(length, self.block_count - start_block)
            
        for block_index in self._block_list(start_block):
            if length <= 0:
                break
            yield block_index
            length -= 1
            
    def peek_block(self, index: int) -> int:
        """
        获取文件的一个块
        """
        iterator = self.block_list(index, 1)
        return next(iterator)
    
    def _new_data_block_index(self) -> int:
        return self.free_block_manager.allocate_block(zero=True)

    def _delete_data_block(self, index: int) -> None:
        self.free_block_manager.release_block(index)

    def push_block(self, index) -> None:
        """
        向索引列表中添加一个新的索引
        """
        insert_position: int = self.block_count
        self.block_count += 1
        index_1, index_2, index_3 = self._get_block_index(insert_position)
        
        # 小型文件
        if insert_position < FILE_INDEX_SMALL_THRESHOLD:
            self.data.d_addr[insert_position] = index
            return
        
        # 大型文件
        if insert_position < FILE_INDEX_LARGE_THRESHOLD:
            # 是否应新增第一层索引块
            if index_2 == 0:
                self.data.d_addr[index_1] = self._new_data_block_index()
            # 获取第一层索引块
            block_1 = self._get_index_block(self.data.d_addr[index_1])
            
            # 设置索引
            block_1[index_2] = index
            return
        
        # 巨型文件
        if insert_position < FILE_INDEX_HUGE_THRESHOLD:
            # 是否应新增第一层索引块
            if index_2 == index_3 == 0:
                self.data.d_addr[index_1] = self._new_data_block_index()
            # 获取第一层索引块
            block_1 = self._get_index_block(self.data.d_addr[index_1])

            # 是否应新增第二层索引块
            if index_3 == 0:
                block_1[index_2] = self._new_data_block_index()
            # 获取第二层索引块
            block_2 = block_1.subblock(index_2)
            
            # 设置索引
            block_2[index_3] = index
            return
        
        raise Exception("文件已达最大大小，无法增加索引块")
    
    def pop_block(self) -> int:
        pop_position: int = self.block_count - 1
        self.block_count -= 1
        index_1, index_2, index_3 = self._get_block_index(pop_position)
        
        # 小型文件
        if pop_position < FILE_INDEX_SMALL_THRESHOLD:
            result = self.data.d_addr[pop_position]
            self.data.d_addr[pop_position] = 0
            return result
        
        # 大型文件
        if pop_position < FILE_INDEX_LARGE_THRESHOLD:
            # 清除索引
            block_1 = self._get_index_block(self.data.d_addr[index_1])
            result = block_1[index_2]
            block_1[index_2] = 0
            
            # 是否应删除第一层索引块
            if index_2 == 0:
                self._delete_data_block(self.data.d_addr[index_1])
                self.data.d_addr[index_1] = 0
                
            return result
        
        # 巨型文件
        if pop_position < FILE_INDEX_HUGE_THRESHOLD:
            # 清除索引
            block_1 = self._get_index_block(self.data.d_addr[index_1])
            block_2 = block_1.subblock(index_2)
            result = block_2[index_3]
            block_2[index_3] = 0
            
            # 是否应删除第二层索引块
            if index_3 == 0:
                self._delete_data_block(self.data.d_addr[index_2])
                block_1[index_2] = 0
                
            # 是否应删除第一层索引块
            if index_2 == index_3 == 0:
                self._delete_data_block(self.data.d_addr[index_1])
                self.data.d_addr[index_1] = 0
            
            return result
        
        raise Exception("文件为空，无法删除索引块")
        
    def update_atime(self) -> None:
        self.data.d_atime = timestamp()
        
    def update_mtime(self) -> None:
        self.data.d_mtime = timestamp()
        