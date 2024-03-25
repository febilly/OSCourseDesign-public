import constants as C
import disk_info as DiskInfo
from block_device import CachedBlockDevice
from object_accessor import ObjectAccessor
from superblock import Superblock
from inode import Inode, FILE_TYPE
from utils import timestamp

def format_disk(path: str, init_params: bool = False):
    if init_params:
        DiskInfo.init_constants()
    
    # 对磁盘低格
    with open(path, 'wb') as f:
        f.write(b'\x00' * DiskInfo.TOTAL_BYTES)
        
    disk = CachedBlockDevice(path)
    accessor = ObjectAccessor(disk)
    superblock = Superblock.new(accessor)
    
    for i in range(DiskInfo.DATA_START, DiskInfo.DISK_BLOCK_SIZE):
        superblock.release_block(i)
        
    root_inode = Inode.new(C.INODE_ROOT_NO, FILE_TYPE.DIR, accessor, superblock)
    
    superblock.flush()
    root_inode.flush()
    disk.close()
    