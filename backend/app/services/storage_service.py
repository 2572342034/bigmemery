import re
from dataclasses import dataclass
from pathlib import Path

from app.core.config import settings


@dataclass
class StoredFile:
    file_name: str
    relative_path: str
    absolute_path: Path
    size: int


class StorageService:
    def __init__(self) -> None:
        self.base_dir = Path(settings.knowledge_storage_directory)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def save_file(self, *, user_id: int, document_id: str, file_name: str, content: bytes) -> StoredFile:
        user_dir = self.base_dir / str(user_id)
        user_dir.mkdir(parents=True, exist_ok=True)

        safe_name = self._sanitize_filename(file_name)
        target_path = user_dir / f"{document_id}__{safe_name}"
        target_path.write_bytes(content)
        relative_path = target_path.relative_to(self.base_dir).as_posix()
        return StoredFile(
            file_name=safe_name,
            relative_path=relative_path,
            absolute_path=target_path,
            size=len(content),
        )

    def delete_file(self, relative_path: str | None) -> None:
        if not relative_path:
            return
        target_path = self.resolve_path(relative_path)
        if target_path.exists() and target_path.is_file():
            target_path.unlink()

    def resolve_path(self, relative_path: str) -> Path:
        resolved = (self.base_dir / relative_path).resolve()
        base = self.base_dir.resolve()
        if base not in resolved.parents and resolved != base:
            raise ValueError("Invalid file path")
        return resolved

    @staticmethod
    def _sanitize_filename(file_name: str) -> str:
        raw_name = Path(file_name or "document").name
        sanitized = re.sub(r"[^A-Za-z0-9._\-\u4e00-\u9fff]+", "_", raw_name).strip("._")
        return sanitized or "document"


storage_service = StorageService()
