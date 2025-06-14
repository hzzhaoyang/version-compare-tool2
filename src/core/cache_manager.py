"""
请求级缓存管理器
避免同一请求内重复API调用，大幅提升性能
"""
import time
from typing import Any, Optional, Dict


class RequestCacheManager:
    """简单高效的请求级缓存"""
    
    def __init__(self):
        self.cache: Dict[str, Any] = {}
        self.stats = {
            'hits': 0, 
            'misses': 0, 
            'api_calls_saved': 0,
            'start_time': time.time()
        }
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        if key in self.cache:
            self.stats['hits'] += 1
            self.stats['api_calls_saved'] += 1
            return self.cache[key]
        
        self.stats['misses'] += 1
        return None
    
    def set(self, key: str, value: Any) -> None:
        """设置缓存值"""
        self.cache[key] = value
    
    def has(self, key: str) -> bool:
        """检查缓存是否存在"""
        return key in self.cache
    
    def clear_and_report(self) -> Dict[str, Any]:
        """清理缓存并报告统计"""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        duration = time.time() - self.stats['start_time']
        
        report = {
            'cache_size': len(self.cache),
            'hit_rate': round(hit_rate, 1),
            'api_calls_saved': self.stats['api_calls_saved'],
            'total_requests': total_requests,
            'duration_seconds': round(duration, 2)
        }
        
        print(f"缓存统计: 命中率 {hit_rate:.1f}%, 节省API调用 {self.stats['api_calls_saved']} 次")
        
        # 清理缓存
        self.cache.clear()
        self.stats = {
            'hits': 0, 
            'misses': 0, 
            'api_calls_saved': 0,
            'start_time': time.time()
        }
        
        return report
    
    def get_stats(self) -> Dict[str, Any]:
        """获取当前统计信息"""
        total_requests = self.stats['hits'] + self.stats['misses']
        hit_rate = (self.stats['hits'] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            'cache_size': len(self.cache),
            'hit_rate': round(hit_rate, 1),
            'hits': self.stats['hits'],
            'misses': self.stats['misses'],
            'api_calls_saved': self.stats['api_calls_saved']
        }


class CacheKey:
    """缓存键生成器，确保键的一致性"""
    
    @staticmethod
    def version_diff(from_version: str, to_version: str) -> str:
        """版本差异缓存键"""
        return f"diff:{from_version}:{to_version}"
    
    @staticmethod
    def branch_tasks(branch_name: str) -> str:
        """分支tasks缓存键"""
        return f"branch_tasks:{branch_name}"
    
    @staticmethod
    def commits(ref_name: str, page: int = 1, per_page: int = 100) -> str:
        """commits缓存键"""
        return f"commits:{ref_name}:p{page}:n{per_page}"
    
    @staticmethod
    def version_compare(from_version: str, to_version: str) -> str:
        """版本比较缓存键"""
        return f"compare:{from_version}:{to_version}"
    
    @staticmethod
    def project_tags(project_id: str) -> str:
        """项目标签缓存键"""
        return f"tags:{project_id}" 