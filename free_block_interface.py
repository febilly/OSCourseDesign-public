from typing import Any
from superblock import Superblock
from object_accessor import ObjectAccessor
from abc import ABC, abstractmethod

class FreeBlockInterface(ABC):
    @abstractmethod
    def allocate(self) -> int:
        pass
    
    def allocate_n(self, n: int) -> list[int]:
        return [self.allocate() for _ in range(n)]

    @abstractmethod
    def deallocate(self, block_index: int) -> None:
        pass

    def deallocate_all(self, block_indexes: list[int]) -> None:
        for index in block_indexes:
            self.deallocate(index)
            