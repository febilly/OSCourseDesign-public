from block_device import CachedBlockDevice
import constants as C
import disk_params as DiskParams
from object_accessor import ObjectAccessor
from superblock import Superblock
from inode import Inode, FILE_TYPE
import os
from dir_block import DirBlock
from math import ceil
from utils import get_disk_start, get_disk_params, debug_print
from format_disk import format_disk
from dataclasses import dataclass
import os, errno
import stat
import time

@dataclass
class DiskStats:
    f_bsize: int
    f_frsize: int
    f_blocks: int
    f_bfree: int
    f_bavail: int
    f_files: int
    f_ffree: int
    f_favail: int
    f_flag: int
    f_namemax: int
    
    def items(self):
        return self.__dict__.items()

@dataclass
class FileStats():
    st_mode: int
    st_ino: int
    st_dev: int
    st_nlink: int
    st_uid: int
    st_gid: int
    st_size: int
    st_atime: int
    st_mtime: int
    st_ctime: int

    def items(self):
        return self.__dict__.items()

    def __repr__(self):
        return f"FileStats(st_mode={self.st_mode}, st_ino={self.st_ino}, st_dev={self.st_dev}, st_nlink={self.st_nlink}, st_uid={self.st_uid}, st_gid={self.st_gid}, st_size={self.st_size}, st_atime={self.st_atime}, st_mtime={self.st_mtime}, st_ctime={self.st_ctime})"

