from collections import OrderedDict
from typing import Callable
from constants import *
import os

class CacheBlock:
    def __init__(self, data: bytes, writer: Callable[[bytes], None]):
        self.dirty = False
        self.data = data
        self.writer = writer
        
    def read_full(self) -> bytes:
        return self.data
    
    def read_bytes(self, start: int, length: int) -> bytes:
        assert start + length <= BLOCK_SIZE, f"start: {start} + length: {length} > BLOCK_SIZE: {BLOCK_SIZE}"
        return self.data[start:start + length]
        
    def flush(self) -> None:
        if self.dirty:
            self.writer(self.data)
            self.dirty = False

    def modify_bytes(self, start: int, data: bytes) -> None:
        assert start + len(data) <= BLOCK_SIZE, f"start: {start} + len(data): {len(data)} > BLOCK_SIZE: {BLOCK_SIZE}"
        self.data = self.data[:start] + data + self.data[start + len(data):]
        if start + len(data) == BLOCK_SIZE:
            self.writer(self.data)
            self.dirty = False
        else:
            self.dirty = True
            
    def modify_full(self, data: bytes) -> None:
        return self.modify_bytes(0, data)

            
class LRUCache:
    def __init__(self, capacity: int):
        self.cache: OrderedDict[int, CacheBlock] = OrderedDict()
        self.capacity = capacity

    def get(self, block_number: int) -> CacheBlock:
        self.cache.move_to_end(block_number)
        return self.cache[block_number]
    
    def put(self, block_number, block: CacheBlock) -> None:
        if block_number in self.cache:
            self.cache.move_to_end(block_number)
        while len(self.cache) >= self.capacity:
            self.cache.popitem(last=False)
        self.cache[block_number] = block

    def __contains__(self, block_number: int) -> bool:
        return block_number in self.cache
    
    def flush_all(self) -> None:
        for block in self.cache.values():
            block.flush()


class BlockDevice:
    def __init__(self, path_to_image: str):
        self.path_to_image = path_to_image
        self.image_size = os.path.getsize(path_to_image)
        assert self.image_size % BLOCK_SIZE == 0
        self.image_file = open(path_to_image, "r+b")
        self.block_count = self.image_size // BLOCK_SIZE
        
    def read_block_full(self, block_number: int) -> bytes:
        self.image_file.seek(block_number * BLOCK_SIZE)
        return self.image_file.read(BLOCK_SIZE)
    
    def write_block(self, block_number: int, data: bytes) -> None:
        self.image_file.seek(block_number * BLOCK_SIZE)
        self.image_file.write(data)
        

class CachedBlockDevice(BlockDevice):
    def __init__(self, path_to_image: str):
        super().__init__(path_to_image)
        self.cache = LRUCache(LRU_CACHE_SIZE)
    
    def _generate_writer(self, block_number: int) -> Callable[[bytes], None]:
        def writer(data: bytes) -> None:
            self.write_block(block_number, data)
        return writer
    
    def read_block_bytes(self, block_number: int, start: int, length: int) -> bytes:
        if block_number in self.cache:
            return self.cache.get(block_number).read_bytes(start, length)
        data = super().read_block_full(block_number)
        block = CacheBlock(data, self._generate_writer(block_number))
        self.cache.put(block_number, block)
        return block.read_bytes(start, length)
    
    def read_block_full(self, block_number: int) -> bytes:
        return self.read_block_bytes(block_number, 0, BLOCK_SIZE)

    def write_block_bytes(self, block_number: int, start: int, data: bytes) -> None:
        if block_number in self.cache:
            block = self.cache.get(block_number)
            block.modify_bytes(start, data)
        else:
            block = CacheBlock(data, self._generate_writer(block_number))
            self.cache.put(block_number, block)
        
    def write_block_full(self, block_number: int, data: bytes) -> None:
        self.write_block_bytes(block_number, 0, data)
        
    def flush(self) -> None:
        self.cache.flush_all()
        
    def close(self) -> None:
        self.flush()
        self.image_file.close()
        