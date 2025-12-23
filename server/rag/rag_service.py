"""
RAG-сервис на базе LlamaIndex.
Отвечает за индексацию документов и выдачу релевантных фрагментов.
"""

from __future__ import annotations

import logging
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import zipfile
import xml.etree.ElementTree as ET

from chromadb import PersistentClient
from llama_index.core import (
    Document,
    ServiceContext,
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
    Settings,
)
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.storage.index_store import SimpleIndexStore
from llama_index.core.llms import MockLLM
from llama_index.core.node_parser import SimpleNodeParser
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.chroma import ChromaVectorStore

from config import Config


logger = logging.getLogger(__name__)

# Маппинг имён файлов в человекочитаемые названия документов
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
    """Управляет построением и использованием векторного индекса документов."""

    def __init__(self, config: Config):
        self.config = config
        self._index: Optional[VectorStoreIndex] = None
        self._retriever = None
        self._embed_model = HuggingFaceEmbedding(model_name=self.config.embedding_model_name)
        self._configure_settings()
        self._chroma_client = PersistentClient(path=str(self.config.chroma_persist_dir))
        self._vector_store: Optional[ChromaVectorStore] = None

    def _configure_settings(self) -> None:
        """Настраивает глобальные параметры LlamaIndex (LLM/эмбеддинги)."""
        Settings.llm = None
        Settings.embed_model = self._embed_model

    def ensure_ready(self) -> None:
        """Гарантирует, что индекс построен и загружен."""
        if self._index is not None and self._retriever is not None:
            return
        persist_dir = self._ensure_storage_dir()
        vector_store = self._get_vector_store()
        if (persist_dir / "docstore.json").exists():
            self._load_index(persist_dir, vector_store)
        else:
            self._build_index(persist_dir, vector_store)

    def rebuild(self) -> None:
        """Полностью пересобирает индекс, очищая предыдущий."""
        persist_dir = self._ensure_storage_dir()
        if persist_dir.exists():
            shutil.rmtree(persist_dir)
        self._reset_vector_store()
        self._index = None
        self._retriever = None
        self._build_index(persist_dir, self._get_vector_store())

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
            # Форматируем номер страницы/раздела человекочитаемо
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

    def _ensure_storage_dir(self) -> Path:
        persist_dir = self.config.rag_storage_path
        persist_dir.mkdir(parents=True, exist_ok=True)
        return persist_dir

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

    def _build_index(self, persist_dir: Path, vector_store: ChromaVectorStore) -> None:
        self._configure_settings()
        documents = self._load_documents()
        docstore = SimpleDocumentStore()
        index_store = SimpleIndexStore()
        storage_context = StorageContext.from_defaults(
            persist_dir=str(persist_dir),
            docstore=docstore,
            index_store=index_store,
            vector_store=vector_store,
        )
        service_context = ServiceContext.from_defaults(
            llm=MockLLM(),
            embed_model=self._embed_model,
            node_parser=SimpleNodeParser.from_defaults(chunk_size=1024, chunk_overlap=200),
        )
        logger.info("Построение векторного индекса...")
        index = VectorStoreIndex.from_documents(
            documents,
            service_context=service_context,
            storage_context=storage_context,
        )
        index.storage_context.persist(persist_dir=str(persist_dir))
        self._index = index
        self._retriever = index.as_retriever(similarity_top_k=self.config.rag_top_k)
        logger.info("Индекс сохранён в %s", persist_dir)

    def _load_index(self, persist_dir: Path, vector_store: ChromaVectorStore) -> None:
        self._configure_settings()
        logger.info("Загрузка существующего индекса из %s", persist_dir)
        storage_context = StorageContext.from_defaults(
            persist_dir=str(persist_dir),
            vector_store=vector_store,
        )
        try:
            index = load_index_from_storage(storage_context)
        except FileNotFoundError:
            logger.warning("Файлы docstore отсутствуют, выполняем пересборку индекса...")
            self._build_index(persist_dir, vector_store)
            return

        self._index = index
        self._retriever = index.as_retriever(similarity_top_k=self.config.rag_top_k)
        logger.info("Индекс загружен")

    def _reset_vector_store(self) -> None:
        try:
            self._chroma_client.delete_collection(self.config.chroma_collection)
        except Exception:
            pass
        self._vector_store = None

    def _get_vector_store(self) -> ChromaVectorStore:
        if self._vector_store is not None:
            return self._vector_store
        collection = self._chroma_client.get_or_create_collection(name=self.config.chroma_collection)
        self._vector_store = ChromaVectorStore(chroma_collection=collection)
        return self._vector_store


if __name__ == "__main__":
    cfg = Config()
    service = RAGService(cfg)
    service.rebuild()


