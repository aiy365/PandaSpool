from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import InputError


SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
SESSION_TTL_SECONDS = 12 * 60 * 60


def _validate_username(value: str) -> str:
    username = value.strip()
    if not 3 <= len(username) <= 64:
        raise InputError("用户名长度必须为3到64个字符。")
    if any(character.isspace() or ord(character) < 32 for character in username):
        raise InputError("用户名不能包含空格或控制字符。")
    return username


def _validate_password(value: str) -> str:
    if not 10 <= len(value) <= 256:
        raise InputError("密码长度必须为10到256个字符。")
    return value


def _password_hash(password: str, salt: bytes) -> bytes:
    return hashlib.scrypt(
        password.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P
    )


@dataclass(frozen=True)
class CredentialSnapshot:
    username: str
    revision: int


class CredentialStore:
    """Small single-user credential store with atomic, permission-restricted writes."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path).expanduser().resolve()
        self._lock = threading.Lock()

    def initialize(self, username: str, password: str, *, replace: bool = False) -> None:
        username = _validate_username(username)
        password = _validate_password(password)
        with self._lock:
            if self.path.exists() and not replace:
                raise InputError("鉴权配置已经存在，不能重复初始化。")
            self._write(self._make_record(username, password, revision=1))

    def snapshot(self) -> CredentialSnapshot:
        record = self._read()
        return CredentialSnapshot(str(record["username"]), int(record["revision"]))

    def verify(self, username: str, password: str) -> CredentialSnapshot | None:
        try:
            record = self._read()
            salt = bytes.fromhex(str(record["salt"]))
            expected = bytes.fromhex(str(record["password_hash"]))
            supplied = _password_hash(password, salt)
        except (InputError, ValueError, TypeError):
            return None
        username_ok = hmac.compare_digest(username, str(record["username"]))
        password_ok = hmac.compare_digest(supplied, expected)
        if not (username_ok and password_ok):
            return None
        return CredentialSnapshot(str(record["username"]), int(record["revision"]))

    def update(
        self,
        current_password: str,
        username: str,
        new_password: str | None,
    ) -> CredentialSnapshot:
        username = _validate_username(username)
        if new_password is not None:
            new_password = _validate_password(new_password)
        with self._lock:
            record = self._read()
            salt = bytes.fromhex(str(record["salt"]))
            expected = bytes.fromhex(str(record["password_hash"]))
            if not hmac.compare_digest(_password_hash(current_password, salt), expected):
                raise InputError("当前密码不正确。")
            revision = int(record["revision"]) + 1
            if new_password is None:
                record = {**record, "username": username, "revision": revision}
            else:
                record = self._make_record(username, new_password, revision=revision)
            self._write(record)
        return CredentialSnapshot(username, revision)

    @staticmethod
    def _make_record(username: str, password: str, revision: int) -> dict[str, Any]:
        salt = secrets.token_bytes(16)
        return {
            "version": 1,
            "username": username,
            "revision": revision,
            "algorithm": "scrypt",
            "scrypt": {"n": SCRYPT_N, "r": SCRYPT_R, "p": SCRYPT_P},
            "salt": salt.hex(),
            "password_hash": _password_hash(password, salt).hex(),
        }

    def _read(self) -> dict[str, Any]:
        try:
            record = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise InputError("无法读取鉴权配置，请联系管理员。") from exc
        required = {"username", "revision", "salt", "password_hash"}
        if not isinstance(record, dict) or not required.issubset(record):
            raise InputError("鉴权配置格式无效，请联系管理员。")
        return record

    def _write(self, record: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(
            prefix=f".{self.path.name}.", dir=self.path.parent, text=True
        )
        temporary_path = Path(temporary)
        try:
            os.chmod(temporary_path, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(record, stream, ensure_ascii=False, indent=2)
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_path, self.path)
            os.chmod(self.path, 0o600)
        finally:
            if temporary_path.exists():
                temporary_path.unlink()


@dataclass(frozen=True)
class Session:
    username: str
    credential_revision: int
    expires_at: float


class SessionStore:
    def __init__(self, ttl_seconds: int = SESSION_TTL_SECONDS) -> None:
        self.ttl_seconds = ttl_seconds
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()

    def create(self, snapshot: CredentialSnapshot) -> str:
        token = secrets.token_urlsafe(32)
        now = time.time()
        with self._lock:
            self._purge(now)
            self._sessions[token] = Session(
                username=snapshot.username,
                credential_revision=snapshot.revision,
                expires_at=now + self.ttl_seconds,
            )
        return token

    def get(self, token: str, current_revision: int) -> Session | None:
        now = time.time()
        with self._lock:
            self._purge(now)
            session = self._sessions.get(token)
            if session is None or session.credential_revision != current_revision:
                return None
            return session

    def revoke(self, token: str) -> None:
        with self._lock:
            self._sessions.pop(token, None)

    def revoke_all(self) -> None:
        with self._lock:
            self._sessions.clear()

    def _purge(self, now: float) -> None:
        expired = [token for token, value in self._sessions.items() if value.expires_at <= now]
        for token in expired:
            self._sessions.pop(token, None)


class LoginLimiter:
    def __init__(self, maximum_attempts: int = 5, window_seconds: int = 10 * 60) -> None:
        self.maximum_attempts = maximum_attempts
        self.window_seconds = window_seconds
        self._failures: list[float] = []
        self._lock = threading.Lock()

    def is_blocked(self) -> bool:
        with self._lock:
            self._purge(time.monotonic())
            return len(self._failures) >= self.maximum_attempts

    def failure(self) -> None:
        with self._lock:
            now = time.monotonic()
            self._purge(now)
            self._failures.append(now)

    def success(self) -> None:
        with self._lock:
            self._failures.clear()

    def _purge(self, now: float) -> None:
        cutoff = now - self.window_seconds
        self._failures = [value for value in self._failures if value >= cutoff]
