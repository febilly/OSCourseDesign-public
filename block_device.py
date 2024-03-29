from collections import OrderedDict
from typing import Callable, TypeVar, Generic
import constants as C
import os

class CacheBlock:
    """
    一个缓存块，记录了一个块的数据，以及一个写回函数（内含块的地址）
    同时会跟踪这个块是否被修改过
    当写到块尾时，会进行写回，并重置dirty标志
    """
    def __init__(self, data: bytes, writer: Callable[[bytes], None], dirty):
        self.data = data
        self.writer = writer
        self.dirty = dirty
        
        if self.dirty:
            self.flush()

    def read_full(self) -> bytes:
        return self.data
    
    def read_bytes(self, start: int, length: int) -> bytes:
        assert start + length <= C.BLOCK_BYTES, f"start: {start} + length: {length} > BLOCK_SIZE: {C.BLOCK_BYTES}"
        return self.data[start:start + length]
        
    def flush(self) -> None:
        if self.dirty:
            self.writer(self.data)
            self.dirty = False

    def modify_bytes(self, start: int, data: bytes) -> None:
        assert start + len(data) <= C.BLOCK_BYTES, f"start: {start} + len(data): {len(data)} > BLOCK_SIZE: {C.BLOCK_BYTES}"
        self.data = self.data[:start] + data + self.data[start + len(data):]
        self.dirty = True
            
    def modify_full(self, data: bytes) -> None:
        return self.modify_bytes(0, data)

ItemType = TypeVar('ItemType')
class LRUCache(Generic[ItemType]):
    """
    一个通用的LRU缓存
    """
    def __init__(self, capacity: int):
        self.cache: OrderedDict[int, ItemType] = OrderedDict()
        self.capacity = capacity

    def get(self, index: int) -> ItemType:
        self.cache.move_to_end(index)
        return self.cache[index]
    
    def put(self, index: int, item: ItemType) -> ItemType | None:
        if index in self.cache:
            self.cache.move_to_end(index)
        self.cache[index] = item
        if len(self.cache) > self.capacity:
            return self.cache.popitem(last=False)[1]
        return None

    def __contains__(self, index: int) -> bool:
        return index in self.cache
    
    def perform_on_all(self, method_name: str) -> None:
        for item in self.cache.values():
            getattr(item, method_name)()


class BlockDevice:
    def __init__(self, path_to_image: str):
        self.path_to_image = path_to_image
        self.image_size = os.path.getsize(path_to_image)
        assert self.image_size % C.BLOCK_BYTES == 0
        self.image_file = open(path_to_image, "r+b")
        self.block_count = self.image_size // C.BLOCK_BYTES
        
    def read_block(self, block_number: int) -> bytes:
        self.image_file.seek(block_number * C.BLOCK_BYTES)
        return self.image_file.read(C.BLOCK_BYTES)
    
    def write_block(self, block_number: int, data: bytes) -> None:
        self.image_file.seek(block_number * C.BLOCK_BYTES)
        self.image_file.write(data)
        
    def close(self) -> None:
        self.image_file.close()

class CachedBlockDevice(BlockDevice):
    def __init__(self, path_to_image: str):
        super().__init__(path_to_image)
        self.cache = LRUCache[CacheBlock](C.LRU_CACHE_LENGTH)
    
    def _generate_writer(self, block_number: int) -> Callable[[bytes], None]:
        parent = super()
        def writer(data: bytes) -> None:
            parent.write_block(block_number, data)
        return writer
    
    def read_block_bytes(self, block_number: int, start: int, length: int) -> bytes:
        if block_number in self.cache:
            return self.cache.get(block_number).read_bytes(start, length)
        data = super().read_block(block_number)
        block = CacheBlock(data, self._generate_writer(block_number), False)
        if popped_block := self.cache.put(block_number, block):
            popped_block.flush()
        return block.read_bytes(start, length)

    def read_block(self, block_number: int) -> bytes:
        return self.read_block_bytes(block_number, 0, C.BLOCK_BYTES)

    def read_block_range(self, start: int, end: int) -> bytes:
        """
        左闭右开，从0开始
        """
        result = b""
        for i in range(start, end):
            result += self.read_block(i)
        return result

    def write_block_bytes(self, block_number: int, start: int, data: bytes) -> None:
        if block_number in self.cache:
            block = self.cache.get(block_number)
            block.modify_bytes(start, data)
        else:
            if len(data) < C.BLOCK_BYTES:
                block_data = super().read_block(block_number)
                data = block_data[:start] + data + block_data[start + len(data):]
            block = CacheBlock(data, self._generate_writer(block_number), True)
            if popped_block := self.cache.put(block_number, block):
                popped_block.flush()
        
    def write_block(self, block_number: int, data: bytes) -> None:
        self.write_block_bytes(block_number, 0, data)
        
    def write_block_range(self, start: int, data: bytes) -> None:
        """
        左闭右开，从0开始
        data的长度必须是BLOCK_SIZE的整数倍
        """
        assert len(data) % C.BLOCK_BYTES == 0
        data_chunks = [data[i : i + C.BLOCK_BYTES] for i in range(0, len(data), C.BLOCK_BYTES)]
        for i, chunk in enumerate(data_chunks):
            self.write_block(start + i, chunk)
            
    def flush(self) -> None:
        self.cache.perform_on_all('flush')
        
    def close(self) -> None:
        self.flush()
        super().close()
    