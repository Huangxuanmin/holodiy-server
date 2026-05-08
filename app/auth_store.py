"""User / token / verification-code store backed by SQLAlchemy (SQLite by default).

Public API is kept stable so ``auth_routes`` / ``hitem3d_routes`` are not
affected by the underlying storage change.
"""
from __future__ import annotations

import secrets
import time
import uuid
from typing import Dict, Optional

from sqlalchemy import select
from werkzeug.security import check_password_hash, generate_password_hash

from .db import session_scope
from .models import OAuthLink, Token, User, VerifyCode

_CODE_TTL_SECONDS = 5 * 60
_TOKEN_TTL_SECONDS = 7 * 24 * 3600


# ---------------------------------------------------------------------------
# serialization helpers
# ---------------------------------------------------------------------------

def _user_to_dict(user: User) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "phone": user.phone,
        "name": user.name,
        "avatar": user.avatar,
        "password_hash": user.password_hash,
        "oauth": [{"provider": link.provider, "uid": link.uid} for link in user.oauth_links],
        "providers": sorted({link.provider for link in user.oauth_links}),
        "created_at": user.created_at,
    }


def public_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "email": user.get("email"),
        "phone": user.get("phone"),
        "name": user.get("name"),
        "avatar": user.get("avatar"),
        "providers": user.get("providers", []),
    }


# ---------------------------------------------------------------------------
# users
# ---------------------------------------------------------------------------

def _find_user_row(session, *, email: Optional[str] = None,
                   phone: Optional[str] = None,
                   provider: Optional[str] = None,
                   provider_uid: Optional[str] = None) -> Optional[User]:
    if email:
        row = session.scalar(select(User).where(User.email == email))
        if row:
            return row
    if phone:
        row = session.scalar(select(User).where(User.phone == phone))
        if row:
            return row
    if provider and provider_uid:
        link = session.scalar(
            select(OAuthLink).where(
                OAuthLink.provider == provider, OAuthLink.uid == provider_uid
            )
        )
        if link:
            return link.user
    return None


def find_user(**kwargs) -> Optional[dict]:
    with session_scope() as session:
        row = _find_user_row(session, **kwargs)
        return _user_to_dict(row) if row else None


def create_user(*, email: Optional[str] = None, phone: Optional[str] = None,
                password: Optional[str] = None, name: Optional[str] = None,
                avatar: Optional[str] = None,
                provider: Optional[str] = None,
                provider_uid: Optional[str] = None) -> dict:
    with session_scope() as session:
        existing = _find_user_row(
            session,
            email=email,
            phone=phone,
            provider=provider,
            provider_uid=provider_uid,
        )
        if existing:
            return _user_to_dict(existing)

        user_id = uuid.uuid4().hex
        default_name = name or (email.split("@")[0] if email else None) or \
                       (f"用户{phone[-4:]}" if phone else f"User-{user_id[:6]}")
        user = User(
            id=user_id,
            email=email,
            phone=phone,
            name=default_name,
            avatar=avatar,
            password_hash=generate_password_hash(password) if password else None,
            created_at=time.time(),
        )
        session.add(user)
        if provider and provider_uid:
            session.add(OAuthLink(user_id=user_id, provider=provider, uid=provider_uid))
        session.flush()
        session.refresh(user)
        return _user_to_dict(user)


def verify_password(user: dict, password: str) -> bool:
    stored = user.get("password_hash")
    if not stored or not password:
        return False
    return check_password_hash(stored, password)


def link_oauth(user_id: str, provider: str, provider_uid: str) -> None:
    with session_scope() as session:
        user = session.get(User, user_id)
        if not user:
            return
        exists = any(
            link.provider == provider and link.uid == provider_uid
            for link in user.oauth_links
        )
        if not exists:
            session.add(OAuthLink(user_id=user_id, provider=provider, uid=provider_uid))


# ---------------------------------------------------------------------------
# tokens
# ---------------------------------------------------------------------------

def issue_token(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    with session_scope() as session:
        session.add(Token(
            token=token,
            user_id=user_id,
            expires_at=time.time() + _TOKEN_TTL_SECONDS,
        ))
    return token


def resolve_token(token: str) -> Optional[dict]:
    if not token:
        return None
    with session_scope() as session:
        row = session.get(Token, token)
        if not row:
            return None
        if row.expires_at < time.time():
            session.delete(row)
            return None
        user = session.get(User, row.user_id)
        return _user_to_dict(user) if user else None


def revoke_token(token: str) -> None:
    if not token:
        return
    with session_scope() as session:
        row = session.get(Token, token)
        if row:
            session.delete(row)


# ---------------------------------------------------------------------------
# verification codes (stored in DB so they survive restarts)
# ---------------------------------------------------------------------------

def generate_code(key: str) -> str:
    code = f"{secrets.randbelow(1000000):06d}"
    with session_scope() as session:
        existing = session.get(VerifyCode, key)
        if existing:
            existing.code = code
            existing.expires_at = time.time() + _CODE_TTL_SECONDS
        else:
            session.add(VerifyCode(
                key=key,
                code=code,
                expires_at=time.time() + _CODE_TTL_SECONDS,
            ))
    return code


def verify_code(key: str, code: str) -> bool:
    with session_scope() as session:
        row = session.get(VerifyCode, key)
        if not row:
            return False
        if row.expires_at < time.time():
            session.delete(row)
            return False
        if row.code != code:
            return False
        session.delete(row)
        return True


# ---------------------------------------------------------------------------
# JSON -> SQLite migration (one-shot, idempotent)
# ---------------------------------------------------------------------------

def _migrate_json_to_sqlite() -> None:
    """Best-effort import of legacy ``data/users.json`` + ``data/tokens.json``
    into SQLite. No-op if JSON files are missing or the users table already
    has data.
    """
    import json
    import os

    from .config import BASE_DIR

    data_dir = os.path.join(BASE_DIR, "data")
    users_file = os.path.join(data_dir, "users.json")
    tokens_file = os.path.join(data_dir, "tokens.json")

    def _load(path: str) -> Dict:
        if not os.path.exists(path):
            return {}
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return {}

    users_data = _load(users_file)
    tokens_data = _load(tokens_file)
    if not users_data and not tokens_data:
        return

    with session_scope() as session:
        already = session.scalar(select(User).limit(1))
        if already:
            return

        valid_user_ids = set()
        for uid, u in users_data.items():
            session.add(User(
                id=uid,
                email=u.get("email"),
                phone=u.get("phone"),
                name=u.get("name"),
                avatar=u.get("avatar"),
                password_hash=u.get("password_hash"),
                created_at=u.get("created_at") or time.time(),
            ))
            valid_user_ids.add(uid)
            for link in u.get("oauth", []) or []:
                if link.get("provider") and link.get("uid"):
                    session.add(OAuthLink(
                        user_id=uid,
                        provider=link["provider"],
                        uid=link["uid"],
                    ))
        session.flush()  # users must be persisted before tokens (FK)

        for token, meta in tokens_data.items():
            if not meta:
                continue
            uid = meta.get("user_id")
            if uid not in valid_user_ids:
                continue
            session.add(Token(
                token=token,
                user_id=uid,
                expires_at=meta.get("expires_at") or (time.time() + _TOKEN_TTL_SECONDS),
            ))

    for path in (users_file, tokens_file):
        if os.path.exists(path):
            try:
                os.replace(path, path + ".migrated")
            except OSError:
                pass
