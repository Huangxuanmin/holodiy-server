"""针对鉴权类敏感接口的简易内存限流。

只适用于单进程 demo / 开发环境；生产环境如需水平扩展，建议换成 Redis 等
分布式后端。
"""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Deque, Dict, Tuple

_lock = threading.Lock()
_hits: Dict[str, Deque[float]] = {}


def check(key: str, *, per_minute: int = 1, per_day: int = 10) -> Tuple[bool, str]:
    """Return (allowed, reason). `reason` is empty when allowed."""
    now = time.time()
    minute_ago = now - 60
    day_ago = now - 24 * 3600

    with _lock:
        q = _hits.setdefault(key, deque())
        while q and q[0] < day_ago:
            q.popleft()

        recent_minute = sum(1 for t in q if t >= minute_ago)
        if recent_minute >= per_minute:
            return False, "操作过于频繁，请稍后再试"
        if len(q) >= per_day:
            return False, "今日发送次数已达上限"

        q.append(now)
        return True, ""
