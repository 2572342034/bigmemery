import json
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import desc, select

from app.db.chat_models import ChatConversation, ChatMessage, KnowledgeDocument
from app.db.session import chat_session_scope
from app.schemas.conversation import (
    ConversationDetail,
    ConversationMessage,
    ConversationSource,
    ConversationSummary,
)
from app.schemas.knowledge import KnowledgeItem


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class ChatDBService:
    def list_conversations(self, user_id: int) -> list[ConversationSummary]:
        with chat_session_scope() as session:
            conversations = session.scalars(
                select(ChatConversation)
                .where(ChatConversation.user_id == user_id)
                .order_by(desc(ChatConversation.updated_at), desc(ChatConversation.created_at))
                .limit(10)
            ).all()
            return [self._to_summary(item) for item in conversations]

    def get_conversation(self, user_id: int, conversation_id: str) -> ConversationDetail | None:
        with chat_session_scope() as session:
            conversation = session.get(ChatConversation, conversation_id)
            if conversation is None or conversation.user_id != user_id:
                return None
            return self._to_detail(conversation)

    def create_conversation(self, user_id: int, model: str, use_rag: bool = True) -> ConversationDetail:
        with chat_session_scope() as session:
            conversation = ChatConversation(
                id=f"conv_{uuid4().hex[:12]}",
                user_id=user_id,
                title="新对话",
                preview="等待开始对话",
                model=model,
                use_rag=use_rag,
                latest_grounded=False,
                latest_sources_json="[]",
            )
            session.add(conversation)
            session.flush()
            session.refresh(conversation)
            return self._to_detail(conversation)

    def delete_conversation(self, user_id: int, conversation_id: str) -> bool:
        with chat_session_scope() as session:
            conversation = session.get(ChatConversation, conversation_id)
            if conversation is None or conversation.user_id != user_id:
                return False
            session.delete(conversation)
            return True

    def add_message(
        self,
        *,
        user_id: int,
        conversation_id: str,
        role: str,
        content: str,
        model: str | None = None,
        latest_sources: list[dict] | None = None,
        latest_grounded: bool | None = None,
    ) -> ConversationDetail:
        with chat_session_scope() as session:
            conversation = session.get(ChatConversation, conversation_id)
            if conversation is None or conversation.user_id != user_id:
                raise ValueError("Conversation not found")

            session.add(
                ChatMessage(
                    conversation_id=conversation_id,
                    role=role,
                    content=content,
                    model=model,
                )
            )
            session.flush()

            if model:
                conversation.model = model
            if latest_grounded is not None:
                conversation.latest_grounded = latest_grounded
            if latest_sources is not None:
                conversation.latest_sources_json = json.dumps(latest_sources, ensure_ascii=False)
            conversation.updated_at = utc_now()
            self._refresh_summary(conversation, session)
            session.flush()
            session.refresh(conversation)
            return self._to_detail(conversation)

    def list_knowledge(self, user_id: int) -> list[KnowledgeItem]:
        with chat_session_scope() as session:
            documents = session.scalars(
                select(KnowledgeDocument)
                .where(KnowledgeDocument.user_id == user_id)
                .order_by(desc(KnowledgeDocument.created_at))
            ).all()
            return [self._to_knowledge_item(item, include_content=False) for item in documents]

    def get_knowledge(self, user_id: int, document_id: str) -> KnowledgeItem | None:
        with chat_session_scope() as session:
            document = session.get(KnowledgeDocument, document_id)
            if document is None or document.user_id != user_id:
                return None
            return self._to_knowledge_item(document, include_content=True)

    def create_knowledge(
        self,
        *,
        user_id: int,
        title: str,
        content: str,
        source: str,
        document_id: str | None = None,
        file_name: str | None = None,
        file_path: str | None = None,
        mime_type: str | None = None,
        storage_provider: str = "local",
        file_size: int = 0,
        chunk_count: int = 0,
        index_status: str = "ready",
    ) -> KnowledgeItem:
        with chat_session_scope() as session:
            document = KnowledgeDocument(
                id=document_id or f"doc_{uuid4().hex[:12]}",
                user_id=user_id,
                title=title,
                content=content,
                source=source,
                file_name=file_name,
                file_path=file_path,
                mime_type=mime_type,
                storage_provider=storage_provider,
                file_size=file_size,
                chunk_count=chunk_count,
                content_length=len(content),
                index_status=index_status,
            )
            session.add(document)
            session.flush()
            session.refresh(document)
            return self._to_knowledge_item(document, include_content=True)

    def update_knowledge_status(
        self,
        user_id: int,
        document_id: str,
        *,
        chunk_count: int,
        index_status: str,
    ) -> KnowledgeItem | None:
        with chat_session_scope() as session:
            document = session.get(KnowledgeDocument, document_id)
            if document is None or document.user_id != user_id:
                return None
            document.chunk_count = chunk_count
            document.index_status = index_status
            session.add(document)
            session.flush()
            session.refresh(document)
            return self._to_knowledge_item(document, include_content=True)

    def delete_knowledge(self, user_id: int, document_id: str) -> KnowledgeItem | None:
        with chat_session_scope() as session:
            document = session.get(KnowledgeDocument, document_id)
            if document is None or document.user_id != user_id:
                return None
            item = self._to_knowledge_item(document, include_content=True)
            session.delete(document)
            return item

    def save_user_message(
        self,
        *,
        user_id: int,
        conversation_id: str,
        model: str,
        content: str,
    ) -> ConversationDetail:
        return self.add_message(
            user_id=user_id,
            conversation_id=conversation_id,
            role="user",
            content=content,
            model=model,
        )

    def save_assistant_message(
        self,
        *,
        user_id: int,
        conversation_id: str,
        model: str,
        content: str,
        latest_sources: list[dict] | None = None,
        latest_grounded: bool | None = None,
    ) -> ConversationDetail:
        return self.add_message(
            user_id=user_id,
            conversation_id=conversation_id,
            role="assistant",
            content=content,
            model=model,
            latest_sources=latest_sources,
            latest_grounded=latest_grounded,
        )

    @staticmethod
    def _parse_latest_sources(raw_value: str | None) -> list[ConversationSource]:
        if not raw_value:
            return []
        try:
            items = json.loads(raw_value)
        except json.JSONDecodeError:
            return []
        if not isinstance(items, list):
            return []
        sources = []
        for item in items:
            if isinstance(item, dict):
                try:
                    sources.append(ConversationSource(**item))
                except Exception:
                    continue
        return sources

    def _refresh_summary(self, conversation: ChatConversation, session) -> None:
        messages = session.scalars(
            select(ChatMessage)
            .where(ChatMessage.conversation_id == conversation.id)
            .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
        ).all()
        first_user_message = next((item.content for item in messages if item.role == "user"), "")
        last_message = messages[-1].content if messages else ""
        conversation.title = self._build_title(first_user_message)
        conversation.preview = self._build_preview(last_message)
        if conversation.updated_at is None:
            conversation.updated_at = utc_now()
        session.add(conversation)

    @staticmethod
    def _build_title(content: str) -> str:
        text = " ".join(content.split()).strip()
        if not text:
            return "新对话"
        return text[:18] + ("..." if len(text) > 18 else "")

    @staticmethod
    def _build_preview(content: str) -> str:
        text = " ".join(content.split()).strip()
        return text[:72] + ("..." if len(text) > 72 else "")

    @staticmethod
    def _to_summary(conversation: ChatConversation) -> ConversationSummary:
        message_count = getattr(conversation, "message_count", None)
        if message_count is None:
            message_count = len(conversation.messages)
        return ConversationSummary(
            id=conversation.id,
            title=conversation.title,
            preview=conversation.preview,
            model=conversation.model,
            use_rag=conversation.use_rag,
            latest_grounded=bool(getattr(conversation, "latest_grounded", False)),
            latest_sources=ChatDBService._parse_latest_sources(
                getattr(conversation, "latest_sources_json", None)
            ),
            updated_at=conversation.updated_at,
            created_at=conversation.created_at,
            message_count=message_count,
        )

    @staticmethod
    def _to_detail(conversation: ChatConversation) -> ConversationDetail:
        return ConversationDetail(
            **ChatDBService._to_summary(conversation).model_dump(),
            messages=[
                ConversationMessage(
                    id=item.id,
                    role=item.role,
                    content=item.content,
                    model=item.model,
                    created_at=item.created_at,
                )
                for item in conversation.messages
            ],
        )

    @staticmethod
    def _to_knowledge_item(document: KnowledgeDocument, *, include_content: bool) -> KnowledgeItem:
        preview = " ".join((document.content or "").split()).strip()
        preview = preview[:180] + ("..." if len(preview) > 180 else "")
        return KnowledgeItem(
            id=document.id,
            title=document.title,
            source=document.source,
            file_name=document.file_name,
            file_path=document.file_path,
            mime_type=document.mime_type,
            storage_provider=document.storage_provider,
            file_size=document.file_size,
            chunk_count=document.chunk_count,
            content_length=document.content_length or len(document.content or ""),
            index_status=document.index_status,
            content_preview=preview,
            content=document.content if include_content else None,
            created_at=document.created_at,
        )


db_service = ChatDBService()
