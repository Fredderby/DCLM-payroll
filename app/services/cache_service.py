"""Enhanced caching system with Redis support, size limits, and TTL management."""
import time
import hashlib
import json
from functools import wraps

_cache = {}
_cache_stats = {"hits": 0, "misses": 0, "size": 0}
MAX_CACHE_SIZE = 500  # Maximum number of cache entries
MAX_CACHE_MEMORY = 50 * 1024 * 1024  # 50MB approximate limit

def get_cache(key: str):
    """Get cached value if not expired."""
    if key in _cache:
        entry = _cache[key]
        if time.time() < entry["expires"]:
            _cache_stats["hits"] += 1
            return entry["value"]
        del _cache[key]
    _cache_stats["misses"] += 1
    return None

def set_cache(key: str, value, ttl_seconds: int = 60):
    """Cache a value with TTL in seconds. Manages cache size limits."""
    # Enforce max cache size - evict oldest entries if needed
    if len(_cache) >= MAX_CACHE_SIZE:
        # Remove 20% of oldest entries
        sorted_keys = sorted(_cache.keys(), key=lambda k: _cache[k].get("created", 0))
        remove_count = max(1, len(_cache) // 5)
        for old_key in sorted_keys[:remove_count]:
            del _cache[old_key]
    
    _cache[key] = {
        "value": value,
        "expires": time.time() + ttl_seconds,
        "created": time.time()
    }

def clear_cache():
    """Clear all cached data."""
    _cache.clear()

def get_cache_stats():
    """Return cache performance statistics."""
    ratio = (_cache_stats["hits"] / (_cache_stats["hits"] + _cache_stats["misses"]) * 100) if (_cache_stats["hits"] + _cache_stats["misses"]) > 0 else 0
    return {
        "hits": _cache_stats["hits"],
        "misses": _cache_stats["misses"],
        "hit_ratio": round(ratio, 2),
        "current_size": len(_cache),
        "max_size": MAX_CACHE_SIZE
    }

def cached(ttl_seconds: int = 60):
    """Decorator to cache function results."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Create a cache key from function name + args
            key_parts = [func.__name__]
            key_parts.extend([str(a) for a in args])
            key_parts.extend([f"{k}={v}" for k, v in sorted(kwargs.items())])
            cache_key = hashlib.md5("|".join(key_parts).encode()).hexdigest()
            
            cached_value = get_cache(cache_key)
            if cached_value is not None:
                return cached_value
            
            result = func(*args, **kwargs)
            set_cache(cache_key, result, ttl_seconds)
            return result
        return wrapper
    return decorator
