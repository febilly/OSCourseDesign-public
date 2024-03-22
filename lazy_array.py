from typing import Callable, TypeVar, Generic

ItemType = TypeVar('ItemType')
class LazyArray(Generic[ItemType]):
    def __init__(self, length: int, getter: Callable[[int], ItemType], setter: Callable[[int, ItemType], None]):
        self.length = length
        self.getter = getter
        self.setter = setter
        
    def __getitem__(self, index):
        assert 0 <= index < self.length
        item = self.getter(index)
        return item
    
    def __setitem__(self, index, value):
        assert 0 <= index < self.length
        self.setter(index, value)
        
    def __len__(self):
        return self.length
    
    def __iter__(self):
        for i in range(self.length):
            yield self[i]
