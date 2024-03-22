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

class Stage(Enum):
    SMALL = 0
    LARGE = 1
    HUGE = 2

class block_index_planner:
    def __init__(self, start: int = 0, len: int = -1):
        self.start = start
        self.len = len
        self.stage = Stage.SMALL
    
    def _small(self, start: int) -> Generator[tuple[int, int, int], None, None]:
        for index_0 in range(start, INODE_SMALL_THRESHOLD):
            yield 0, 0, index_0
        
    def _large(self, start: int) -> Generator[tuple[int, int, int], None, None]:
        start_index_1 = start // FILE_INDEX_PER_BLOCK
        start_index_0 = start % FILE_INDEX_PER_BLOCK
        
        for index_1 in range(INODE_SMALL_THRESHOLD + start_index_1, INODE_LARGE_THRESHOLD):
            for index_0 in range(start_index_0, FILE_INDEX_PER_BLOCK):
                yield 0, index_1, index_0
            start_index_0 = 0

    def __next__
    

class Inode:
    """
    注意：
    需要手动flush
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
    
    def _get_s_inode_block(self, index: int) -> FileIndexBlock:
        return self._get_index_block(self.data.d_addr[index])
    
    def _get_index_list(self, block_index: int) -> list[int]:
        list = self._get_index_block(block_index).to_list()
        while list and list[-1] == 0:
            list.pop()
        return list
    
    def _get_block_list(self, start_block: int = 0) -> Generator[int, None, None]:
        """
        我们首先获取原始的混合索引表，
        根据列表的长度判断此文件是小型文件、大型文件，还是巨型文件。
        返回完整的文件块序号列表
        """        
        compressed_list: list[int] = self.data.d_addr.copy()
        while compressed_list and compressed_list[-1] == 0:  # 去掉末尾的0
            compressed_list.pop()
        
        # 直接索引块的序号
        if start_block <= FILE_INDEX_SMALL_THRESHOLD:
            for index_0 in compressed_list[start_block:INODE_SMALL_THRESHOLD]:
                yield index_0
            start_block = FILE_INDEX_SMALL_THRESHOLD
        
        # 解压一次直接索引块（如果有的话）
        if start_block <= FILE_INDEX_LARGE_THRESHOLD:
            start_block -= FILE_INDEX_SMALL_THRESHOLD
            start_index_1 = start_block // FILE_INDEX_PER_BLOCK
            start_index_0 = start_block % FILE_INDEX_PER_BLOCK
            
            for index_1 in compressed_list[INODE_SMALL_THRESHOLD + start_index_1 : INODE_LARGE_THRESHOLD]:
                for index_0 in self._get_index_list(index_1)[start_index_0:]:
                    yield index_0
                start_index_0 = 0
                
            start_block = FILE_INDEX_LARGE_THRESHOLD
            
        # 解压二次直接索引块（如果有的话）
        if start_block <= FILE_INDEX_HUGE_THRESHOLD:
            start_block -= FILE_INDEX_LARGE_THRESHOLD
            start_index_2 = start_block // (FILE_INDEX_PER_BLOCK ** 2)
            start_index_1 = (start_block % (FILE_INDEX_PER_BLOCK ** 2)) // FILE_INDEX_PER_BLOCK
            start_index_0 = start_block % FILE_INDEX_PER_BLOCK

            for index_2 in compressed_list[INODE_LARGE_THRESHOLD + start_index_2 : ]:
                for index_1 in self._get_index_list(index_2)[start_index_1:]:
                    for index_0 in self._get_index_list(index_1)[start_index_0:]:
                        yield index_0
                    start_index_0 = 0
                start_index_1 = 0

    
    def get_block_list(self, start_block: int = 0, len: int = -1) -> Generator[int, None, None]:
        """
        获取文件的块序号列表
        """
        for block_index in self._get_block_list(start_block):
            if len == 0:
                break
            yield block_index
            len -= 1
    
    def _new_data_block_index(self) -> int:
        return self.free_block_manager.allocate_block(zero=True)

    def _delete_data_block(self, index: int) -> None:
        self.free_block_manager.release_block(index)
    
    def push_block(self, index) -> None:
        """
        向索引列表中添加一个新的索引
        """
        insert_position: int = ceil(self.data.d_size / BLOCK_BYTES)

        # 小型文件
        if insert_position < FILE_INDEX_SMALL_THRESHOLD:
            self.data.d_addr[insert_position] = index
            return
        
        # 大型文件
        if FILE_INDEX_SMALL_THRESHOLD <= insert_position < FILE_INDEX_LARGE_THRESHOLD:
            index_big = insert_position - FILE_INDEX_SMALL_THRESHOLD
            index_1 = index_big // FILE_INDEX_PER_BLOCK
            index_0 = index_big % FILE_INDEX_PER_BLOCK

            # 是否应新增一级索引块
            if index_0 == 0:
                self.data.d_addr[index_1] = self._new_data_block_index()
            
            # 在计算出的位置设置索引
            index_block = self._get_s_inode_block(index_1)
            index_block[index_0] = index
            return
        
        # 巨型文件
        if FILE_INDEX_LARGE_THRESHOLD <= insert_position < FILE_INDEX_HUGE_THRESHOLD:
            index_huge = insert_position - FILE_INDEX_LARGE_THRESHOLD
            index_2 = index_huge // (FILE_INDEX_PER_BLOCK ** 2)
            index_1 = (index_huge % (FILE_INDEX_PER_BLOCK ** 2)) // FILE_INDEX_PER_BLOCK
            index_0 = index_huge % FILE_INDEX_PER_BLOCK
            
            # 是否应新增二级索引块
            if index_1 == 0 and index_0 == 0:
                self.data.d_addr[index_2] = self._new_data_block_index()
            # 是否应新增一级索引块
            if index_0 == 0:
                index_block_1 = self._get_s_inode_block(index_2)
                index_block_1[index_1] = self._new_data_block_index()
            
            # 在计算出的位置设置索引
            index_block_2 = self._get_s_inode_block(index_2)
            index_block_1 = index_block_2.subblock(index_1)
            index_block_1[index_0] = index
            return
        
        raise Exception("文件已达最大大小，无法增加索引块")
    
    def pop_block(self) -> None:
        pop_position: int = ceil(self.data.d_size / BLOCK_BYTES) - 1
        
        # 小型文件
        if 0 <= pop_position < FILE_INDEX_SMALL_THRESHOLD:
            self.data.d_addr[pop_position] = 0
            return
        
        # 大型文件
        if FILE_INDEX_SMALL_THRESHOLD <= pop_position < FILE_INDEX_LARGE_THRESHOLD:
            index_big = pop_position - FILE_INDEX_SMALL_THRESHOLD
            index_1 = index_big // FILE_INDEX_PER_BLOCK
            index_0 = index_big % FILE_INDEX_PER_BLOCK
            
            # 在计算出的位置清除索引
            block_1 = self._get_s_inode_block(index_1)
            block_1[index_0] = 0

            # 是否应删除一级索引块
            if index_0 == 0:
                self._delete_data_block(block_1.data_block_index)
                self.data.d_addr[index_1] = 0
            return
        
        # 巨型文件
        if FILE_INDEX_LARGE_THRESHOLD <= pop_position < FILE_INDEX_HUGE_THRESHOLD:
            index_huge = pop_position - FILE_INDEX_LARGE_THRESHOLD
            index_2 = index_huge // (FILE_INDEX_PER_BLOCK ** 2)
            index_1 = (index_huge % (FILE_INDEX_PER_BLOCK ** 2)) // FILE_INDEX_PER_BLOCK
            index_0 = index_huge % FILE_INDEX_PER_BLOCK
            
            # 在计算出的位置清除索引
            block_2 = self._get_s_inode_block(index_2)
            block_1 = block_2.subblock(index_1)
            block_1[index_0] = 0
            
            # 是否应删除一级索引块
            if index_0 == 0:
                self._delete_data_block(block_1.data_block_index)
                block_2[index_1] = 0
            # 是否应删除二级索引块
            if index_1 == 0:
                self._delete_data_block(block_2.data_block_index)
                self.data.d_addr[index_2] = 0
            return

        raise Exception("文件为空，无法删除索引块")

    def update_atime(self) -> None:
        self.data.d_atime = timestamp()
        
    def update_mtime(self) -> None:
        self.data.d_mtime = timestamp()
        