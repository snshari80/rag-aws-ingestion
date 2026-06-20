import logging
import sys

def setup_logger():
    logger = logging.getLogger("RAG_APP")

    if logger.handlers:
        return logger
    
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler(sys.stdout)

    format = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    handler.setFormatter(format)
    logger.addHandler(handler)

    return logger


logger = setup_logger()
