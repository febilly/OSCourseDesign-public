from disk import Disk

class DiskWithHandle(Disk):
    def __init__(self, path: str):
        super().__init__(path)
        self.handle_to_path: dict[int, str] = {}
        self.path_to_handle: dict[str, int] = {}
        self.new_handle = 1

    def open(self, path: str) -> int:
        if path in self.path_to_handle:
            return self.path_to_handle[path]
        
        handle = self.new_handle
        self.new_handle += 1

        self.handle_to_path[handle] = path
        self.path_to_handle[path] = handle
        return handle
    
    def remove_file(self, path: str) -> None:
        if path in self.path_to_handle:
            handle = self.path_to_handle[path]
            self.handle_to_path.pop(handle)
            self.path_to_handle.pop(path)
        super().remove_file(path)
            
    def truncate(self, handle: int, new_size: int) -> None:
        if handle not in self.handle_to_path:
            raise FileNotFoundError(f"File handle {handle} not found")
        super().truncate(self.handle_to_path[handle], new_size)
    
    def read_file(self, handle: int, offset: int, size: int) -> bytes:
        if handle not in self.handle_to_path:
            raise FileNotFoundError(f"File handle {handle} not found")
        return super().read_file(self.handle_to_path[handle], offset, size)
    
    def write_file(self, handle: int, offset: int, data: bytes) -> None:
        if handle not in self.handle_to_path:
            raise FileNotFoundError(f"File handle {handle} not found")
        super().write_file(self.handle_to_path[handle], offset, data)
        
    def format(self):
        self.handle_to_path.clear()
        self.path_to_handle.clear()
        super().format()
    