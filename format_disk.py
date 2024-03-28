import constants as C
import disk_params as DiskParams
from block_device import CachedBlockDevice
from object_accessor import ObjectAccessor
from superblock import Superblock
from inode import Inode, FILE_TYPE

def format_disk(path: str, init_params: bool = False):
    if init_params:
        DiskParams.init_constants()
    
    # 对磁盘低格
    with open(path, 'wb') as f:
        f.write(b'\x00' * DiskParams.TOTAL_BYTES)
        
    disk = CachedBlockDevice(path)
    accessor = ObjectAccessor(disk)
    superblock = Superblock.new(accessor)
    root_inode = Inode.new(C.INODE_ROOT_NO, FILE_TYPE.DIR, accessor, superblock)
    
    superblock.flush()
    root_inode.flush()
    disk.close()
    