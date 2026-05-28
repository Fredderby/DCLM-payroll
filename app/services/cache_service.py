"""Simple in-memory cache to reduce remote DB queries."""
import time

_cache = {}

def get_cache(key: str):
    """Get cached value if not expired."""
    if key in _cache:
        entry = _cache[key]
        if time.time() < entry["expires"]:
            return entry["value"]
        del _cache[key]
    return None

def set_cache(key: str, value, ttl_seconds: int = 60):
    """Cache a value with TTL in seconds."""
    _cache[key] = {
        "value": value,
        "expires": time.time() + ttl_seconds
    }

def clear_cache():
    """Clear all cached data."""
    _cache.clear()
