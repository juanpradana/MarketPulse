import os
import logging
from tqdm import tqdm
from modules.database import DatabaseManager

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CHROMA_PATH = os.path.join(BASE_DIR, "chroma_db")
COLLECTION_NAME = "idx_rag"
LLM_MODEL = "qwen2.5:7b"
EMBED_MODEL = "nomic-embed-text:latest"

# Setup Logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def _check_ollama_available():
    """Check if Ollama server is reachable."""
    try:
        import urllib.request
        req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


class IDXProcessor:
    def __init__(self):
        self.base_dir = BASE_DIR
        self.chroma_path = CHROMA_PATH
        self.db = DatabaseManager()
        
        # Lazy-initialized components
        self._embeddings = None
        self._llm = None
        self._vector_store = None
        self._text_splitter = None
        self._fallback_splitter = None
        self._ollama_available = None
    
    @property
    def ollama_available(self):
        """Check Ollama availability (cached per instance)."""
        if self._ollama_available is None:
            self._ollama_available = _check_ollama_available()
            if not self._ollama_available:
                logger.warning("Ollama is not available. AI summarization will be skipped.")
        return self._ollama_available
    
    @property
    def embeddings(self):
        """Lazy-initialize Ollama embeddings."""
        if self._embeddings is None and self.ollama_available:
            try:
                from langchain_ollama import OllamaEmbeddings
                self._embeddings = OllamaEmbeddings(model=EMBED_MODEL)
            except Exception as e:
                logger.error(f"Failed to initialize embeddings: {e}")
                self._ollama_available = False
        return self._embeddings
    
    @property
    def llm(self):
        """Lazy-initialize Ollama LLM."""
        if self._llm is None and self.ollama_available:
            try:
                from langchain_ollama import ChatOllama
                self._llm = ChatOllama(model=LLM_MODEL, temperature=0)
            except Exception as e:
                logger.error(f"Failed to initialize LLM: {e}")
                self._ollama_available = False
        return self._llm
    
    @property
    def vector_store(self):
        """Lazy-initialize Chroma vector store."""
        if self._vector_store is None and self.embeddings is not None:
            try:
                from langchain_chroma import Chroma
                self._vector_store = Chroma(
                    collection_name=COLLECTION_NAME,
                    embedding_function=self.embeddings,
                    persist_directory=self.chroma_path
                )
            except Exception as e:
                logger.error(f"Failed to initialize vector store: {e}")
        return self._vector_store
    
    @property
    def text_splitter(self):
        """Lazy-initialize SemanticChunker with fallback."""
        if self._text_splitter is None:
            if self.embeddings is not None:
                try:
                    from langchain_experimental.text_splitter import SemanticChunker
                    self._text_splitter = SemanticChunker(
                        self.embeddings,
                        breakpoint_threshold_type="percentile"
                    )
                except Exception as e:
                    logger.warning(f"SemanticChunker failed, using fallback: {e}")
                    self._text_splitter = self._get_fallback_splitter()
            else:
                self._text_splitter = self._get_fallback_splitter()
        return self._text_splitter
    
    def _get_fallback_splitter(self):
        """Get a simple text splitter that doesn't require Ollama."""
        if self._fallback_splitter is None:
            try:
                from langchain_text_splitters import RecursiveCharacterTextSplitter
            except ImportError:
                from langchain.text_splitter import RecursiveCharacterTextSplitter
            self._fallback_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=200,
                separators=["\n\n", "\n", ". ", " ", ""]
            )
        return self._fallback_splitter

    def _resolve_path(self, local_path):
        """Resolve a potentially relative path to an absolute one."""
        if not local_path or not local_path.strip():
            return None
        
        local_path = local_path.strip()
        
        # Already absolute and exists
        if os.path.isabs(local_path) and os.path.exists(local_path):
            return local_path
        
        # Try relative to BASE_DIR
        candidates = [
            local_path,
            os.path.join(self.base_dir, local_path),
            os.path.join(self.base_dir, "downloads", os.path.basename(local_path)),
        ]
        
        for candidate in candidates:
            if os.path.exists(candidate) and os.path.getsize(candidate) > 0:
                return os.path.abspath(candidate)
        
        return None

    def _extract_text_from_pdf(self, file_path):
        """Extract text from PDF with multiple fallback methods."""
        # Method 1: PyPDFLoader (LangChain)
        try:
            from langchain_community.document_loaders import PyPDFLoader
            loader = PyPDFLoader(file_path)
            pages = loader.load()
            if pages and any(p.page_content.strip() for p in pages):
                return pages
        except Exception as e:
            logger.warning(f"PyPDFLoader failed for {file_path}: {e}")
        
        # Method 2: Direct pypdf
        try:
            from pypdf import PdfReader
            from langchain_core.documents import Document
            
            reader = PdfReader(file_path)
            pages = []
            for i, page in enumerate(reader.pages):
                text = page.extract_text() or ""
                if text.strip():
                    pages.append(Document(
                        page_content=text,
                        metadata={"source": file_path, "page": i}
                    ))
            if pages:
                return pages
        except Exception as e:
            logger.warning(f"pypdf fallback failed for {file_path}: {e}")
        
        return None

    def summarize(self, chunks, title=""):
        """Generate AI summary with timeout and fallback."""
        if not self.llm:
            # No LLM available - generate basic summary from title
            return self._basic_summary(chunks, title)
        
        try:
            from langchain_core.prompts import ChatPromptTemplate
            from langchain_core.output_parsers import StrOutputParser
            
            # Take first 3 chunks (max ~3000 chars to keep it fast)
            context_text = "\n\n".join([c.page_content[:1000] for c in chunks[:3]])
            
            prompt = ChatPromptTemplate.from_template("""
            Anda adalah asisten AI yang ahli dalam menganalisis laporan keterbukaan informasi perusahaan.
            Tugas Anda adalah meringkas teks di bawah ini menjadi 1 kalimat singkat dalam Bahasa Indonesia.
            Fokus pada peristiwa inti (Dividen, Laba, Rugi, Pengunduran Diri, RUPS, dll).
            Jika ini hanya laporan rutin biasa, katakan 'Laporan Rutin'.

            Teks:
            {context}

            Ringkasan (Bahasa Indonesia):
            """)
            
            chain = prompt | self.llm | StrOutputParser()
            summary = chain.invoke({"context": context_text})
            return summary.strip()
        except Exception as e:
            logger.warning(f"LLM summarization failed: {e}")
            return self._basic_summary(chunks, title)
    
    def _basic_summary(self, chunks, title=""):
        """Generate a basic summary without AI when Ollama is unavailable."""
        if title and title != "No Title":
            return title
        if chunks:
            # Use first 200 chars of first chunk
            preview = chunks[0].page_content[:200].strip()
            if preview:
                return preview + "..."
        return "Dokumen keterbukaan informasi"

    def process_document(self, doc_id, local_path, ticker, title=""):
        """Process a single document: extract text, chunk, embed, summarize."""
        try:
            resolved_path = self._resolve_path(local_path)
            
            if not resolved_path:
                logger.error(f"File not found for doc {doc_id}: {local_path}")
                self.db.disclosure_repo.update_status(doc_id, 'FAILED')
                return False

            # Extract text from PDF
            pages = self._extract_text_from_pdf(resolved_path)
            
            if not pages:
                logger.warning(f"No text extracted from {resolved_path} (possibly scanned/image PDF)")
                # Still mark as completed with basic summary from title
                summary = title if title and title != "No Title" else "Dokumen tidak dapat diekstrak (PDF gambar)"
                self.db.disclosure_repo.update_status(doc_id, 'COMPLETED', summary)
                return True

            # Split into chunks
            try:
                chunks = self.text_splitter.split_documents(pages)
            except Exception as e:
                logger.warning(f"Text splitter failed, using fallback: {e}")
                chunks = self._get_fallback_splitter().split_documents(pages)
            
            if not chunks:
                summary = title if title and title != "No Title" else "Dokumen kosong"
                self.db.disclosure_repo.update_status(doc_id, 'COMPLETED', summary)
                return True

            # Add Metadata
            for i, chunk in enumerate(chunks):
                chunk.metadata['source_id'] = doc_id
                chunk.metadata['ticker'] = ticker or ""
                chunk.metadata['chunk_index'] = i

            # Add to Vector Store (only if available)
            if self.vector_store:
                try:
                    doc_unique_id = f"doc_{doc_id}"
                    chunk_ids = [f"{doc_unique_id}_{i}" for i in range(len(chunks))]
                    self.vector_store.add_documents(documents=chunks, ids=chunk_ids)
                except Exception as e:
                    logger.warning(f"Failed to add to vector store for doc {doc_id}: {e}")

            # Summarize
            summary = self.summarize(chunks, title)
            
            # Update DB
            self.db.disclosure_repo.update_status(doc_id, 'COMPLETED', summary)
            return True

        except Exception as e:
            logger.exception(f"Error processing document {doc_id}: {str(e)}")
            self.db.disclosure_repo.update_status(doc_id, 'FAILED')
            return False

    def run_processor(self):
        """Process all pending disclosures."""
        records = self.db.disclosure_repo.get_pending_disclosures()
        if not records:
            logger.info("No pending disclosures found.")
            return {"processed": 0, "success": 0, "failed": 0}

        logger.info(f"Found {len(records)} pending disclosures.")
        
        if self.ollama_available:
            logger.info("Ollama is available - full AI processing enabled.")
        else:
            logger.info("Ollama not available - using basic text extraction only.")
        
        result = {"processed": 0, "success": 0, "failed": 0}
        
        for record in tqdm(records, desc="Processing PDFs"):
            doc_id, local_path, ticker = record[0], record[1], record[2]
            title = record[3] if len(record) > 3 else ""
            
            success = self.process_document(doc_id, local_path, ticker, title)
            result["processed"] += 1
            if success:
                result["success"] += 1
            else:
                result["failed"] += 1
        
        logger.info(f"Processing complete: {result['success']}/{result['processed']} succeeded, {result['failed']} failed")
        return result


if __name__ == "__main__":
    processor = IDXProcessor()
    processor.run_processor()
