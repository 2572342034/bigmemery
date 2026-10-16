from contextlib import contextmanager
from datetime import datetime

from sqlalchemy import create_engine, inspect, text, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.db.chat_models import ChatBase, ChatMessage
from app.db.user_models import UserBase, User

chat_engine = create_engine(
    settings.chat_sqlite_url,
    echo=False,
    future=True,
    connect_args={"check_same_thread": False},
)
ChatSessionLocal = sessionmaker(
    bind=chat_engine,
    autoflush=False,
    autocommit=False,
    future=True,
    expire_on_commit=False,
)

user_engine = create_engine(
    settings.mysql_url,
    echo=False,
    future=True,
    pool_pre_ping=True,
)

UserSessionLocal = sessionmaker(
    bind=user_engine,
    autoflush=False,
    autocommit=False,
    future=True,
    expire_on_commit=False,
)


def init_databases() -> None:
    ChatBase.metadata.create_all(bind=chat_engine)
    migrate_chat_sqlite_schema()
    UserBase.metadata.create_all(bind=user_engine)


def migrate_chat_sqlite_schema() -> None:
    if not settings.chat_sqlite_url.startswith("sqlite:///"):
        return

    inspector = inspect(chat_engine)
    existing_tables = set(inspector.get_table_names())

    with chat_engine.begin() as connection:
        if "chat_messages" in existing_tables:
            columns = {item["name"] for item in inspector.get_columns("chat_messages")}
            expected_columns = {"id", "conversation_id", "role", "content", "model", "created_at"}
            if not expected_columns.issubset(columns):
                backup_name = f"chat_messages_legacy_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                connection.execute(text(f"ALTER TABLE chat_messages RENAME TO {backup_name}"))
                ChatMessage.__table__.create(bind=connection, checkfirst=True)

        if "chat_conversations" in existing_tables:
            columns = {item["name"] for item in inspector.get_columns("chat_conversations")}
            if "use_rag" not in columns:
                connection.execute(
                    text("ALTER TABLE chat_conversations ADD COLUMN use_rag BOOLEAN DEFAULT 1 NOT NULL")
                )
            additions = {
                "latest_grounded": (
                    "ALTER TABLE chat_conversations "
                    "ADD COLUMN latest_grounded BOOLEAN DEFAULT 0 NOT NULL"
                ),
                "latest_sources_json": "ALTER TABLE chat_conversations ADD COLUMN latest_sources_json TEXT",
            }
            for name, statement in additions.items():
                if name not in columns:
                    connection.execute(text(statement))

            connection.execute(
                text(
                    "UPDATE chat_conversations "
                    "SET latest_sources_json = '[]' "
                    "WHERE latest_sources_json IS NULL OR latest_sources_json = ''"
                )
            )

        if "knowledge_documents" in existing_tables:
            columns = {item["name"] for item in inspector.get_columns("knowledge_documents")}
            additions = {
                "file_name": "ALTER TABLE knowledge_documents ADD COLUMN file_name VARCHAR(255)",
                "file_path": "ALTER TABLE knowledge_documents ADD COLUMN file_path VARCHAR(500)",
                "mime_type": "ALTER TABLE knowledge_documents ADD COLUMN mime_type VARCHAR(160)",
                "storage_provider": (
                    "ALTER TABLE knowledge_documents "
                    "ADD COLUMN storage_provider VARCHAR(40) DEFAULT 'local' NOT NULL"
                ),
                "file_size": "ALTER TABLE knowledge_documents ADD COLUMN file_size INTEGER DEFAULT 0 NOT NULL",
                "chunk_count": "ALTER TABLE knowledge_documents ADD COLUMN chunk_count INTEGER DEFAULT 0 NOT NULL",
                "content_length": (
                    "ALTER TABLE knowledge_documents ADD COLUMN content_length INTEGER DEFAULT 0 NOT NULL"
                ),
                "index_status": (
                    "ALTER TABLE knowledge_documents "
                    "ADD COLUMN index_status VARCHAR(40) DEFAULT 'ready' NOT NULL"
                ),
            }
            for name, statement in additions.items():
                if name not in columns:
                    connection.execute(text(statement))

            connection.execute(
                text(
                    "UPDATE knowledge_documents "
                    "SET content_length = LENGTH(COALESCE(content, '')) "
                    "WHERE content_length IS NULL OR content_length = 0"
                )
            )
            connection.execute(
                text(
                    "UPDATE knowledge_documents "
                    "SET storage_provider = 'local' "
                    "WHERE storage_provider IS NULL OR storage_provider = ''"
                )
            )
            connection.execute(
                text(
                    "UPDATE knowledge_documents "
                    "SET index_status = 'ready' "
                    "WHERE index_status IS NULL OR index_status = ''"
                )
            )


@contextmanager
def chat_session_scope() -> Session:
    session = ChatSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@contextmanager
def user_session_scope() -> Session:
    session = UserSessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()



