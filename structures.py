from construct import Int16ub, Struct, Int32ub, Array, Bytes, Padding, Union, Flag, BitsInteger

# 超级块
SuperBlockStruct = Struct(
    "s_isize" / Int32ub,
    "s_fsize" / Int32ub,
    
    "s_nfree" / Int32ub,
    "s_free" / Int32ub[100],
    "s_flock" / Int32ub,
    
    "s_ninode" / Int32ub,
    "s_inode" / Int32ub[100],
    "s_ilock" / Int32ub,
    
    "s_fmod" / Int32ub,
    "s_ronly" / Int32ub,
    "s_time" / Int32ub,
    Padding(4 * 27),  # 填充到1024字节
)

InodeMode = Struct(
    Padding(16),
    "IALLOC" / Flag,
    "IFMT" / BitsInteger(2),
    "ILARG" / Flag,
    "ISUID" / Flag,
    "ISGID" / Flag,
    "ISVTX" / Flag,
    "IREAD" / Flag,
    "IWRITE" / Flag,
    "IEXEC" / Flag,
    "IREAD2" / Flag,
    "IWRITE2" / Flag,
    "IEXEC2" / Flag,
    "IREAD3" / Flag,
    "IWRITE3" / Flag,
    "IEXEC3" / Flag,
)

# inode
InodeStruct = Struct(
    "d_mode" / InodeMode,
    "d_nlink" / Int32ub,
    "d_uid" / Int16ub,
    "d_gid" / Int16ub,
    
    "d_size" / Int32ub,
    "d_addr" / Int32ub[10],
    
    "d_atime" / Int32ub,
    "d_mtime" / Int32ub,
)

# 普通文件数据块
FileBlockStruct = Struct(
    "data" / Bytes(512),
)

# 目录文件数据块
DirectoryBlockStruct = Struct(
    "data" / Array(16, Struct(
        "d_ino" / Int32ub,
        "d_name" / Bytes(12),
    )),
)

# 空闲块索引块
FreeBlockIndexBlock = Struct(
    "s_nfree" / Int32ub,
    "s_free" / Array(100, Int32ub),
)

# 文件索引块
FileIndexBlock = Struct(
    "d_addr" / Array(128, Int32ub),
)

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