class Disk:
    def __init__(self, path: str):
        self.path = path
        self.mounted = False
    
    def get_stats(self) -> DiskStats:
        debug_print(f"Disk.get_stats()")
        return DiskStats(
            f_bsize=C.BLOCK_BYTES,
            f_frsize=C.BLOCK_BYTES,
            f_blocks=DiskParams.DISK_BLOCKS,
            f_bfree=self.superblock.data.bfree,
            f_bavail=self.superblock.data.bfree,
            f_files=DiskParams.INODE_COUNT,
            f_ffree=self.superblock.data.ffree,
            f_favail=self.superblock.data.ffree,
            f_flag=os.ST_NOSUID,
            f_namemax=27
        )
    
    @classmethod
    def new(cls, path: str):
        debug_print(f"Disk.new({path})")
        format_disk(path, init_params=True)
        disk = cls(path)
        return disk
    
    def mount(self):
        debug_print(f"Disk.mount()")
        print('加载磁盘中...')
        if self.mounted:
            return
        
        self.block_device = CachedBlockDevice(self.path)
        
        boot_block = self.block_device.read_block(0)
        disk_start = get_disk_start(boot_block)
        
        superblock_bytes = self.block_device.read_block_range(disk_start, disk_start + 2)
        inode_block_size, disk_block_size = get_disk_params(superblock_bytes)
        
        DiskParams.init_constants(disk_start, inode_block_size, disk_block_size)
        
        self.object_accessor = ObjectAccessor(self.block_device)
        self.superblock = Superblock(self.object_accessor.superblock, self.object_accessor, new=False)
        self.root_inode = Inode.from_index(C.INODE_ROOT_NO, self.object_accessor, self.superblock)
        
        self.mounted = True
        print('磁盘挂载成功')
        
    def flush(self):
        debug_print(f"Disk.flush()")
        self.superblock.flush()
        self.root_inode.flush()
        self.block_device.flush()
    
    def unmount(self):
        debug_print(f"Disk.unmount()")
        if not self.mounted:
            return
        self.flush()
        self.block_device.close()
        self.mounted = False

    def _get_inode(self, path: str) -> Inode:
        debug_print(f"Disk._get_inode({path})")
        if path == '/':
            return self.root_inode

        parent_path, name = os.path.split(path)
        parent = self._get_inode(parent_path)
        
        if name == '':
            return parent
        if parent.file_type != FILE_TYPE.DIR:
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path)
        
        for index in parent.block_list():
            dir_block = DirBlock.from_index(index, self.object_accessor)
            if name not in dir_block:
                continue
            inode_no = dir_block.find_inode(name)
            return Inode.from_index(inode_no, self.object_accessor, self.superblock)
        
        raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path)
    
    def get_attr(self, path: str) -> FileStats:
        debug_print(f"Disk.get_attr({path})")
        inode = self._get_inode(path)
        st_mode = 0
        if inode.file_type == FILE_TYPE.DIR:
            st_mode |= stat.S_IFDIR
        elif inode.file_type == FILE_TYPE.FILE:
            st_mode |= stat.S_IFREG
        elif inode.file_type == FILE_TYPE.BLOCK_DEVICE:
            st_mode |= stat.S_IFBLK
        elif inode.file_type == FILE_TYPE.CHAR_DEVICE:
            st_mode |= stat.S_IFCHR
        st_mode |= 0o777
        return FileStats(
            st_mode=st_mode,
            st_ino=inode.index,
            st_dev=0,
            st_nlink=inode.data.d_nlink,
            st_uid=inode.data.d_uid,
            st_gid=inode.data.d_gid,
            st_size=inode.size,
            st_atime=inode.data.d_atime,
            st_mtime=inode.data.d_mtime,
            st_ctime=inode.data.d_mtime
        )
    
    def _add_to_dir(self, parent: Inode, name: str, inode: Inode) -> None:
        debug_print(f"Disk._add_to_dir({parent.index}, {name}, {inode.index})")
        position = 0
        # 如果父inode的文件索引里面还有空位，就直接添加到空位里
        for index in parent.block_list():
            dir_block = DirBlock.from_index(index, self.object_accessor)
            if dir_block.add(inode.index, name):
                supposed_size = position + dir_block.length() * C.DIRECTORY_BYTES
                if supposed_size > parent.size:
                    parent.size = supposed_size
                    parent.flush()
                return
            position += C.DATA_BLOCK_BYTES

        # 没有空位，因此我们新建一个目录块
        new_block_index = self.superblock.allocate_block()
        dir_block = DirBlock.new(new_block_index, self.object_accessor)
        dir_block.add(inode.index, name)
        
        parent.push_block(new_block_index)
        parent.size += C.DIRECTORY_BYTES
        parent.flush()

    def dir_list(self, path: str) -> list[str]:
        debug_print(f"Disk.dir_list({path})")
        inode = self._get_inode(path)
        if inode.file_type != FILE_TYPE.DIR:
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path)
        
        result = []
        for index in inode.block_list():
            dir_block = DirBlock.from_index(index, self.object_accessor)
            result += dir_block.list()
        
        return result
    
    def exists(self, path: str) -> bool:
        debug_print(f"Disk.exists({path})")
        try:
            self._get_inode(path)
        except FileNotFoundError:
            return False
        return True
    
    def create(self, path: str, type: FILE_TYPE) -> Inode:
        debug_print(f"Disk.create({path}, {type})")
        if self.exists(path):
            raise FileExistsError(f"{path} already exists")

        parent_path, name = os.path.split(path)
        if name == '':
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path)
        
        # 创建新的文件（夹）的inode
        inode_index = self.superblock.allocate_inode()
        inode = Inode.new(inode_index, type, self.object_accessor, self.superblock)
        inode.data.d_nlink = 1
        inode.flush()
        
        # 添加到父文件夹里
        parent = self._get_inode(parent_path)
        self._add_to_dir(parent, name, inode)
        
        return inode
    
    def unlink(self, path: str) -> None:
        debug_print(f"Disk.unlink({path})")
        inode = self._get_inode(path)
        inode.data.d_nlink -= 1
        
        # 只有硬连接数归零了才删除文件
        if inode.data.d_nlink == 0:
            # 释放inode的所有数据块
            for i in inode.block_list():
                self.superblock.release_block(i)
            self.superblock.release_inode(inode.index)
            # 如果path是文件夹，那还要移除所有子文件
            if inode.file_type == FILE_TYPE.DIR:
                for name in self.dir_list(path):
                    self.unlink(os.path.join(path, name))
        else:
            inode.flush()

        parent_path, name = os.path.split(path)
        parent = self._get_inode(parent_path)
        
        # 删除文件夹里对此文件的引用
        for index in parent.block_list():
            dir_block = DirBlock.from_index(index, self.object_accessor)
            if name not in dir_block:
                continue
            dir_block.remove(name)
            return

    def link(self, src: str, dst: str) -> None:
        debug_print(f"Disk.link({src}, {dst})")
        inode = self._get_inode(src)
        if self.exists(dst):
            raise FileExistsError(f"{dst} already exists")
        
        parent_path, name = os.path.split(dst)
        parent = self._get_inode(parent_path)
        
        # 添加到父文件夹里
        parent = self._get_inode(parent_path)
        self._add_to_dir(parent, name, inode)

    def rename(self, src: str, dst: str) -> None:
        debug_print(f"Disk.rename({src}, {dst})")
        self.link(src, dst)
        self.unlink(src)

    def truncate(self, path: str, new_size: int) -> None:
        debug_print(f"Disk.truncate({path}, {new_size})")
        inode = self._get_inode(path)
        if inode.file_type != FILE_TYPE.FILE:
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path)
        
        target_blockcount = ceil(new_size / C.BLOCK_BYTES)
        while inode.block_count < target_blockcount:
            block_index = self.superblock.allocate_block(zero=True)
            inode.push_block(block_index)
        while inode.block_count > target_blockcount:
            block_index = inode.pop_block()
            self.superblock.release_block(block_index)
        
        # 进行块内的修剪
        # 修建的是truncate之后留下的最后一个块
        if new_size % C.BLOCK_BYTES != 0 and 0 < new_size < inode.size:
            last_block_position = new_size % C.BLOCK_BYTES
            last_block_index = inode.peek_block(target_blockcount - 1)
            block_data = self.object_accessor.file_blocks[last_block_index]
            block_data = block_data[:last_block_position] + b"\x00" * (C.BLOCK_BYTES - last_block_position)
            self.object_accessor.file_blocks[last_block_index] = block_data
                
        inode.size = new_size
        inode.flush()
    
    def read_file(self, path: str, offset: int, size: int) -> bytes:
        debug_print(f"Disk.read_file({path}, {offset}, {size})")
        inode = self._get_inode(path)
        offset = max(offset, 0)
        if size < 0:
            size = inode.size - offset
        else:
            size = min(size, inode.size - offset)
        
        if inode.file_type != FILE_TYPE.FILE:
            raise FileNotFoundError(errno.ENOENT, os.strerror(errno.ENOENT), path)
        
        start_block_index = offset // C.BLOCK_BYTES
        position = offset % C.BLOCK_BYTES
        
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
        debug_print(f"Disk.write_file({path}, {offset}, (data omitted for performance reason) )")
        inode = self._get_inode(path)
        if offset < 0:
            offset = inode.size
        
        start_block_index = offset // C.BLOCK_BYTES
        position = offset % C.BLOCK_BYTES
        target_size = offset + len(data)
        
        if position > inode.size:  # 如果起始位置就已经超过文件大小了，那就先扩展文件到起始位置
            self.truncate(path, position)
        
        # 对现有的block进行覆写
        for index in inode.block_list(start_block_index):
            part_length = min(len(data), C.BLOCK_BYTES - position)
            chunk, data = data[:part_length], data[part_length:]
            
            block_data = self.object_accessor.file_blocks[index]
            block_data = block_data[:position] + chunk + block_data[position + part_length:]
            self.object_accessor.file_blocks[index] = block_data
            
            if len(data) == 0:
                break
        
        # 如果新的数据比原来就有的还多，就要加新的block来写
        while (len(data) > 0):
            part_length = min(len(data), C.BLOCK_BYTES)
            chunk, data = data[:part_length], data[part_length:]
            chunk = chunk + b"\x00" * (C.BLOCK_BYTES - len(chunk))
            
            block_index = self.superblock.allocate_block()
            self.object_accessor.file_blocks[block_index] = chunk
            inode.push_block(block_index)
            
        inode.size = max(inode.size, target_size)
        inode.flush()

    def modify_timestamp(self, path: str, atime: int = -1, mtime: int = -1) -> None:
        debug_print(f"Disk.modify_timestamp({path}, {atime}, {mtime})")
        inode = self._get_inode(path)
        if atime >= 0:
            inode.data.d_atime = atime
        if mtime >= 0:
            inode.data.d_mtime = mtime
        inode.flush()
    
    def update_time(self, path: str) -> None:
        debug_print(f"Disk.update_time({path})")
        inode = self._get_inode(path)
    
    def format(self):
        debug_print(f"Disk.format()")
        mounted = self.mounted
        if mounted:
            self.unmount()
        format_disk(self.path)
        if mounted:
            self.mount()
    
    @property
    def inode_size(self) -> int:
        return self.superblock.data.s_isize
    
    @property
    def block_size(self) -> int:
        return self.superblock.data.s_fsize