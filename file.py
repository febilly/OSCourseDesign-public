from inode import Inode

class File:
    def __init__(self, path: str):
        self.path = path
        self.offset = 0
        
class OpenedFiles:
    def __init__(self) -> None:
        self.files: dict[int, File] = {}
        self.new_handle = 1

    def clear(self) -> None:
        self.files.clear()
        self.new_handle = 1

    def add(self, file: File) -> int:
        handle = self.new_handle
        self.files[handle] = file
        self.new_handle += 1
        return handle
    
    def get(self, handle: int) -> File:
        if handle not in self.files:
            raise FileNotFoundError(f"File handle {handle} not found")
        return self.files[handle]
    
    def find(self, path: str) -> int:
        for handle, file in self.files.items():
            if file.path == path:
                return handle
        raise FileNotFoundError(f"File {path} not found")
    
    def pop(self, item: int | str) -> None:
        if isinstance(item, int):
            self.files.pop(item)
        else:
            handle = self.find(item)
            self.files.pop(handle)
        
    def __contains__(self, wanted: int | str) -> bool:
        if isinstance(wanted, int):
            return wanted in self.files
        for file in self.files.values():
            if file.path == wanted:
                return True
        return False
    