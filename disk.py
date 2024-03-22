from block_device import CachedBlockDevice
from constants import *
from object_accessor import ObjectAccessor
from superblock import Superblock
from inode import Inode, FILE_TYPE
import os
from file_index_block import FileIndexBlock
from free_block_interface import FreeBlockInterface
from dir_block import DirBlock

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
        
        dir_block_indexes = parent.get_block_list()
        for index in dir_block_indexes:
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
        dir_block_indexes = parent.get_block_list()
        for index in dir_block_indexes:
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
    
    def format(self):
        pass
        
    
    @property
    def inode_size(self) -> int:
        return self.superblock.data.s_isize
    
    @property
    def block_size(self) -> int:
        return self.superblock.data.s_fsize