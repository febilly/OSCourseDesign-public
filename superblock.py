from object_accessor import ObjectAccessor
from construct import Container
import constants as C
import disk_info as DiskInfo
from free_block_interface import FreeBlockInterface
from utils import timestamp


class Superblock(FreeBlockInterface):
    def __init__(self, data: Container, object_accessor: ObjectAccessor, fill: bool = True):
        self.data = data
        self.object_accessor = object_accessor
        
        if not fill:
            return
        # 我也不知道为啥s_ninode会大于100......
        # 我读了superblock一看，s_ninode是六千多，人都给我看傻了
        if self.data.s_ninode > C.SUPERBLOCK_FREE_INODE or self.data.s_ninode <= 0:
            self.data.s_ninode = 0
            self._fill_inode()
        
    @classmethod
    def new(cls, object_accessor: ObjectAccessor):
        data = Container(
            s_isize = DiskInfo.INODE_BLOCK_SIZE,
            s_fsize = DiskInfo.DISK_BLOCK_SIZE,
            
            s_nfree = 0,
            s_free = [0] * C.SUPERBLOCK_FREE_BLOCK,
            s_flock = 0,
            
            s_ninode = 0,
            s_inode = [0] * C.SUPERBLOCK_FREE_INODE,
            s_ilock = 0,
            
            s_fmod = 0,
            s_ronly = 0,
            s_time = timestamp())
        object = cls(data, object_accessor, fill=False)
        object._fill_inode(1)
        return object
        
    def flush(self) -> None:
        self.object_accessor.superblock = self.data
    
    def allocate_block(self, zero=False) -> int:
        self.data.s_nfree -= 1
        index = self.data.s_free[self.data.s_nfree]
        
        # 如果superblock里的表已用完，那就将下一个空闲块索引块读入superblock
        if self.data.s_nfree == 0:
            if self.data.s_free[0] == 0:
                raise Exception("No free block")
            next_block = self.object_accessor.free_index_blocks[self.data.s_free[0]]
            self.data.s_nfree = next_block.s_nfree
            self.data.s_free = next_block.s_free
            
        if zero:  # 是否清零
            self.object_accessor.clear_data_block(index)
        
        # print(f"allocate block {index}")
        return index

    def release_block(self, block_index: int) -> None:
        if self.data.s_nfree < C.FREE_INDEX_PER_BLOCK:
            self.data.s_free[self.data.s_nfree] = block_index
            self.data.s_nfree += 1
        else:
            # 写入下一个空闲块索引块
            new_block = Container(s_nfree=self.data.s_nfree, s_free=self.data.s_free)
            self.object_accessor.free_index_blocks[block_index] = new_block

            self.data.s_nfree = 1
            self.data.s_free = [0] * C.FREE_INDEX_PER_BLOCK
            self.data.s_free[0] = block_index
            
        # print(f"release block {block_index}")
    
    def _fill_inode(self, start: int = 0) -> None:
        assert self.data.s_ninode == 0
        for index in range(start, DiskInfo.INODE_COUNT):
            if self.object_accessor.inodes[index].d_mode.IALLOC:
                continue
            self.data.s_inode[self.data.s_ninode] = index
            self.data.s_ninode += 1
            if self.data.s_ninode == C.SUPERBLOCK_FREE_INODE:
                break
                
    def allocate_inode(self) -> int:
        self.data.s_ninode -= 1
        index = self.data.s_inode[self.data.s_ninode]
    
        # 设置IALLOC位
        # inode = self.object_accessor.inodes[index]
        # inode.d_mode.IALLOC = 1
    
        # 如果用完了缓存的空白inode表，就一次性把它填充满
        if self.data.s_ninode == 0:
            self._fill_inode()
            
        return index
    
    def release_inode(self, inode_index: int) -> None:
        # 清除IALLOC位
        inode = self.object_accessor.inodes[inode_index]
        inode.d_mode.IALLOC = 0
        self.object_accessor.inodes[inode_index] = inode

        # 如果缓存的空白inode表没装满，就把这个空出来的inode塞进去 
        if self.data.s_ninode < C.INODE_PER_BLOCK:
            self.data.s_inode[self.data.s_ninode] = inode_index
            self.data.s_ninode += 1
        