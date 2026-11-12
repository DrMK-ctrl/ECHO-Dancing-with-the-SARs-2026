"""Private, content-addressed storage for local investigation drafts."""

from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import uuid
from typing import Any

from echo.investigation_draft import (
    InvestigationDraftError,
    inherited_followup_sources_for_revision,
    validate_investigation_draft,
)


_DRAFT_NAME = re.compile(r"^([0-9a-f]{64})\.json$")
MAX_DRAFTS = 100
MAX_STORE_BYTES = 512 * 1024 * 1024
MAX_DRAFT_BYTES = 40 * 1024 * 1024


class DraftStoreError(ValueError):
    """Raised when a local draft cannot be stored or retrieved safely."""


def default_draft_store_dir() -> Path:
    """Return the per-user XDG data directory used by the local application."""
    base = os.environ.get("XDG_DATA_HOME")
    return (Path(base).expanduser() if base else Path.home() / ".local" / "share") / "echo" / "investigations"


def _serialize(draft: dict[str, Any]) -> bytes:
    try:
        return json.dumps(
            draft,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        raise DraftStoreError("investigation draft is not serializable JSON") from exc


class LocalDraftStore:
    """Store immutable draft snapshots with owner-only filesystem permissions."""

    def __init__(self, directory: Path):
        self.directory = Path(directory).expanduser().resolve()

    def _prepare(self) -> None:
        try:
            self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            self.directory.chmod(0o700)
        except OSError as exc:
            raise DraftStoreError("local investigation storage is unavailable") from exc
        if not self.directory.is_dir():
            raise DraftStoreError("local investigation storage path is not a directory")

    def save(self, draft: dict[str, Any]) -> dict[str, str | bool]:
        try:
            validate_investigation_draft(draft)
        except InvestigationDraftError as exc:
            raise DraftStoreError(f"investigation draft validation failed: {exc}") from exc
        self.verify_revision_parent(draft)
        payload = _serialize(draft)
        if len(payload) > MAX_DRAFT_BYTES:
            raise DraftStoreError("investigation draft exceeds the 40 MiB local storage limit")
        digest = hashlib.sha256(payload).hexdigest()
        self._prepare()
        target = self.directory / f"{digest}.json"
        if target.is_file():
            existing = target.read_bytes()
            if hashlib.sha256(existing).hexdigest() == digest and existing == payload:
                return {"draft_id": digest, "saved_at_utc": datetime.fromtimestamp(target.stat().st_mtime, timezone.utc).isoformat(), "already_saved": True}
            raise DraftStoreError("content-addressed draft path contains unexpected data")

        files = [item for item in self.directory.glob("*.json") if item.is_file()]
        total_bytes = sum(item.stat().st_size for item in files)
        if len(files) >= MAX_DRAFTS:
            raise DraftStoreError("local investigation storage reached its 100-draft limit")
        if total_bytes + len(payload) > MAX_STORE_BYTES:
            raise DraftStoreError("local investigation storage reached its 512 MiB limit")

        temporary = self.directory / f".{uuid.uuid4().hex}.tmp"
        try:
            descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, target)
            directory_fd = os.open(self.directory, os.O_RDONLY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        except OSError as exc:
            try:
                temporary.unlink(missing_ok=True)
            except OSError:
                pass
            raise DraftStoreError("investigation draft could not be saved atomically") from exc
        target.chmod(0o600)
        return {"draft_id": digest, "saved_at_utc": datetime.now(timezone.utc).isoformat(), "already_saved": False}

    def list(self) -> list[dict[str, Any]]:
        self._prepare()
        records = []
        for path in self.directory.glob("*.json"):
            match = _DRAFT_NAME.fullmatch(path.name)
            if not match or not path.is_file():
                continue
            try:
                size = path.stat().st_size
                if size > MAX_DRAFT_BYTES:
                    records.append({"draft_id": match.group(1), "integrity": "INVALID", "error": "size_limit"})
                    continue
                payload = path.read_bytes()
                if hashlib.sha256(payload).hexdigest() != match.group(1):
                    records.append({"draft_id": match.group(1), "integrity": "INVALID", "error": "checksum_mismatch"})
                    continue
                draft = json.loads(payload)
                validate_investigation_draft(draft)
                self.verify_revision_parent(draft, seen={match.group(1)})
                records.append({
                    "draft_id": match.group(1),
                    "integrity": "VALID",
                    "saved_at_utc": datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat(),
                    "created_at_utc": draft.get("created_at_utc"),
                    "status": draft.get("status"),
                    "question": draft.get("question"),
                })
            except (DraftStoreError, OSError, json.JSONDecodeError, InvestigationDraftError, UnicodeDecodeError, TypeError):
                records.append({"draft_id": match.group(1), "integrity": "INVALID", "error": "invalid_record"})
        records.sort(key=lambda item: item.get("saved_at_utc", ""), reverse=True)
        return records

    def load(self, draft_id: str) -> dict[str, Any]:
        if not isinstance(draft_id, str) or not re.fullmatch(r"[0-9a-f]{64}", draft_id):
            raise DraftStoreError("draft_id must be a lowercase SHA-256 identifier")
        return self._load(draft_id, seen=set())

    def _load(self, draft_id: str, *, seen: set[str]) -> dict[str, Any]:
        if draft_id in seen:
            raise DraftStoreError("investigation revision chain contains a cycle")
        self._prepare()
        path = self.directory / f"{draft_id}.json"
        try:
            payload = path.read_bytes()
        except OSError as exc:
            raise DraftStoreError("saved investigation draft or revision parent is unavailable") from exc
        if len(payload) > MAX_DRAFT_BYTES or hashlib.sha256(payload).hexdigest() != draft_id:
            raise DraftStoreError("saved investigation draft checksum or size is invalid")
        try:
            draft = json.loads(payload)
            validate_investigation_draft(draft)
        except (json.JSONDecodeError, UnicodeDecodeError, InvestigationDraftError) as exc:
            raise DraftStoreError("saved investigation draft failed structural validation") from exc
        self.verify_revision_parent(draft, seen=seen | {draft_id})
        return draft

    def verify_revision_parent(self, draft: dict[str, Any], *, seen: set[str] | None = None) -> None:
        revision = draft.get("revision")
        if revision is None:
            return
        parent_id = revision["parent_draft_sha256"]
        visited = seen or set()
        parent = self._load(parent_id, seen=visited)
        parent_revision = parent.get("revision")
        parent_number = parent_revision["revision_number"] if isinstance(parent_revision, dict) else 0
        if (
            parent.get("status") != "DRAFT_ANALYST_ASSESSED_UNVERIFIED"
            or parent.get("analyst_assessment", {}).get("assessment_sha256") != revision["parent_assessment_sha256"]
            or revision["revision_number"] != parent_number + 1
        ):
            raise DraftStoreError("investigation revision does not match its immutable assessed parent")
        if (
            "inherited_followup_sources" in revision
            and revision["inherited_followup_sources"] != inherited_followup_sources_for_revision(parent)
        ):
            raise DraftStoreError("investigation revision changed the source-to-follow-up lineage of inherited metadata")
