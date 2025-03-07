import constants as C
from object_accessor import ObjectAccessor

class FileIndexBlock:
    def __init__(self, block_index: int, indexes: list[int], object_accessor: ObjectAccessor):
        self.block_index = block_index
        self.indexes = indexes
        assert len(self.indexes) == C.FILE_INDEX_PER_BLOCK
        self.object_accessor = object_accessor

    @classmethod
    def from_index(cls, index: int, object_accessor: ObjectAccessor):
        """
        通过块号构造索引对象
        """
        # index_data: list[int] = object_accessor.file_index_blocks[index]._obj
        index_data: list[int] = object_accessor.file_index_blocks[index]
        return cls(index, index_data, object_accessor)
        
    def __getitem__(self, index: int) -> int:
        return self.indexes[index]

    def __setitem__(self, index: int, value: int) -> None:
        self.indexes[index] = value
        self.flush()

    def flush(self) -> None:
        self.object_accessor.file_index_blocks[self.block_index] = self.indexes        
 
    def to_list(self) -> list[int]:
        return self.indexes.copy()
    
    def subblock(self, index: int) -> 'FileIndexBlock':
        return FileIndexBlock.from_index(self[index], self.object_accessor)