from typing import Any
from superblock import Superblock
from object_accessor import ObjectAccessor
from abc import ABC, abstractmethod

class FreeBlockInterface(ABC):
    @abstractmethod
    def allocate_block(self, zero=False) -> int:
        pass
    
    def allocate_block_n(self, n: int, zero=False) -> list[int]:
        return [self.allocate_block(zero) for _ in range(n)]

    @abstractmethod
    def release_block(self, block_index: int) -> None:
        pass

    def release_block_all(self, block_indexes: list[int]) -> None:
        for index in block_indexes:
            self.release_block(index)
            