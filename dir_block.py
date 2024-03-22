from constants import *
from construct import Container
from object_accessor import ObjectAccessor

class DirBlock:
    def __init__(self, dir_block_index: int, dirs: list[Container], object_accessor: ObjectAccessor):
        self.dir_block_index = dir_block_index
        self.dirs = dirs
        assert len(self.dirs) == DIRECTORY_PER_BLOCK
        self.object_accessor = object_accessor

    @classmethod
    def from_index(cls, index: int, object_accessor: ObjectAccessor):
        """
        通过块号构造索引对象
        """
        # dirs: list[Container] = object_accessor.dir_blocks[index]._obj
        dirs: list[Container] = object_accessor.dir_blocks[index]
        return cls(index, dirs, object_accessor)

    def __getitem__(self, index: int) -> Container:
        return self.dirs[index]

    def __setitem__(self, index: int, value: Container) -> None:
        self.dirs[index] = value
        self.flush()

    def __iter__(self):
        return iter(self.dirs)

    def flush(self) -> None:
        self.object_accessor.file_index_blocks[self.dir_block_index] = self.dirs
    
    def __contains__(self, item: str) -> bool:
        return any([dir.d_name == item for dir in self.dirs])
    
    def find(self, name: str) -> int:
        for index, dir in enumerate(self.dirs):
            if dir.d_name == name:
                return index
        return -1
    
    def is_empty(self) -> bool:
        return all([dir.d_ino == 0 for dir in self.dirs])
    
    def is_full(self) -> bool:
        return all([dir.d_ino != 0 for dir in self.dirs])
    
    def add(self, ino: int, name: str) -> bool:
        for index, dir in enumerate(self.dirs):
            if dir.d_ino == 0:
                self.dirs[index] = Container(d_ino=ino, d_name=name)
                self.flush()
                return True
        return False
    
    def remove(self, name: str) -> bool:
        index = self.find(name)
        if index == -1:
            return False
        self.dirs[index] = Container(d_ino=0, d_name="")
        self.flush()
        return True
    