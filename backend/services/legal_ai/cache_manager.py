"""Centralized Enterprise Cache Manager supporting TTL, LRU eviction, and Statistics tracking."""
import os
import sqlite3
import hashlib
import json
import time
from typing import Dict, Any, Optional

class CacheManager:
    _instance = None
    
    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(CacheManager, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance
        
    def __init__(self, cache_dir: str = None, max_size: int = 5000):
        if self._initialized:
            return
        if cache_dir is None:
            cache_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
                "local_storage",
                "cache"
            )
        self.cache_dir = cache_dir
        self.max_size = max_size
        os.makedirs(self.cache_dir, exist_ok=True)
        self.db_path = os.path.join(self.cache_dir, "cache_store.db")
        self._init_db()
        self._initialized = True

    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cache_store (
                cache_type TEXT,
                key TEXT,
                val TEXT,
                hits INTEGER DEFAULT 0,
                misses INTEGER DEFAULT 0,
                expire_at REAL,
                last_accessed_at REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (cache_type, key)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stats (
                cache_type TEXT PRIMARY KEY,
                hits INTEGER DEFAULT 0,
                misses INTEGER DEFAULT 0
            )
        """)
        for t in ["ocr", "embedding", "retrieval", "prompt", "slm_response"]:
            cursor.execute("INSERT OR IGNORE INTO stats (cache_type, hits, misses) VALUES (?, 0, 0)", (t,))
        conn.commit()
        conn.close()

    def get(self, cache_type: str, key: str) -> Optional[Any]:
        text_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
        now = time.time()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT val, expire_at FROM cache_store WHERE cache_type = ? AND key = ?", 
            (cache_type, text_hash)
        )
        row = cursor.fetchone()
        
        if row:
            val, expire_at = row
            # Check TTL
            if expire_at and now > expire_at:
                # Expired: invalidate it, count as miss
                cursor.execute("DELETE FROM cache_store WHERE cache_type = ? AND key = ?", (cache_type, text_hash))
                cursor.execute("UPDATE stats SET misses = misses + 1 WHERE cache_type = ?", (cache_type,))
                conn.commit()
                conn.close()
                return None
                
            # Valid cache hit
            cursor.execute(
                "UPDATE cache_store SET hits = hits + 1, last_accessed_at = ? WHERE cache_type = ? AND key = ?", 
                (now, cache_type, text_hash)
            )
            cursor.execute("UPDATE stats SET hits = hits + 1 WHERE cache_type = ?", (cache_type,))
            conn.commit()
            conn.close()
            return json.loads(val)
            
        # Cache miss
        cursor.execute("UPDATE stats SET misses = misses + 1 WHERE cache_type = ?", (cache_type,))
        conn.commit()
        conn.close()
        return None

    def set(self, cache_type: str, key: str, value: Any, ttl_seconds: int = None):
        text_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
        now = time.time()
        expire_at = (now + ttl_seconds) if ttl_seconds else None
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Enforce LRU eviction if cache size exceeds limit
        cursor.execute("SELECT COUNT(*) FROM cache_store WHERE cache_type = ?", (cache_type,))
        count = cursor.fetchone()[0]
        if count >= self.max_size:
            # Delete 10% of the oldest accessed items
            evict_count = max(1, int(self.max_size * 0.1))
            cursor.execute(
                "DELETE FROM cache_store WHERE cache_type = ? AND key IN (SELECT key FROM cache_store WHERE cache_type = ? ORDER BY last_accessed_at ASC LIMIT ?)",
                (cache_type, cache_type, evict_count)
            )
            
        cursor.execute(
            """INSERT OR REPLACE INTO cache_store 
               (cache_type, key, val, expire_at, last_accessed_at) 
               VALUES (?, ?, ?, ?, ?)""",
            (cache_type, text_hash, json.dumps(value), expire_at, now)
        )
        conn.commit()
        conn.close()

    def invalidate(self, cache_type: str, key: str):
        """Invalidate a specific cache key."""
        text_hash = hashlib.sha256(key.encode("utf-8")).hexdigest()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cache_store WHERE cache_type = ? AND key = ?", (cache_type, text_hash))
        conn.commit()
        conn.close()

    def invalidate_all(self, cache_type: str):
        """Invalidate all items of a given cache type."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cache_store WHERE cache_type = ?", (cache_type,))
        cursor.execute("UPDATE stats SET hits = 0, misses = 0 WHERE cache_type = ?", (cache_type,))
        conn.commit()
        conn.close()

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT cache_type, hits, misses FROM stats")
        rows = cursor.fetchall()
        
        # Get actual stored item count per cache type
        counts = {}
        for t in ["ocr", "embedding", "retrieval", "prompt", "slm_response"]:
            cursor.execute("SELECT COUNT(*) FROM cache_store WHERE cache_type = ?", (t,))
            counts[t] = cursor.fetchone()[0]
            
        conn.close()
        
        stats = {}
        for cache_type, hits, misses in rows:
            total = hits + misses
            hit_rate = (hits / total) if total > 0 else 0.0
            stats[cache_type] = {
                "hits": hits,
                "misses": misses,
                "hit_rate": round(hit_rate, 2),
                "item_count": counts.get(cache_type, 0)
            }
        return stats
        
    def clear_cache(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM cache_store")
        cursor.execute("UPDATE stats SET hits = 0, misses = 0")
        conn.commit()
        conn.close()
