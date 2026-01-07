"""
Advanced caching system for API responses and computed data
"""
import asyncio
import json
import logging
from typing import Dict, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import hashlib
import pickle
import os

logger = logging.getLogger(__name__)

# Import metrics functions (with fallback if not available)
try:
    from app.core.metrics import record_cache_hit, record_cache_miss
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    
    async def record_cache_hit(cache_type: str = "memory"):
        pass
    
    async def record_cache_miss(cache_type: str = "memory"):
        pass

@dataclass
class CacheEntry:
    key: str
    value: Any
    created_at: datetime
    expires_at: Optional[datetime]
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    size_bytes: int = 0

class AdvancedCacheManager:
    """Advanced in-memory cache with TTL, LRU eviction, and persistence"""
    
    def __init__(self, max_size_mb: int = 100, default_ttl_minutes: int = 60):
        self.cache: Dict[str, CacheEntry] = {}
        self.max_size_bytes = max_size_mb * 1024 * 1024  # Convert MB to bytes
        self.current_size_bytes = 0
        self.default_ttl = timedelta(minutes=default_ttl_minutes)
        self.cache_file = "cache_data.pkl"
        self._cleanup_task_started = False
        
        # Load cache from disk if exists
        self._load_cache()
    
    def _ensure_cleanup_task(self):
        """Ensure cleanup task is started (called when event loop is available)"""
        if not self._cleanup_task_started:
            try:
                asyncio.create_task(self._cleanup_task())
                self._cleanup_task_started = True
            except RuntimeError:
                # No event loop running, will try again later
                pass
    
    def _calculate_size(self, value: Any) -> int:
        """Calculate approximate size of cached value in bytes"""
        try:
            if isinstance(value, (str, int, float, bool)):
                return len(str(value).encode('utf-8'))
            elif isinstance(value, (list, dict)):
                return len(json.dumps(value, default=str).encode('utf-8'))
            else:
                return len(pickle.dumps(value))
        except:
            return 1024  # Default 1KB if calculation fails
    
    def _generate_key(self, prefix: str, **kwargs) -> str:
        """Generate cache key from prefix and parameters"""
        # Sort kwargs for consistent key generation
        sorted_params = sorted(kwargs.items())
        param_str = json.dumps(sorted_params, sort_keys=True, default=str)
        key_hash = hashlib.md5(param_str.encode()).hexdigest()[:8]
        return f"{prefix}:{key_hash}"
    
    def _evict_lru(self, required_space: int):
        """Evict least recently used items to make space"""
        if not self.cache:
            return
        
        # Sort by last_accessed (oldest first), then by access_count (least used first)
        sorted_entries = sorted(
            self.cache.values(),
            key=lambda x: (x.last_accessed or x.created_at, x.access_count)
        )
        
        freed_space = 0
        keys_to_remove = []
        
        for entry in sorted_entries:
            if freed_space >= required_space:
                break
            
            keys_to_remove.append(entry.key)
            freed_space += entry.size_bytes
        
        for key in keys_to_remove:
            self._remove_entry(key)
        
        logger.info(f"Evicted {len(keys_to_remove)} cache entries, freed {freed_space} bytes")
    
    def _remove_entry(self, key: str):
        """Remove a cache entry and update size tracking"""
        if key in self.cache:
            entry = self.cache[key]
            self.current_size_bytes -= entry.size_bytes
            del self.cache[key]
    
    def _is_expired(self, entry: CacheEntry) -> bool:
        """Check if cache entry is expired"""
        if entry.expires_at is None:
            return False
        return datetime.now() > entry.expires_at
    
    def set(self, key: str, value: Any, ttl_minutes: Optional[int] = None) -> bool:
        """Set a cache entry with optional TTL"""
        # Ensure cleanup task is running
        self._ensure_cleanup_task()
        
        try:
            size_bytes = self._calculate_size(value)
            
            # Check if we need to make space
            if self.current_size_bytes + size_bytes > self.max_size_bytes:
                required_space = size_bytes - (self.max_size_bytes - self.current_size_bytes)
                self._evict_lru(required_space)
            
            # Remove existing entry if it exists
            if key in self.cache:
                self._remove_entry(key)
            
            # Calculate expiration
            expires_at = None
            if ttl_minutes is not None:
                expires_at = datetime.now() + timedelta(minutes=ttl_minutes)
            elif self.default_ttl:
                expires_at = datetime.now() + self.default_ttl
            
            # Create new entry
            entry = CacheEntry(
                key=key,
                value=value,
                created_at=datetime.now(),
                expires_at=expires_at,
                size_bytes=size_bytes
            )
            
            self.cache[key] = entry
            self.current_size_bytes += size_bytes
            
            return True
            
        except Exception as e:
            logger.error(f"Error setting cache entry {key}: {e}")
            return False
    
    def get(self, key: str) -> Optional[Any]:
        """Get a cache entry, returns None if not found or expired"""
        if key not in self.cache:
            # Record cache miss
            if METRICS_AVAILABLE:
                asyncio.create_task(record_cache_miss("memory"))
            return None
        
        entry = self.cache[key]
        
        # Check if expired
        if self._is_expired(entry):
            self._remove_entry(key)
            # Record cache miss for expired entries
            if METRICS_AVAILABLE:
                asyncio.create_task(record_cache_miss("memory"))
            return None
        
        # Update access statistics
        entry.access_count += 1
        entry.last_accessed = datetime.now()
        
        # Record cache hit
        if METRICS_AVAILABLE:
            asyncio.create_task(record_cache_hit("memory"))
        
        return entry.value
    
    def get_or_set(self, key: str, factory_func: Callable, ttl_minutes: Optional[int] = None) -> Any:
        """Get from cache or set using factory function if not found"""
        value = self.get(key)
        if value is not None:
            return value
        
        # Generate new value
        try:
            new_value = factory_func()
            self.set(key, new_value, ttl_minutes)
            return new_value
        except Exception as e:
            logger.error(f"Error in cache factory function for key {key}: {e}")
            return None
    
    async def get_or_set_async(self, key: str, factory_func: Callable, ttl_minutes: Optional[int] = None) -> Any:
        """Async version of get_or_set"""
        value = self.get(key)
        if value is not None:
            return value
        
        # Generate new value
        try:
            if asyncio.iscoroutinefunction(factory_func):
                new_value = await factory_func()
            else:
                new_value = factory_func()
            
            self.set(key, new_value, ttl_minutes)
            return new_value
        except Exception as e:
            logger.error(f"Error in async cache factory function for key {key}: {e}")
            return None
    
    def delete(self, key: str) -> bool:
        """Delete a cache entry"""
        if key in self.cache:
            self._remove_entry(key)
            return True
        return False
    
    def clear(self):
        """Clear all cache entries"""
        self.cache.clear()
        self.current_size_bytes = 0
        logger.info("Cache cleared")
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        total_entries = len(self.cache)
        expired_entries = sum(1 for entry in self.cache.values() if self._is_expired(entry))
        
        return {
            'total_entries': total_entries,
            'expired_entries': expired_entries,
            'active_entries': total_entries - expired_entries,
            'current_size_mb': round(self.current_size_bytes / (1024 * 1024), 2),
            'max_size_mb': round(self.max_size_bytes / (1024 * 1024), 2),
            'utilization_percent': round((self.current_size_bytes / self.max_size_bytes) * 100, 2)
        }
    
    def _save_cache(self):
        """Save cache to disk"""
        try:
            # Only save non-expired entries
            active_cache = {
                key: entry for key, entry in self.cache.items()
                if not self._is_expired(entry)
            }
            
            with open(self.cache_file, 'wb') as f:
                pickle.dump(active_cache, f)
            
            logger.debug(f"Saved {len(active_cache)} cache entries to disk")
        except Exception as e:
            logger.error(f"Error saving cache to disk: {e}")
    
    def _load_cache(self):
        """Load cache from disk"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'rb') as f:
                    loaded_cache = pickle.load(f)
                
                # Filter out expired entries and update size tracking
                for key, entry in loaded_cache.items():
                    if not self._is_expired(entry):
                        self.cache[key] = entry
                        self.current_size_bytes += entry.size_bytes
                
                logger.info(f"Loaded {len(self.cache)} cache entries from disk")
        except Exception as e:
            logger.error(f"Error loading cache from disk: {e}")
    
    async def _cleanup_task(self):
        """Background task to clean up expired entries and save cache"""
        while True:
            try:
                # Remove expired entries
                expired_keys = [
                    key for key, entry in self.cache.items()
                    if self._is_expired(entry)
                ]
                
                for key in expired_keys:
                    self._remove_entry(key)
                
                if expired_keys:
                    logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")
                
                # Save cache to disk every 5 minutes
                self._save_cache()
                
            except Exception as e:
                logger.error(f"Error in cache cleanup task: {e}")
            
            # Run cleanup every 5 minutes
            await asyncio.sleep(300)

# Global cache manager instance
cache_manager = AdvancedCacheManager()

# Cache decorators for common use cases
def cache_result(key_prefix: str, ttl_minutes: int = 60):
    """Decorator to cache function results"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = cache_manager._generate_key(key_prefix, args=args, kwargs=kwargs)
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl_minutes)
            return result
        
        return wrapper
    return decorator

def cache_async_result(key_prefix: str, ttl_minutes: int = 60):
    """Decorator to cache async function results"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Generate cache key
            cache_key = cache_manager._generate_key(key_prefix, args=args, kwargs=kwargs)
            
            # Try to get from cache
            cached_result = cache_manager.get(cache_key)
            if cached_result is not None:
                return cached_result
            
            # Execute function and cache result
            result = await func(*args, **kwargs)
            cache_manager.set(cache_key, result, ttl_minutes)
            return result
        
        return wrapper
    return decorator