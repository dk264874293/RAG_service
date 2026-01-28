# utils/cache_manager.py
import time
import pickle
import hashlib
import logging
from typing import Any, Optional, Dict, List
from dataclasses import dataclass
from datetime import datetime, timedelta
from collections import OrderedDict
import threading

@dataclass
class CacheEntry:
    value: Any
    timestamp: float
    access_count: int = 0
    size: int = 0

class CacheManager:
    """缓存管理器，支持内存缓存和持久化"""
    
    def __init__(self, 
                 ttl: int = 3600,  # 生存时间（秒）
                 max_size: int = 1000,  # 最大缓存项数
                 max_memory_mb: int = 100,  # 最大内存使用（MB）
                 persistent: bool = False,
                 cache_dir: Optional[str] = None):
        
        self.logger = logging.getLogger(__name__)
        self.ttl = ttl
        self.max_size = max_size
        self.max_memory_bytes = max_memory_mb * 1024 * 1024
        
        # 使用OrderedDict实现LRU
        self.cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self.current_memory = 0
        self.lock = threading.RLock()
        
        # 持久化缓存
        self.persistent = persistent
        self.cache_dir = cache_dir
        if persistent and cache_dir:
            import os
            os.makedirs(cache_dir, exist_ok=True)
            self._load_persistent_cache()
        
        # 启动清理线程
        self._start_cleanup_thread()
    
    def _start_cleanup_thread(self):
        """启动定期清理线程"""
        def cleanup_loop():
            while True:
                time.sleep(60)  # 每分钟清理一次
                self.cleanup()
        
        cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        cleanup_thread.start()
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取缓存值"""
        with self.lock:
            if key in self.cache:
                entry = self.cache[key]
                
                # 检查是否过期
                if time.time() - entry.timestamp > self.ttl:
                    self._remove_entry(key)
                    return default
                
                # 更新访问时间和计数
                entry.access_count += 1
                self.cache.move_to_end(key)  # 移到末尾（最近使用）
                
                return entry.value
            
            # 检查持久化缓存
            if self.persistent:
                return self._get_persistent(key, default)
            
            return default
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """设置缓存值"""
        with self.lock:
            # 计算值大小
            value_size = self._calculate_size(value)
            
            # 检查是否超出内存限制
            if self.current_memory + value_size > self.max_memory_bytes:
                self._evict_entries(value_size)
            
            # 如果已经存在，先移除旧值
            if key in self.cache:
                self._remove_entry(key)
            
            # 创建缓存条目
            entry = CacheEntry(
                value=value,
                timestamp=time.time(),
                access_count=1,
                size=value_size
            )
            
            # 添加到缓存
            self.cache[key] = entry
            self.current_memory += value_size
            
            # 维护最大大小
            if len(self.cache) > self.max_size:
                self._evict_entries(0)
            
            # 持久化
            if self.persistent:
                self._set_persistent(key, value, ttl or self.ttl)
            
            return True
    
    def delete(self, key: str) -> bool:
        """删除缓存项"""
        with self.lock:
            if key in self.cache:
                self._remove_entry(key)
            
            if self.persistent:
                self._delete_persistent(key)
            
            return True
    
    def clear(self):
        """清空缓存"""
        with self.lock:
            self.cache.clear()
            self.current_memory = 0
            
            if self.persistent:
                self._clear_persistent()
    
    def cleanup(self):
        """清理过期缓存"""
        with self.lock:
            current_time = time.time()
            keys_to_remove = []
            
            for key, entry in self.cache.items():
                if current_time - entry.timestamp > self.ttl:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                self._remove_entry(key)
            
            # 清理持久化缓存
            if self.persistent:
                self._cleanup_persistent()
            
            if keys_to_remove:
                self.logger.debug(f"Cleaned up {len(keys_to_remove)} expired cache entries")
    
    def stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        with self.lock:
            total_entries = len(self.cache)
            memory_usage_mb = self.current_memory / (1024 * 1024)
            
            # 计算命中率（需要记录统计）
            if hasattr(self, 'hit_count') and hasattr(self, 'miss_count'):
                total = self.hit_count + self.miss_count
                hit_rate = self.hit_count / total if total > 0 else 0
            else:
                hit_rate = 0
            
            return {
                'total_entries': total_entries,
                'memory_usage_mb': round(memory_usage_mb, 2),
                'hit_rate': round(hit_rate, 4),
                'max_size': self.max_size,
                'ttl_seconds': self.ttl
            }
    
    def _remove_entry(self, key: str):
        """移除缓存条目"""
        if key in self.cache:
            entry = self.cache[key]
            self.current_memory -= entry.size
            del self.cache[key]
    
    def _evict_entries(self, required_space: int):
        """淘汰缓存项以释放空间"""
        # LRU淘汰策略：移除最久未使用的
        while (self.current_memory + required_space > self.max_memory_bytes and 
               len(self.cache) > 0):
            # 移除第一个（最久未使用）
            key, entry = self.cache.popitem(last=False)
            self.current_memory -= entry.size
    
    def _calculate_size(self, value: Any) -> int:
        """估算对象大小"""
        try:
            # 使用pickle估算大小
            pickled = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
            return len(pickled)
        except:
            # 如果无法pickle，返回一个估计值
            return 1024  # 默认1KB
    
    # 持久化缓存方法
    def _get_persistent(self, key: str, default: Any = None) -> Any:
        """从持久化缓存获取"""
        if not self.cache_dir:
            return default
        
        try:
            import os
            import json
            
            cache_file = os.path.join(self.cache_dir, f"{key}.cache")
            
            if os.path.exists(cache_file):
                # 检查是否过期
                meta_file = os.path.join(self.cache_dir, f"{key}.meta")
                if os.path.exists(meta_file):
                    with open(meta_file, 'r') as f:
                        meta = json.load(f)
                    
                    if time.time() - meta['timestamp'] > meta['ttl']:
                        os.remove(cache_file)
                        os.remove(meta_file)
                        return default
                
                # 读取缓存
                with open(cache_file, 'rb') as f:
                    return pickle.load(f)
        
        except Exception as e:
            self.logger.error(f"Failed to read persistent cache: {e}")
        
        return default
    
    def _set_persistent(self, key: str, value: Any, ttl: int):
        """保存到持久化缓存"""
        if not self.cache_dir:
            return
        
        try:
            import os
            import json
            
            cache_file = os.path.join(self.cache_dir, f"{key}.cache")
            meta_file = os.path.join(self.cache_dir, f"{key}.meta")
            
            # 保存缓存数据
            with open(cache_file, 'wb') as f:
                pickle.dump(value, f, protocol=pickle.HIGHEST_PROTOCOL)
            
            # 保存元数据
            meta = {
                'timestamp': time.time(),
                'ttl': ttl,
                'key': key
            }
            with open(meta_file, 'w') as f:
                json.dump(meta, f)
        
        except Exception as e:
            self.logger.error(f"Failed to write persistent cache: {e}")
    
    def _delete_persistent(self, key: str):
        """删除持久化缓存"""
        if not self.cache_dir:
            return
        
        try:
            import os
            cache_file = os.path.join(self.cache_dir, f"{key}.cache")
            meta_file = os.path.join(self.cache_dir, f"{key}.meta")
            
            if os.path.exists(cache_file):
                os.remove(cache_file)
            if os.path.exists(meta_file):
                os.remove(meta_file)
        
        except Exception as e:
            self.logger.error(f"Failed to delete persistent cache: {e}")
    
    def _load_persistent_cache(self):
        """加载持久化缓存到内存"""
        if not self.cache_dir:
            return
        
        try:
            import os
            import json
            
            # 只加载最近使用的N个文件
            cache_files = []
            for fname in os.listdir(self.cache_dir):
                if fname.endswith('.meta'):
                    meta_file = os.path.join(self.cache_dir, fname)
                    try:
                        with open(meta_file, 'r') as f:
                            meta = json.load(f)
                        
                        # 检查是否过期
                        if time.time() - meta['timestamp'] <= meta['ttl']:
                            cache_files.append((meta['timestamp'], meta['key']))
                    except:
                        continue
            
            # 按时间戳排序，取最新的
            cache_files.sort(reverse=True)
            cache_files = cache_files[:self.max_size // 2]  # 加载一半的最大容量
            
            for timestamp, key in cache_files:
                value = self._get_persistent(key)
                if value is not None:
                    # 不设置ttl，因为已经检查过过期
                    self.set(key, value, ttl=999999)
        
        except Exception as e:
            self.logger.error(f"Failed to load persistent cache: {e}")
    
    def _cleanup_persistent(self):
        """清理过期持久化缓存"""
        if not self.cache_dir:
            return
        
        try:
            import os
            import json
            
            current_time = time.time()
            
            for fname in os.listdir(self.cache_dir):
                if fname.endswith('.meta'):
                    meta_file = os.path.join(self.cache_dir, fname)
                    try:
                        with open(meta_file, 'r') as f:
                            meta = json.load(f)
                        
                        if current_time - meta['timestamp'] > meta['ttl']:
                            key = meta['key']
                            self._delete_persistent(key)
                    except:
                        continue
        
        except Exception as e:
            self.logger.error(f"Failed to cleanup persistent cache: {e}")
    
    def _clear_persistent(self):
        """清空持久化缓存"""
        if not self.cache_dir:
            return
        
        try:
            import os
            import shutil
            shutil.rmtree(self.cache_dir)
            os.makedirs(self.cache_dir, exist_ok=True)
        except Exception as e:
            self.logger.error(f"Failed to clear persistent cache: {e}")