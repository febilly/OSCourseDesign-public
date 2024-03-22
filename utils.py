from constants import *
from time import time
from datetime import datetime

def get_data_block_index(block_number: int) -> int:
    return DATA_START + block_number

def timestamp() -> int:
    return int(time())

def timestr(timestamp: int) -> str:
    return datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')