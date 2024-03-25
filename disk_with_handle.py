from disk import Disk
from file import File, OpenedFiles

class DiskWithHandle(Disk):
    def __init__(self, path: str):
        super().__init__(path)
        self.files = OpenedFiles()
        self.new_handle = 1

    def open(self, path: str) -> int:
        if path in self.files:
            return self.files.find(path)
        file = File(path)
        return self.files.add(file)
    
    def close(self, handle: int) -> None:
        if handle not in self.files:
            raise FileNotFoundError(f"File handle {handle} not found")
        self.files.pop(handle)

    def seek(self, handle: int, offset: int) -> None:
        file = self.files.get(handle)
        file.offset = offset

    def dir_list(self, handle: int) -> list[str]:
        file = self.files.get(handle)
        return super().dir_list(file.path)

    def unlink(self, path: str) -> None:
        if path in self.files:
            self.files.pop(path)
        super().unlink(path)
            
    def truncate(self, handle: int, new_size: int) -> None:
        file = self.files.get(handle)
        file.offset = min(file.offset, new_size)
        super().truncate(file.path, new_size)
    
    def read_file(self, handle: int, size: int) -> bytes:
        file = self.files.get(handle)
        result = super().read_file(file.path, file.offset, size)
        file.offset += len(result)
        return result
    
    def write_file(self, handle: int, data: bytes) -> None:
        file = self.files.get(handle)
        file.offset += len(data)
        super().write_file(file.path, file.offset, data)
        
    def format(self):
        self.files.clear()
        super().format()
    