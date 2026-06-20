from app.core.logger import logger

def read_file_from_path(tmp_path:str)->bytes:
    if not tmp_path:
        logger.erro(f"File Byte Embedding Failed -> No Temp Path found")
        return ""
        
    with open(tmp_path, "rb") as f:
        file_bytes = f.read()
        return file_bytes