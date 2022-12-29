
from os import path

def dir_path(file_name: str) -> str:
    DIR_PATH = path.dirname(__file__)
    return path.join(DIR_PATH, file_name)
