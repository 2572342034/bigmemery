import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document

from app.core.config import settings
from app.db.chat_models import KnowledgeDocument
from app.db.session import chat_session_scope
from app.schemas.knowledge import KnowledgeItem
from app.services.llm_service import llm_service


@dataclass
class RetrievedChunk:
    document_id: str
    title: str
    source: str
    content: str
    vector_score: float
    keyword_score: float
    rerank_score: float
    citation: str


@dataclass
class IndexingResult:
    success: bool
    chunk_count: int
    mode: str


class KnowledgeService:
    def __init__(self) -> None:
        self._vectorstore: Chroma | None = None

    def _get_store(self) -> Chroma:
        if self._vectorstore is None:
            Path(settings.chroma_persist_directory).mkdir(parents=True, exist_ok=True)
            self._vectorstore = Chroma(
                collection_name=settings.chroma_collection_name,
                embedding_function=llm_service.get_embeddings(),
                persist_directory=settings.chroma_persist_directory,
            )
        return self._vectorstore

    def index_document(self, user_id: int, item: KnowledgeItem) -> IndexingResult:
        chunks = self._chunk_text(item.content or "")
        documents = [
            Document(
                page_content=chunk,
                metadata={
                    "document_id": item.id,
                    "user_id": user_id,
                    "title": item.title,
                    "source": item.source,
                    "chunk_index": index,
                },
            )
            for index, chunk in enumerate(chunks)
        ]
        if not documents:
            return IndexingResult(success=False, chunk_count=0, mode="empty")

        try:
            store = self._get_store()
            store.add_documents(documents)
            return IndexingResult(success=True, chunk_count=len(documents), mode="vector")
        except Exception:
            return IndexingResult(success=False, chunk_count=len(documents), mode="keyword_only")

    def delete_document(self, document_id: str) -> None:
        try:
            store = self._get_store()
            store._collection.delete(where={"document_id": document_id})
        except Exception:
            return None

    def retrieve_context(self, user_id: int, query: str, top_k: int | None = None) -> list[RetrievedChunk]:
        vector_hits = self._vector_search(user_id, query, settings.rag_vector_k)
        keyword_hits = self._keyword_search(user_id, query, settings.rag_keyword_k)
        merged = self._merge_and_rerank(query, vector_hits, keyword_hits)
        limit = top_k or settings.rag_top_k
        return [item for item in merged if item.rerank_score >= settings.rag_min_score][:limit]

    @staticmethod
    def _chunk_text(content: str, chunk_size: int = 500, overlap: int = 80) -> list[str]:
        text = content.strip()
        if not text:
            return []
        if len(text) <= chunk_size:
            return [text]

        chunks: list[str] = []
        start = 0
        while start < len(text):
            end = min(len(text), start + chunk_size)
            chunks.append(text[start:end])
            if end == len(text):
                break
            start = max(0, end - overlap)
        return chunks

    def _vector_search(self, user_id: int, query: str, k: int) -> list[RetrievedChunk]:
        try:
            store = self._get_store()
            pairs = store.similarity_search_with_score(
                query,
                k=k,
                filter={"user_id": user_id},
            )
        except Exception:
            return []
        results: list[RetrievedChunk] = []
        for index, (doc, distance) in enumerate(pairs, start=1):
            score = 1 / (1 + float(distance))
            results.append(
                RetrievedChunk(
                    document_id=str(doc.metadata.get("document_id", "")),
                    title=str(doc.metadata.get("title", "Knowledge")),
                    source=str(doc.metadata.get("source", "upload")),
                    content=doc.page_content,
                    vector_score=score,
                    keyword_score=0.0,
                    rerank_score=score,
                    citation=f"[{index}] {doc.metadata.get('title', 'Knowledge')}",
                )
            )
        return results

    def _keyword_search(self, user_id: int, query: str, k: int) -> list[RetrievedChunk]:
        query_terms = self._tokenize(query)
        if not query_terms:
            return []

        with chat_session_scope() as session:
            documents = session.query(KnowledgeDocument).filter(KnowledgeDocument.user_id == user_id).all()

        scored: list[tuple[KnowledgeDocument, float]] = []
        for document in documents:
            score = self._keyword_score(query_terms, document.content, document.title)
            if score > 0:
                scored.append((document, score))

        scored.sort(key=lambda item: item[1], reverse=True)
        results: list[RetrievedChunk] = []
        for index, (document, score) in enumerate(scored[:k], start=1):
            results.append(
                RetrievedChunk(
                    document_id=document.id,
                    title=document.title,
                    source=document.source,
                    content=document.content,
                    vector_score=0.0,
                    keyword_score=score,
                    rerank_score=score,
                    citation=f"[K{index}] {document.title}",
                )
            )
        return results

    def _merge_and_rerank(
        self,
        query: str,
        vector_hits: list[RetrievedChunk],
        keyword_hits: list[RetrievedChunk],
    ) -> list[RetrievedChunk]:
        merged: dict[tuple[str, str], RetrievedChunk] = {}
        for item in vector_hits + keyword_hits:
            key = (item.document_id, item.content)
            existing = merged.get(key)
            if existing is None:
                merged[key] = item
                continue
            existing.vector_score = max(existing.vector_score, item.vector_score)
            existing.keyword_score = max(existing.keyword_score, item.keyword_score)

        query_terms = self._tokenize(query)
        reranked: list[RetrievedChunk] = []
        for item in merged.values():
            semantic_overlap = self._overlap_score(query_terms, item.content, item.title)
            item.rerank_score = (
                0.5 * item.vector_score
                + 0.3 * item.keyword_score
                + 0.2 * semantic_overlap
            )
            reranked.append(item)

        reranked.sort(key=lambda item: item.rerank_score, reverse=True)
        return reranked[: settings.rag_rerank_k]

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        lowered = text.lower()
        tokens: list[str] = []
        for block in re.findall(r"[\u4e00-\u9fff]+|[A-Za-z0-9_]+", lowered):
            if re.fullmatch(r"[A-Za-z0-9_]+", block):
                tokens.append(block)
                continue

            tokens.extend(list(block))
            if len(block) > 1:
                tokens.extend(block[index : index + 2] for index in range(len(block) - 1))
            if len(block) > 2:
                tokens.extend(block[index : index + 3] for index in range(len(block) - 2))
        return tokens

    def _keyword_score(self, query_terms: list[str], content: str, title: str) -> float:
        haystack_terms = self._tokenize(f"{title} {content}")
        if not haystack_terms:
            return 0.0

        tf = Counter(haystack_terms)
        length = max(len(haystack_terms), 1)
        score = 0.0
        for term in query_terms:
            freq = tf.get(term, 0)
            if freq == 0:
                continue
            score += math.log1p(freq) / length * 20
            if term in title.lower():
                score += 0.25
        return score

    def _overlap_score(self, query_terms: list[str], content: str, title: str) -> float:
        haystack = set(self._tokenize(f"{title} {content}"))
        if not query_terms or not haystack:
            return 0.0
        overlap = sum(1 for term in query_terms if term in haystack)
        return overlap / max(len(set(query_terms)), 1)


knowledge_service = KnowledgeService()
