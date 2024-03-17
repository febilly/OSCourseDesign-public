from construct import Int16ub, Struct, Int32ub, Array, Bytes, Padding, Union

# 超级块
SuperBlock = Struct(
    "s_isize" / Int32ub,
    "s_fsize" / Int32ub,
    
    "s_nfree" / Int32ub,
    "s_free" / Array(100, Int32ub),
    "s_flock" / Int32ub,
    
    "s_ninode" / Int32ub,
    "s_inode" / Array(100, Int32ub),
    "s_ilock" / Int32ub,
    
    "s_fmod" / Int32ub,
    "s_ronly" / Int32ub,
    "s_time" / Int32ub,
    Padding(4 * 27),  # 填充到1024字节
)

# inode
Inode = Struct(
    "d_mode" / Int32ub,
    "d_nlink" / Int32ub,
    "d_uid" / Int16ub,
    "d_gid" / Int16ub,
    
    "d_size" / Int32ub,
    "d_addr" / Array(10, Int32ub),
    
    "d_atime" / Int32ub,
    "d_mtime" / Int32ub,
)

# 普通文件数据块
FileBlock = Struct(
    "data" / Bytes(512),
)

# 目录文件数据块
DirectoryBlock = Struct(
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
    "data" / FileBlock,
    "directory" / DirectoryBlock,
    "free_block_index" / FreeBlockIndexBlock,
    "file_index" / FileIndexBlock,
)

# 定义磁盘映像文件的数据结构
DiskImage = Struct(
    "superblock" / SuperBlock,
    "inodes" / Array(lambda ctx: ctx.superblock.s_isize, Inode),
    "disk_blocks" / Array(lambda ctx: ctx.superblock.s_fsize - ctx.superblock.s_isize - 2, DiskBlock),
)
