from typing import Callable, TypeVar, Generic

BASIC_TYPES = (int, float, str, bytes)

class ObjectProxy():
    __slots__ = ["_obj", "_writeback"]
    
    def __init__(self, obj, writeback):
        self._obj = obj
        self._writeback = writeback

    def __getattr__(self, name):
        if name in self.__slots__:
            return object.__getattribute__(self, name)
        attr = getattr(self._obj, name)
        if isinstance(attr, BASIC_TYPES):  # 如果是基本类型，直接返回
            return attr
        return ObjectProxy(attr, self._writeback)  # 如果是对象，返回一个新的代理对象

    def __setattr__(self, name, value):
        if name in self.__slots__:
            return object.__setattr__(self, name, value)
        setattr(self._obj, name, value)
        self._writeback()
        
    def __getitem__(self, index):
        item = self._obj[index]
        if isinstance(item, BASIC_TYPES):  # 如果是基本类型，直接返回
            return item
        def writeback():
            self._obj[index] = item
        return ObjectProxy(item, writeback)
    
    def __setitem__(self, index, value):
        self._obj[index] = value
        self._writeback()
    

ItemType = TypeVar('ItemType')
class LazyProxyArray(Generic[ItemType]):
    def __init__(self, length: int, getter: Callable[[int], ItemType], setter: Callable[[int, ItemType], None]):
        self.length = length
        self.getter = getter
        self.setter = setter
        
    def __getitem__(self, index):
        assert 0 <= index < self.length
        item = self.getter(index)
        if isinstance(item, BASIC_TYPES):  # 如果是基本类型，直接返回
            return item
        
        def writeback():
            self.setter(index, item)
        return ObjectProxy(item, writeback)
    
    def __setitem__(self, index, value):
        assert 0 <= index < self.length
        if isinstance(value, ObjectProxy):
            value = value._obj
        self.setter(index, value)
        
    def __len__(self):
        return self.length
    
    def __iter__(self):
        for i in range(self.length):
            yield self[i]
