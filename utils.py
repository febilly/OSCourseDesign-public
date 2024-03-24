import constants as C
from time import time
from datetime import datetime

def timestamp() -> int:
    return int(time())

def timestr(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')

def get_disk_start(block: bytes):
    # 检查mbr的魔数
    if block[-2:] == b'\x55\xaa':
        return 200
    else:
        return 0
        