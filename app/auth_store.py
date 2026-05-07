"""Simple JSON-file-based user store and token manager.

This is intentionally lightweight — no real database. Suitable for demo / dev.
"""
from __future__ import annotations

import json
import os
import secrets
import threading
import time
import uuid
from typing import Dict, Optional

from werkzeug.security import check_password_hash, generate_password_hash

from .config import BASE_DIR

_DATA_DIR = os.path.join(BASE_DIR, "data")
os.makedirs(_DATA_DIR, exist_ok=True)

_USERS_FILE = os.path.join(_DATA_DIR, "users.json")
_TOKENS_FILE = os.path.join(_DATA_DIR, "tokens.json")

_lock = threading.RLock()

# in-memory verification codes: key -> {code, expires_at}
_codes: Dict[str, Dict[str, float]] = {}
_CODE_TTL_SECONDS = 5 * 60
_TOKEN_TTL_SECONDS = 7 * 24 * 3600


def _load(path: str) -> dict:
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _save(path: str, data: dict) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def _public_user(user: dict) -> dict:
    return {
        "id": user["id"],
        "email": user.get("email"),
        "phone": user.get("phone"),
        "name": user.get("name"),
        "avatar": user.get("avatar"),
        "providers": user.get("providers", []),
    }


# --- users -----------------------------------------------------------------

def _find_user(users: dict, *, email: Optional[str] = None,
               phone: Optional[str] = None,
               provider: Optional[str] = None,
               provider_uid: Optional[str] = None) -> Optional[dict]:
    for user in users.values():
        if email and user.get("email") == email:
            return user
        if phone and user.get("phone") == phone:
            return user
        if provider and provider_uid:
            for link in user.get("oauth", []):
                if link.get("provider") == provider and link.get("uid") == provider_uid:
                    return user
    return None


def find_user(**kwargs) -> Optional[dict]:
    with _lock:
        users = _load(_USERS_FILE)
        user = _find_user(users, **kwargs)
        return dict(user) if user else None


def create_user(*, email: Optional[str] = None, phone: Optional[str] = None,
                password: Optional[str] = None, name: Optional[str] = None,
                avatar: Optional[str] = None,
                provider: Optional[str] = None,
                provider_uid: Optional[str] = None) -> dict:
    with _lock:
        users = _load(_USERS_FILE)
        existing = _find_user(users, email=email, phone=phone,
                              provider=provider, provider_uid=provider_uid)
        if existing:
            return dict(existing)

        user_id = uuid.uuid4().hex
        default_name = name or (email.split("@")[0] if email else None) or \
                       (f"用户{phone[-4:]}" if phone else f"User-{user_id[:6]}")
        user = {
            "id": user_id,
            "email": email,
            "phone": phone,
            "name": default_name,
            "avatar": avatar,
            "password_hash": generate_password_hash(password) if password else None,
            "oauth": [],
            "providers": [],
            "created_at": time.time(),
        }
        if provider and provider_uid:
            user["oauth"].append({"provider": provider, "uid": provider_uid})
            user["providers"] = [provider]
        users[user_id] = user
        _save(_USERS_FILE, users)
        return dict(user)


def verify_password(user: dict, password: str) -> bool:
    stored = user.get("password_hash")
    if not stored or not password:
        return False
    return check_password_hash(stored, password)


def link_oauth(user_id: str, provider: str, provider_uid: str) -> None:
    with _lock:
        users = _load(_USERS_FILE)
        user = users.get(user_id)
        if not user:
            return
        user.setdefault("oauth", [])
        if not any(o["provider"] == provider and o["uid"] == provider_uid
                   for o in user["oauth"]):
            user["oauth"].append({"provider": provider, "uid": provider_uid})
        providers = set(user.get("providers", []))
        providers.add(provider)
        user["providers"] = sorted(providers)
        users[user_id] = user
        _save(_USERS_FILE, users)


# --- tokens ----------------------------------------------------------------

def issue_token(user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    with _lock:
        tokens = _load(_TOKENS_FILE)
        tokens[token] = {"user_id": user_id, "expires_at": time.time() + _TOKEN_TTL_SECONDS}
        _save(_TOKENS_FILE, tokens)
    return token


def resolve_token(token: str) -> Optional[dict]:
    if not token:
        return None
    with _lock:
        tokens = _load(_TOKENS_FILE)
        meta = tokens.get(token)
        if not meta or meta.get("expires_at", 0) < time.time():
            if meta:
                tokens.pop(token, None)
                _save(_TOKENS_FILE, tokens)
            return None
        users = _load(_USERS_FILE)
        user = users.get(meta["user_id"])
        return dict(user) if user else None


def revoke_token(token: str) -> None:
    if not token:
        return
    with _lock:
        tokens = _load(_TOKENS_FILE)
        if token in tokens:
            tokens.pop(token, None)
            _save(_TOKENS_FILE, tokens)


def public_user(user: dict) -> dict:
    return _public_user(user)


# --- verification codes ----------------------------------------------------

def generate_code(key: str) -> str:
    code = f"{secrets.randbelow(1000000):06d}"
    _codes[key] = {"code": code, "expires_at": time.time() + _CODE_TTL_SECONDS}
    return code


def verify_code(key: str, code: str) -> bool:
    entry = _codes.get(key)
    if not entry:
        return False
    if entry["expires_at"] < time.time():
        _codes.pop(key, None)
        return False
    if entry["code"] != code:
        return False
    _codes.pop(key, None)
    return True
