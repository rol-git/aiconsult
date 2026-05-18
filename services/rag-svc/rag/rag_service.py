"""
RAG-сервис на базе LlamaIndex поверх pgvector.

Документы парсятся, нарезаются на чанки и складываются в pgvector-таблицу.
Сам поиск идёт через VectorIndexRetriever, который под капотом дёргает pgvector.
"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from llama_index.core import (
    Document,
    Settings,
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
)
from llama_index.core.node_parser import SimpleNodeParser
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.postgres import PGVectorStore
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import ProgrammingError

from config import Config


logger = logging.getLogger(__name__)


DOCUMENT_NAMES = {
    "68-ФЗ.odt": "Федеральный закон № 68-ФЗ «О защите населения от ЧС»",
    "Методика 631.pdf": "Методика оценки ущерба № 631",
    "Порядок ТО.pdf": "Порядок предоставления помощи в Тюменской области",
    "ПП 1327.odt": "Постановление Правительства РФ № 1327",
    "ПП 1928.odt": "Постановление Правительства РФ № 1928",
    "ПП 304.odt": "Постановление Правительства РФ № 304",
    "ПП 794.odt": "Постановление Правительства РФ № 794",
}


def get_document_title(filename: str) -> str:
    """Преобразует имя файла в читаемое название документа."""
    return DOCUMENT_NAMES.get(filename, filename.rsplit(".", 1)[0] if "." in filename else filename)


@dataclass
class RAGChunk:
    """Фрагмент документа, возвращаемый RAG."""

    document: str
    location: str
    text: str
    score: float


class ODTReader:
    """ODT-reader, который безопасно извлекает текст без внешних DTD."""

    _NAMESPACES = {
        "office": "urn:oasis:names:tc:opendocument:xmlns:office:1.0",
        "text": "urn:oasis:names:tc:opendocument:xmlns:text:1.0",
    }

    def _extract_paragraphs(self, xml_bytes: bytes) -> List[str]:
        root = ET.fromstring(xml_bytes)
        office_text = root.find("office:body/office:text", self._NAMESPACES)
        if office_text is None:
            return []
        paragraphs: List[str] = []
        for paragraph in office_text.findall(".//text:p", self._NAMESPACES):
            text_content = "".join(paragraph.itertext()).strip()
            if text_content:
                paragraphs.append(text_content)
        return paragraphs

    def load_data(self, file: Path, extra_info: Optional[dict] = None) -> List[Document]:
        try:
            with zipfile.ZipFile(file, "r") as archive:
                xml_bytes = archive.read("content.xml")
        except KeyError as exc:
            logger.error("Не удалось прочитать content.xml в ODT %s: %s", file, exc)
            return []

        paragraphs = self._extract_paragraphs(xml_bytes)
        text_content = "\n".join(paragraphs).strip()
        if not text_content:
            logger.warning("ODT файл пустой или не содержит текста: %s", file)
            return []

        metadata = extra_info or {}
        metadata.update(
            {
                "source": file.name,
                "file_name": file.name,
                "source_path": str(file),
            }
        )
        return [Document(text=text_content, metadata=metadata)]


class RAGService:
    """Управляет построением и использованием векторного индекса документов в pgvector."""

    def __init__(self, config: Config):
        self.config = config
        self._index: Optional[VectorStoreIndex] = None
        self._retriever = None
        self._embed_model = HuggingFaceEmbedding(model_name=self.config.embedding_model_name)
        self._configure_settings()
        self._db_url: URL = make_url(self.config.database_url)
        self._engine = create_engine(self._db_url, future=True, pool_pre_ping=True)
        self._vector_store: Optional[PGVectorStore] = None

    def _configure_settings(self) -> None:
        Settings.llm = None
        Settings.embed_model = self._embed_model

    def ensure_ready(self) -> None:
        """Гарантирует, что индекс готов к выдаче чанков."""
        if self._index is not None and self._retriever is not None:
            return
        vector_store = self._get_vector_store()
        if self._has_data():
            self._load_index(vector_store)
        else:
            self._build_index(vector_store)

    def rebuild(self) -> None:
        """Полностью пересобирает индекс, очищая данные в pgvector."""
        self._drop_table()
        self._vector_store = None
        self._index = None
        self._retriever = None
        self._build_index(self._get_vector_store())

    def retrieve(self, query: str, *, agent_hint: Optional[str] = None) -> List[RAGChunk]:
        """Возвращает релевантные фрагменты под конкретный запрос."""
        self.ensure_ready()
        assert self._retriever is not None
        enriched_query = query.strip()
        if agent_hint:
            enriched_query += f"\n\n[Контекст агента: {agent_hint}]"
        nodes = self._retriever.retrieve(enriched_query)
        chunks: List[RAGChunk] = []
        for node in nodes:
            metadata = node.metadata or {}
            filename = metadata.get("file_name") or metadata.get("source") or "Документ"
            document_title = get_document_title(filename)
            location = ""
            page_num = metadata.get("page_label") or metadata.get("page_number")
            if page_num:
                location = f"стр. {page_num}"
            elif metadata.get("section"):
                location = f"раздел {metadata.get('section')}"
            elif metadata.get("paragraph"):
                location = f"п. {metadata.get('paragraph')}"
            chunks.append(
                RAGChunk(
                    document=document_title,
                    location=location,
                    text=node.get_text().strip(),
                    score=float(getattr(node, "score", 0.0) or 0.0),
                )
            )
        return chunks

    # --- внутреннее ---

    def _load_documents(self) -> List[Document]:
        docs_root = self.config.docs_root
        if not docs_root.exists():
            raise FileNotFoundError(f"Каталог с документами не найден: {docs_root}")

        logger.info("Загрузка документов из %s", docs_root)
        odt_reader = ODTReader()
        reader = SimpleDirectoryReader(
            input_dir=str(docs_root),
            recursive=True,
            required_exts=[".pdf", ".odt"],
            file_extractor={
                ".odt": odt_reader,
                "odt": odt_reader,
            },
        )
        documents = reader.load_data()
        if not documents:
            raise ValueError("Не найдено документов для индексации в папке docs")
        logger.info("Загружено %s документов", len(documents))
        return documents

    def _build_index(self, vector_store: PGVectorStore) -> None:
        self._configure_settings()
        documents = self._load_documents()
        storage_context = StorageContext.from_defaults(vector_store=vector_store)
        node_parser = SimpleNodeParser.from_defaults(chunk_size=1024, chunk_overlap=200)
        logger.info("Построение индекса в pgvector (таблица data_%s)...", self.config.rag_table_name)
        index = VectorStoreIndex.from_documents(
            documents,
            storage_context=storage_context,
            embed_model=self._embed_model,
            transformations=[node_parser],
            show_progress=False,
        )
        self._index = index
        self._retriever = index.as_retriever(similarity_top_k=self.config.rag_top_k)
        logger.info("Индекс собран")

    def _load_index(self, vector_store: PGVectorStore) -> None:
        self._configure_settings()
        logger.info("Подключение к существующему индексу pgvector (data_%s)", self.config.rag_table_name)
        index = VectorStoreIndex.from_vector_store(
            vector_store=vector_store,
            embed_model=self._embed_model,
        )
        self._index = index
        self._retriever = index.as_retriever(similarity_top_k=self.config.rag_top_k)

    def _get_vector_store(self) -> PGVectorStore:
        if self._vector_store is not None:
            return self._vector_store
        self._vector_store = PGVectorStore.from_params(
            host=self._db_url.host,
            port=self._db_url.port or 5432,
            user=self._db_url.username,
            password=self._db_url.password,
            database=self._db_url.database,
            table_name=self.config.rag_table_name,
            embed_dim=self.config.embedding_dim,
        )
        return self._vector_store

    def _full_table_name(self) -> str:
        # llama-index складывает данные в data_{table_name}
        return f"data_{self.config.rag_table_name}"

    def _has_data(self) -> bool:
        table = self._full_table_name()
        try:
            with self._engine.connect() as conn:
                result = conn.execute(text(f'SELECT COUNT(*) FROM public."{table}"'))
                count = result.scalar() or 0
            logger.info("В таблице %s найдено %s чанков", table, count)
            return count > 0
        except ProgrammingError:
            return False

    def _drop_table(self) -> None:
        table = self._full_table_name()
        with self._engine.begin() as conn:
            conn.execute(text(f'DROP TABLE IF EXISTS public."{table}"'))
        logger.info("Таблица %s удалена", table)


if __name__ == "__main__":
    cfg = Config()
    service = RAGService(cfg)
    service.rebuild()
