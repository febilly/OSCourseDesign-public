from object_accessor import ObjectAccessor
from construct import Container
import constants as C
import disk_params as DiskParams
from free_block_interface import FreeBlockInterface
from utils import timestamp, get_superblock_hash
from structures import SuperBlockStruct
from utils import debug_print

class Superblock(FreeBlockInterface):
    def __init__(self, data: Container, object_accessor: ObjectAccessor, new: bool = True):
        self.data = data
        self.object_accessor = object_accessor

        # 计算hash，并根据是否是新建磁盘来决定是写入hash，还是校验hash        
        if new:  # 对新磁盘，初始化额外信息
            self._fill_inode()
            self.data.bfree = DiskParams.DATA_BLOCK_COUNT
            self.data.files = DiskParams.INODE_COUNT
            self.data.ffree = DiskParams.INODE_COUNT - 1
            self.flush()
            return
            
        # 对已有磁盘，校验hash
        encoded = SuperBlockStruct.build(self.data)
        hash = get_superblock_hash(encoded)
        if self.data.hash == hash:
            # 如果此磁盘上一次是用本程序读写的，那就不需要再计算空闲盘块数啥的了
            debug_print("找到附加信息。")
            return
        
        debug_print("未找到附加信息，将重新计算...")
        
        # 我也不知道为啥那个c.img里面s_ninode会大于100......
        # 我读了superblock一看，s_ninode是六千多，人都给我看傻了
        if self.data.s_ninode > C.SUPERBLOCK_FREE_INODE or self.data.s_ninode <= 0:
            self.data.s_ninode = 0
            self._fill_inode()
        
        self.recount()
        debug_print("重新计算完毕。")
        self.flush()
                
    def recount(self) -> None:
        # 计算空闲盘块数
        self.data.bfree = self.data.s_nfree
        index = self.data.s_free[0]
        while index != 0:
            self.data.bfree += self.object_accessor.free_index_blocks[index].s_nfree
            index = self.object_accessor.free_index_blocks[index].s_free[0]
        # 最后一个索引块的最后一项是0，并不是有效的空闲块，所以bfree要减去1
        self.data.bfree -= 1
        
        # 写入总inode数
        self.data.files = DiskParams.INODE_COUNT
        
        # 计算空闲inode数
        self.data.ffree = 0
        for i in range(1, DiskParams.INODE_COUNT):
            if not self.object_accessor.inodes[i].d_mode.IALLOC:
                self.data.ffree += 1
    
    
    @classmethod
    def new(cls, object_accessor: ObjectAccessor):
        data = Container(
            s_isize = DiskParams.INODE_BLOCKS,
            s_fsize = DiskParams.DISK_BLOCKS,
            
            s_nfree = 1,
            s_free = [0] * C.SUPERBLOCK_FREE_BLOCK,
            s_flock = 0,
            
            s_ninode = 0,
            s_inode = [0] * C.SUPERBLOCK_FREE_INODE,
            s_ilock = 0,
            
            s_fmod = 0,
            s_ronly = 0,
            s_time = timestamp(),
            
            bfree = 0,
            files = 0,
            ffree = 0,
            hash = 0,
            magic = 0,)
        object = cls(data, object_accessor, new=True)
        return object
        
    def flush(self) -> None:
        # 计算并写入hash
        encoded = SuperBlockStruct.build(self.data)
        hash = get_superblock_hash(encoded)
        self.data.hash = hash
        
        # 写入MAGIC
        self.data.magic = C.MAGIC
        
        self.object_accessor.superblock = self.data
    
    def allocate_block(self, zero=False) -> int:
        if self.data.s_nfree == 1 and self.data.s_free[0] == 0:
            raise Exception("No free block")
        
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
        
        # debug_print(f"allocate block {index}")
        self.data.bfree -= 1
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
            
        # debug_print(f"release block {block_index}")
        self.data.bfree += 1
    
    def _fill_inode(self) -> None:
        assert self.data.s_ninode == 0 or self.data.s_ninode == 1 and self.data.s_inode[0] == 0
        for index in range(1, DiskParams.INODE_COUNT):
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
        
        self.data.ffree -= 1
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
        
        self.data.ffree += 1
        