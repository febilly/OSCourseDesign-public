import constants as C
from time import time
from datetime import datetime
import hashlib
from structures import SuperBlockStruct
from construct import Container

def timestamp() -> int:
    return int(time())

def timestr(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def get_disk_start(block: bytes) -> int:
    # 检查mbr的魔数
    if block[-2:] == b'\x55\xaa':
        return 200
    else:
        return 0

def get_disk_params(data: bytes) -> tuple[int, int]:
    superblock = SuperBlockStruct.parse(data)
    inode_block_size = superblock.s_isize
    disk_block_size = superblock.s_fsize
    return inode_block_size, disk_block_size
    
def bytes_or(b1: bytes, b2: bytes) -> bytes:
    return bytes(b1[i] | b2[i] for i in range(len(b1)))

def get_superblock_hash(superblock: bytes) -> bytes:
    data = superblock[:C.SUPERBLOCK_BYTES - 16]
    hash = hashlib.sha256(data).digest()
    return bytes_or(hash[:8], C.MAGIC)

