from block_device import CachedBlockDevice
import constants as C
import disk_params as DiskParams
from structures import *
from construct import Container
from lazy_array import LazyArray


class ObjectAccessor:
    """
    提供访问数据结构的接口，向已经实现缓存了的磁盘发出读写指令
    只负责单个对象的读写，不考虑多个对象之间的联系
    只要读取此对象的属性，即可访问磁盘中对应的对象
    修改此对象的属性，则会自动将更改写回磁盘
    """
    def __init__(self, block_device: CachedBlockDevice):
        self.block_device = block_device
    
    # 给下面读写数据块用的工厂方法
    def _create_lazy_proxy_array(self, parser, builder, item_type) -> LazyArray:
        def getter(index):
            # block_index = DATA_START + index
            block_index = index
            block_bytes = self.block_device.read_block(block_index)
            return parser(block_bytes)

        def setter(index, value) -> None:
            # block_index = DATA_START + index
            block_index = index
            block_bytes = builder(value)
            self.block_device.write_block(block_index, block_bytes)

        return LazyArray[item_type](DiskParams.DISK_BLOCKS, getter, setter)

    # 超级块的读写接口
    @property
    def superblock(self) -> Container:
        data = self.block_device.read_block_range(DiskParams.SUPERBLOCK_START, DiskParams.SUPERBLOCK_START + C.SUPERBLOCK_BLOCKS)
        return SuperBlockStruct.parse(data)
    
    @superblock.setter
    def superblock(self, value: Container):
        data = SuperBlockStruct.build(value)
        self.block_device.write_block_range(DiskParams.SUPERBLOCK_START, data)
    
    # inode的读写接口
    @property
    def inodes(self) -> LazyArray[Container]:
        """
        inode的读写接口。
        这个inodes本身是一个定长的数组，不能直接被修改，
        但是我们可以对inodes里面的元素进行访问和修改，
        所做的修改会自动保存至磁盘。
        注意：如果这个LazyArray的元素是一个列表，那修改这个元素列表并不会被保存，
        需要直接替换那个列表才行。
        """
        def getter(index) -> Container:
            block_index = DiskParams.INODE_START + index // C.INODE_PER_BLOCK
            inode_index = index % C.INODE_PER_BLOCK
            
            block_bytes = self.block_device.read_block(block_index)
            return InodeBlockStruct.parse(block_bytes)[inode_index]
        
        def setter(index, value: Container) -> None:
            block_index = DiskParams.INODE_START + index // C.INODE_PER_BLOCK
            inode_index = index % C.INODE_PER_BLOCK
            
            block_bytes = self.block_device.read_block(block_index)
            inode_block = InodeBlockStruct.parse(block_bytes)
            
            inode_block[inode_index] = value
            block_bytes = InodeBlockStruct.build(inode_block)
            self.block_device.write_block(block_index, block_bytes)
            
        return LazyArray[Container](DiskParams.INODE_COUNT, getter, setter)
    
    # 数据块分为文件数据块、目录数据块、文件索引块，以及空白块索引块
    # 文件数据块
    @property
    def file_blocks(self) -> LazyArray[bytes]:
        return self._create_lazy_proxy_array(lambda x: x, lambda x: x, bytes)
   
    # 目录数据块
    @property
    def dir_blocks(self) -> LazyArray[list[Container]]:
        parser = DirectoryBlockStruct.parse
        builder = DirectoryBlockStruct.build
        return self._create_lazy_proxy_array(parser, builder, list[Container])

    # 文件索引块
    @property
    def file_index_blocks(self) -> LazyArray[list[int]]:
        parser = FileIndexBlock.parse
        builder = FileIndexBlock.build
        return self._create_lazy_proxy_array(parser, builder, list[int])
    
    # 空白块索引块
    @property
    def free_index_blocks(self) -> LazyArray[Container]:
        parser = FreeBlockIndexBlock.parse
        builder = FreeBlockIndexBlock.build
        return self._create_lazy_proxy_array(parser, builder, Container)
    
    # 清空一个数据块
    def clear_data_block(self, block_index: int) -> None:
        self.block_device.write_block(block_index, b'\x00' * C.DATA_BLOCK_BYTES)
        