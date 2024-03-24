from block_device import CachedBlockDevice
from constants import *
from object_accessor import ObjectAccessor
from superblock import Superblock
from inode import Inode, FILE_TYPE
import os
from dir_block import DirBlock
from math import ceil
from file import File

class Disk:
    def __init__(self, path: str):
        self.path = path
        self.opened_files: dict[int, File] = {}
        self.path_to_handle: dict[str, int] = {}
        self.handle_to_path: dict[int, str] = {}
        self.new_handle = 1
        
    def _get_inode(self, path: str) -> Inode:
        if path == '/':
            return self.root_inode

        parent_path, name = os.path.split(path)
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
        
        raise FileNotFoundError(f"{path} not found")

    def open(self, path: str) -> int:
        if path in self.path_to_handle:
            return self.path_to_handle[path]
        
        handle = self.new_handle
        self.new_handle += 1

        inode = self._get_inode(path)
        file = File(path, inode)
        self.opened_files[handle] = file
        self.path_to_handle[path] = handle
        self.handle_to_path[handle] = path
        return handle
        
    def mount(self):
        self.block_device = CachedBlockDevice(self.path)
        self.object_accessor = ObjectAccessor(self.block_device)
        self.superblock = Superblock(self.object_accessor.superblock, self.object_accessor)
        self.root_inode = Inode.from_index(INODE_ROOT_NO, self.object_accessor, self.superblock)
        
    def flush(self):
        self.superblock.flush()
        self.root_inode.flush()
        self.block_device.flush()
    
    def unmount(self):
        self.block_device.close()
    
    def create_file(self, path: str, type: FILE_TYPE) -> Inode:
        parent_path, name = os.path.split(path)
        if name == '':
            raise FileNotFoundError("File name is empty")
        
        # 创建新的文件（夹）的inode
        inode_index = self.superblock.allocate_inode()
        inode = Inode.new(inode_index, type, self.object_accessor, self.superblock)
        inode.data.d_nlink = 1
        inode.flush()
        
        parent = self._get_inode(parent_path)

        position = 0
        # 如果父inode的文件索引里面还有空位，就直接添加到空位里
        for index in parent.block_list():
            dir_block = DirBlock.from_index(index, self.object_accessor)
            if dir_block.add(inode.index, name):
                supposed_size = position + dir_block.length() * DIRECTORY_BYTES
                if supposed_size > parent.size:
                    parent.size = supposed_size
                    parent.flush()
                return inode
            position += DATA_BLOCK_BYTES

        # 没有空位，因此我们新建一个目录块
        new_block_index = self.superblock.allocate_block()
        dir_block = DirBlock.new(new_block_index, self.object_accessor)
        dir_block.add(inode.index, name)
        
        parent.push_block(new_block_index)
        parent.size += DIRECTORY_BYTES
        parent.flush()
        
        return inode
    
    def remove_file(self, path: str) -> None:
        if path in self.path_to_handle:
            handle = self.path_to_handle[path]
            self.opened_files.pop(handle)
            self.path_to_handle.pop(path)
            self.handle_to_path.pop(handle)
        
        parent_path, name = os.path.split(path)
        if name == '':
            raise FileNotFoundError("File name is empty")

        parent = self._get_inode(parent_path)
        
        for index in parent.block_list():
            dir_block = DirBlock.from_index(index, self.object_accessor)
            if name not in dir_block:
                continue
            inode_no = dir_block.find(name)
            dir_block.remove(name)
            inode = Inode.from_index(inode_no, self.object_accessor, self.superblock)
            
            inode.data.d_nlink -= 1
            if inode.data.d_nlink == 0:
                self.superblock.release_inode(inode_no)
                dir_block.remove(name)
            else:
                inode.flush()
                
            # 检查是否要移除多余的DirBlock
            # 好像unix v6++ 里面没有干这个事？那我也不搞了算了
            
            return
        
        raise FileNotFoundError(f"{path} not found")
    
    def truncate(self, handle: int, new_size: int) -> None:
        if handle not in self.opened_files:
            raise FileNotFoundError(f"File handle {handle} not found")
        
        inode = self.opened_files[handle].inode
        if inode.file_type != FILE_TYPE.FILE:
            raise FileNotFoundError(f"{self.handle_to_path[handle]} is not a file")
        
        target_blockcount = ceil(new_size / BLOCK_BYTES)
        while inode.block_count < target_blockcount:
            block_index = self.superblock.allocate_block(zero=True)
            inode.push_block(block_index)
        while inode.block_count > target_blockcount:
            block_index = inode.pop_block()
            self.superblock.release_block(block_index)
        
        # 进行块内的修剪
        # 修建的是truncate之后留下的最后一个块
        if new_size % BLOCK_BYTES != 0 and 0 < new_size < inode.size:
            last_block_position = new_size % BLOCK_BYTES
            last_block_index = inode.peek_block(target_blockcount - 1)
            block_data = self.object_accessor.file_blocks[last_block_index]
            block_data = block_data[:last_block_position] + b"\x00" * (BLOCK_BYTES - last_block_position)
            self.object_accessor.file_blocks[last_block_index] = block_data
                
        inode.size = new_size
        inode.flush()
    
    def read_file(self, handle: int, offset: int, size: int) -> bytes:
        if handle not in self.opened_files:
            raise FileNotFoundError(f"File handle {handle} not found")
        
        inode = self.opened_files[handle].inode
        if inode.file_type != FILE_TYPE.FILE:
            raise FileNotFoundError(f"{self.handle_to_path[handle]} is not a file")

        offset = max(offset, 0)
        if size < 0:
            size = inode.size - offset
        else:
            size = min(size, inode.size - offset)
        
        if inode.file_type != FILE_TYPE.FILE:
            raise FileNotFoundError(f"{path} is not a file")
        
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
    
    def write_file(self, handle: int, offset: int, data: bytes) -> None:
        if handle not in self.opened_files:
            raise FileNotFoundError(f"File handle {handle} not found")
        
        inode = self.opened_files[handle].inode
        if inode.file_type != FILE_TYPE.FILE:
            raise FileNotFoundError(f"{self.handle_to_path[handle]} is not a file")

        if offset < 0:
            offset = inode.size
        
        start_block_index = offset // BLOCK_BYTES
        position = offset % BLOCK_BYTES
        target_size = offset + len(data)
        
        if position > inode.size:  # 如果起始位置就已经超过文件大小了，那就先扩展文件到起始位置
            self.truncate(path, position)
        
        # 对现有的block进行覆写
        for index in inode.block_list(start_block_index):
            part_length = min(len(data), BLOCK_BYTES - position)
            chunk, data = data[:part_length], data[part_length:]
            
            block_data = self.object_accessor.file_blocks[index]
            block_data = block_data[:position] + chunk + block_data[position + part_length:]
            self.object_accessor.file_blocks[index] = block_data
            
            if len(data) == 0:
                break
        
        # 如果新的数据比原来就有的还多，就要加新的block来写
        while (len(data) > 0):
            part_length = min(len(data), BLOCK_BYTES)
            chunk, data = data[:part_length], data[part_length:]
            chunk = chunk + b"\x00" * (BLOCK_BYTES - len(chunk))
            
            block_index = self.superblock.allocate_block()
            self.object_accessor.file_blocks[block_index] = chunk
            inode.push_block(block_index)
            
        inode.size = max(inode.size, target_size)
        inode.flush()

    
    def format(self):
        pass
    
    @property
    def inode_size(self) -> int:
        return self.superblock.data.s_isize
    
    @property
    def block_size(self) -> int:
        return self.superblock.data.s_fsize