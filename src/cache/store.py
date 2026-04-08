"""In-memory cache with TTL for POC."""

import time
import hashlib
import json
from typing import Optional, Any
from dataclasses import dataclass, field
from src.api.schemas import Address


@dataclass
class CacheEntry:
    """Cache entry with value and expiration timestamp."""
    value: Any
    expires_at: float


class InMemoryCache:
    """Simple in-memory cache with TTL support."""
    
    def __init__(self):
        """Initialize empty cache."""
        self._store: dict[str, CacheEntry] = {}
    
    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if cache entry has expired."""
        return time.time() > entry.expires_at
    
    def _cleanup_expired(self) -> None:
        """Remove expired entries from cache."""
        expired_keys = [
            key for key, entry in self._store.items()
            if self._is_expired(entry)
        ]
        for key in expired_keys:
            del self._store[key]
    
    async def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        entry = self._store.get(key)
        
        if entry is None:
            return None
        
        if self._is_expired(entry):
            del self._store[key]
            return None
        
        return entry.value
    
    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        """
        Store value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live in seconds
        """
        expires_at = time.time() + ttl_seconds
        self._store[key] = CacheEntry(value=value, expires_at=expires_at)
        
        # Cleanup expired entries periodically (simple approach)
        if len(self._store) % 100 == 0:
            self._cleanup_expired()
    
    async def delete(self, key: str) -> None:
        """Delete key from cache."""
        if key in self._store:
            del self._store[key]
    
    def clear(self) -> None:
        """Clear all cache entries."""
        self._store.clear()


def generate_address_cache_key(address: Address) -> str:
    """
    Generate cache key from address using SHA-256 hash.
    
    Args:
        address: Address to hash
        
    Returns:
        Hex digest of address hash
    """
    # Normalize address for consistent hashing
    normalized = f"{address.street.lower().strip()},{address.city.lower().strip()},{address.state.lower()},{(address.zip or '').lower().strip()}"
    return hashlib.sha256(normalized.encode()).hexdigest()
