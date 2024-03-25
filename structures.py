from construct import BitStruct, Int16ul, Struct, Int32ul, Array, Bytes, Padding, Union, Flag, BitsInteger, PaddedString
import constants as C

# 超级块
SuperBlockStruct = Struct(
    "s_isize" / Int32ul,
    "s_fsize" / Int32ul,
    
    "s_nfree" / Int32ul,
    "s_free" / Int32ul[100],
    "s_flock" / Int32ul,
    
    "s_ninode" / Int32ul,
    "s_inode" / Int32ul[100],
    "s_ilock" / Int32ul,
    
    "s_fmod" / Int32ul,
    "s_ronly" / Int32ul,
    "s_time" / Int32ul,
    Padding(4 * 40),  # 填充到1024字节
    
    "bfree" / Int32ul,
    "files" / Int32ul,
    "ffree" / Int32ul,
    "hash" / Bytes(8),
    "magic" / Bytes(8),
)
assert SuperBlockStruct.sizeof() == C.SUPERBLOCK_BYTES

InodeMode = BitStruct(
    "IWRITE" / Flag,
    "IEXEC" / Flag,
    "IREAD2" / Flag,
    "IWRITE2" / Flag,
    "IEXEC2" / Flag,
    "IREAD3" / Flag,
    "IWRITE3" / Flag,
    "IEXEC3" / Flag,
    "IALLOC" / Flag,
    "IFMT" / BitsInteger(2),
    "ILARG" / Flag,
    "ISUID" / Flag,
    "ISGID" / Flag,
    "ISVTX" / Flag,
    "IREAD" / Flag,
    Padding(16),
)
assert InodeMode.sizeof() == 4

# inode
InodeStruct = Struct(
    "d_mode" / InodeMode,
    "d_nlink" / Int32ul,
    "d_uid" / Int16ul,
    "d_gid" / Int16ul,
    
    "d_size" / Int32ul,
    "d_addr" / Int32ul[10],
    
    "d_atime" / Int32ul,
    "d_mtime" / Int32ul,
)
assert InodeStruct.sizeof() == C.INODE_BYTES

InodeBlockStruct = Array(8, InodeStruct)
assert InodeBlockStruct.sizeof() == C.BLOCK_BYTES

# 普通文件数据块
FileBlockStruct = Struct(
    "data" / Bytes(C.DATA_BLOCK_BYTES),
)
assert FileBlockStruct.sizeof() == C.DATA_BLOCK_BYTES

# 目录文件数据块
DirectoryStruct = Struct(
    "m_ino" / Int32ul,
    "m_name" / PaddedString(28, "utf8"),
)
assert DirectoryStruct.sizeof() == 32

DirectoryBlockStruct = Array(16, DirectoryStruct)
assert DirectoryBlockStruct.sizeof() == C.DATA_BLOCK_BYTES

# 空闲块索引块
FreeBlockIndexBlock = Struct(
    "s_nfree" / Int32ul,
    "s_free" / Array(100, Int32ul),
    Padding(4 * 27),  # 填充到512字节
)
assert FreeBlockIndexBlock.sizeof() == C.BLOCK_BYTES

# 文件索引块
FileIndexBlock = Array(128, Int32ul)
assert FileIndexBlock.sizeof() == C.BLOCK_BYTES

# 一个盘块
DiskBlock = Union(
    None,
    "data" / FileBlockStruct,
    "directory" / DirectoryBlockStruct,
    "free_block_index" / FreeBlockIndexBlock,
    "file_index" / FileIndexBlock,
)

# 定义磁盘映像文件的数据结构
DiskImage = Struct(
    "superblock" / SuperBlockStruct,
    "inodes" / Array(lambda ctx: ctx.superblock.s_isize, InodeStruct),
    "disk_blocks" / Array(lambda ctx: ctx.superblock.s_fsize - ctx.superblock.s_isize - 2, DiskBlock),
)
