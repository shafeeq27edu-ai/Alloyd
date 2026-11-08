import time
import asyncio
import ipaddress
from typing import Dict, List, Tuple
from fastapi import Request, HTTPException, status
from app.config import settings

class InMemoryRateLimiter:
    def __init__(self):
        self.state: Dict[str, List[float]] = {}
        self._lock = asyncio.Lock()

    async def check(self, key: str, limit: int, window: int) -> Tuple[bool, int]:
        now = time.time()
        
        async with self._lock:
            # Clean up old timestamps
            if key in self.state:
                self.state[key] = [t for t in self.state[key] if now - t < window]
            else:
                self.state[key] = []
                
            if len(self.state[key]) >= limit:
                # Calculate retry after
                oldest = self.state[key][0]
                retry_after = int(window - (now - oldest))
                if retry_after < 1:
                    retry_after = 1
                return False, retry_after
                
            self.state[key].append(now)
            return True, 0

    async def clear_for_test(self):
        async with self._lock:
            self.state.clear()

# Global instance for the process
limiter = InMemoryRateLimiter()

def _is_trusted_proxy(host: str) -> bool:
    for entry in settings.TRUSTED_PROXIES.split(","):
        entry = entry.strip()
        if not entry:
            continue
        try:
            if ipaddress.ip_address(host) in ipaddress.ip_network(entry, strict=False):
                return True
        except ValueError:
            continue
    return False

def get_client_ip(request: Request) -> str:
    peer = request.client.host if request.client else "127.0.0.1"
    if not _is_trusted_proxy(peer):
        return peer
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return peer

async def check_rate_limit(key: str, limit: int, window: int):
    allowed, retry_after = await limiter.check(key, limit, window)
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too Many Requests",
            headers={"Retry-After": str(retry_after)}
        )
