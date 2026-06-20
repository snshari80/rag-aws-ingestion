from pathlib import Path
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import ( PyMuPDFLoader, Docx2txtLoader )
from app.core.logger import logger
from app.core.config import SUPPORTED_EXTENSIONS
import re
from app.utils.util import (read_file_from_path)
from bs4 import BeautifulSoup

class DocumentParser:
    def __init__(self):
        self.text_spliter = RecursiveCharacterTextSplitter(
            chunk_size = 200,
            chunk_overlap=50,
            separators = ["\n\n","\n",". ","?","!"," "]
        )
        logger.info(f"Step[2/4] Chunking the temp file")
    
    def parse(self,tmp_path:str)->list[str]:
        ext = Path(tmp_path).suffix.lower()
        if ext not in SUPPORTED_EXTENSIONS:
            logger.error(f"Unsupported File extension:{ext}")
        logger.info(f"Step[2/4] Extracting temp file to chunks")
        logger.info(f"Documentx Extraction available:{ext}")

        raw_text = self._extract_text(tmp_path,ext)
        
        if not raw_text:
            logger.error(f"Could not extract text from document: {tmp_path}")
            return []

        chunks = self.text_spliter.split_text(raw_text)
        return chunks


    def _extract_text(self,tmp_path:str, ext:str):
        if ext.lstrip(".") == "docx":
            return self._extract_docx(tmp_path)
        elif ext.lstrip(".") == "pdf":
            return self._extract_pdf(tmp_path)
        elif ext.lstrip(".") == "html":
            return self._extract_html(tmp_path)
        else:
            raise ValueError("No extractor for this ext:{file_ext}")
        
    def _extract_html(self,tmp_path:str):
        logger.info(f"Documentx Extraction started:{tmp_path}")
        try:
            file_bytes = read_file_from_path(tmp_path=tmp_path)
            html_str = file_bytes.decode("utf-8",errors="replace")
            soup = BeautifulSoup(html_str,"html.parser")
            
            text = soup.get_text(
                separator="\n",
                strip=True
            )
            return text
        
        except Exception as e:
            logger.error(f"DOCX extraction failed:{e}")
            return ""

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
            return ""

    def _extract_pdf(self,tmp_path:str):
        logger.info(f"Document Extraction Started:{tmp_path}")
        try:
            loader = PyMuPDFLoader(tmp_path)
            docs = loader.load()
            text = "\n\n".join(doc.page_content for doc in docs)
            final_text = self._clean_text(text)
            return final_text
        except Exception as e:
            logger.error(f"PDF extraction failed:{e}")
            return ""

    def _clean_text(self,text:str):
        text = re.sub(r"\n+","\n" ,text)
        text = re.sub(r"\t+", " ",text)
        return text.strip()