from block_device import CachedBlockDevice
from constants import *
from object_accessor import ObjectAccessor
from superblock import Superblock
from inode import Inode, FILE_TYPE
import os
from file_index_block import FileIndexBlock
from free_block_interface import FreeBlockInterface
from dir_block import DirBlock
from math import ceil

class Disk:
    def __init__(self, path: str):
        self.path = path
        
    def mount(self):
        self.block_device = CachedBlockDevice(self.path)
        self.object_accessor = ObjectAccessor(self.block_device)
        self.superblock = Superblock(self.object_accessor.superblock, self.object_accessor)
        self.root_inode = Inode.from_index(INODE_ROOT_NO, self.object_accessor, self.superblock)
        
    def unmount(self):
        self.block_device.close()

    def _get_inode(self, path: str) -> Inode:
        if path == '/':
            return self.root_inode

        parent_path, name = os.path.split('/')
        parent = self._get_inode(parent_path)
        
        if name == '':
            return parent
        if parent.file_type != FILE_TYPE.DIR:
            raise FileNotFoundError(f"{path} is not a directory")
        
        for index in parent.block_list():
            dir_block = DirBlock.from_index(index, self.object_accessor)
            if name not in dir_block:
                continue
            inode_no = dir_block.find(name)
            return Inode.from_index(inode_no, self.object_accessor, self.superblock)
        
        raise FileNotFoundError(f"{path} is not a directory")
    
    def create_file(self, path: str) -> Inode:
        parent_path, name = os.path.split('/')
        if name == '':
            raise FileNotFoundError("File name is empty")
        
        # 创建新的文件的inode
        block_index = self.superblock.allocate_block()
        inode = Inode.new(block_index, FILE_TYPE.FILE, self.object_accessor, self.superblock)
        inode.flush()
        
        parent = self._get_inode(parent_path)

        # 如果父inode的文件索引里面还有空位，就直接添加到空位里
        for index in parent.block_list():
            dir_block = DirBlock.from_index(index, self.object_accessor)
            if dir_block.add(inode.index, name):
                return inode

        # 没有空位，因此我们新建一个目录块
        new_block_index = self.superblock.allocate_block()
        dir_block = DirBlock.new(new_block_index, self.object_accessor)
        dir_block.add(inode.index, name)
        dir_block.flush()
        
        parent.push_block(new_block_index)
        parent.flush()
        
        return inode
    
    def truncate(self, path: str, new_size: int) -> None:
        inode = self._get_inode(path)
        if inode.file_type != FILE_TYPE.FILE:
            raise FileNotFoundError(f"{path} is not a file")
        origin_blockcount = ceil(inode.size / BLOCK_BYTES)
        target_blockcount = ceil(new_size / BLOCK_BYTES)
        
        if target_blockcount < origin_blockcount:
            for _ in range(target_blockcount, origin_blockcount):
                inode.pop_block()                    
        elif target_blockcount > origin_blockcount:
            for _ in range(origin_blockcount, target_blockcount):
                block_index = self.superblock.allocate_block(zero=True)
                inode.push_block(block_index)
        
        # 进行块内的修剪
        # 修建的是truncate之后留下的最后一个块
        if new_size % BLOCK_BYTES != 0 and 0 < new_size < inode.size:
            last_block_position = new_size % BLOCK_BYTES
            last_block_index = inode.get_one_block(target_blockcount - 1)
            block_data = self.object_accessor.file_blocks[last_block_index]
            block_data = block_data[:last_block_position] + b"\x00" * (BLOCK_BYTES - last_block_position)
            self.object_accessor.file_blocks[last_block_index] = block_data
                
        inode.size = new_size
        inode.flush()
    
    def read_file(self, path: str, offset: int, size: int) -> bytes:
        assert size >= 0
        inode = self._get_inode(path)
        if inode.file_type != FILE_TYPE.FILE:
            raise FileNotFoundError(f"{path} is not a file")
        size = min(size, inode.size - offset)
        
        start_block_index = offset // BLOCK_BYTES
        position = offset % BLOCK_BYTES
        
        result = b""
        for index in inode.block_list(start_block_index):
            data = self.object_accessor.file_blocks[index][position : position + size]
            result += data
            position = 0
            size -= len(data)
            if size == 0:
                break
            
        return result
    
    def write_file(self, path: str, offset: int, data: bytes) -> None:
        inode = self._get_inode(path)
        start_block_index = offset // BLOCK_BYTES
        position = offset % BLOCK_BYTES
        bytes_written = 0
        
        if position > inode.size:  # 如果起始位置就已经超过文件大小了，那就先扩展文件到起始位置
            self.truncate(path, position)
        
        # 对现有的block进行覆写
        for index in inode.block_list(start_block_index):
            part_length = min(len(data), BLOCK_BYTES - position)
            bytes_written += part_length
            chunk, data = data[:part_length], data[part_length:]
            
            block_data = self.object_accessor.file_blocks[index]
            block_data = block_data[:position] + chunk + block_data[position + part_length:]
            self.object_accessor.file_blocks[index] = block_data
            
            if len(data) == 0:
                break
        
        # 原文件的最后一个块有可能原来没写满
        inode.size = max(inode.size, offset + bytes_written)

        # 如果新的数据比原来就有的还多，就要加新的block来写
        while (len(data) > 0):
            part_length = min(len(data), BLOCK_BYTES)
            chunk, data = data[:part_length], data[part_length:]
            chunk = chunk + b"\x00" * (BLOCK_BYTES - len(chunk))
            
            block_index = self.superblock.allocate_block()
            self.object_accessor.file_blocks[block_index] = chunk
            inode.push_block(block_index)
            
            inode.size += part_length

        inode.flush()

    
    def format(self):
        pass
    
    @property
    def inode_size(self) -> int:
        return self.superblock.data.s_isize
    
    @property
    def block_size(self) -> int:
        return self.superblock.data.s_fsize