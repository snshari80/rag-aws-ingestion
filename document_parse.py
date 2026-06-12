import io
from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import ( PyMuPDFLoader, Docx2txtLoader )
import logging
from config import SUPPORTED_EXTENSIONS
import re

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


class DocumentParser:
    def __init__(self):
        self.text_spliter = RecursiveCharacterTextSplitter(
            chunk_size = 200,
            chunk_overlap=50,
            separators = ["\n\n","\n",". ","?","!"," "]
        )
        logger.info(f"Step[2/4] Chunking the temp file")
    
    def parse(self,tmp_path:str, file_size:str, last_modified:str)->list[str]:
        ext = Path(tmp_path).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            logger.error(f"Unsupported File extension:{ext}")
        logger.info(f"Step[2/4] Extracting temp file to chunks")
        logger.info(f"Documentx Extraction available:{ext}")

        raw_text = self._extract_text(tmp_path,ext)
        
        if not raw_text:
            logger.error(f"Could be able to chunk the docment{tmp_path}")

        chunks = self.text_spliter.split_text(raw_text)
        return chunks


    def _extract_text(self,tmp_path:str, ext:str):
        if ext.lstrip(".") == "docx":
            return self._extract_docx(tmp_path)
        else:
            raise ValueError("No extractor for this ext:{file_ext}")
    
    def _extract_docx(self,tmp_path:str):
        logger.info(f"Documentx Extraction started:{tmp_path}")
        try:
            loader = Docx2txtLoader(tmp_path)
            docs = loader.load()
            text = "\n\n".join(doc.page_content for doc in docs)
            final_text = self._clean_text(text)
            return final_text
        except Exception as e:
            logger.error(f"DOCX extraction failed:{e}")

    def _clean_text(self,text:str):
        text = re.sub(r"\n+","\n" ,text)
        text = re.sub(r"\t+", " ",text)
        return text.strip()