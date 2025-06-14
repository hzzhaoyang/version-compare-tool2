"""
GitLab API管理器
集成缓存功能，提供高效的GitLab数据访问
"""
import gitlab
import time
from typing import List, Dict, Any, Optional
from ..core.cache_manager import RequestCacheManager, CacheKey


class GitLabManager:
    """GitLab API管理器"""
    
    def __init__(self, gitlab_url: str, token: str, project_id: str):
        self.gitlab_url = gitlab_url
        self.token = token
        self.project_id = project_id
        
        # 初始化GitLab连接
        self.gitlab = gitlab.Gitlab(gitlab_url, private_token=token)
        self.project = self.gitlab.projects.get(project_id)
        
        # 初始化缓存
        self.cache = RequestCacheManager()
        
        print(f"GitLab连接已建立: {gitlab_url}, 项目ID: {project_id}")
    
    def get_version_diff(self, from_version: str, to_version: str) -> List[Dict[str, Any]]:
        """获取版本差异（带缓存）"""
        cache_key = CacheKey.version_diff(from_version, to_version)
        
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        try:
            print(f"正在获取版本差异: {from_version} -> {to_version}")
            comparison = self.project.repository_compare(
                from_=from_version, 
                to=to_version
            )
            diff_commits = comparison.get('commits', [])
            
            # 转换为字典格式，便于处理
            commits_data = []
            for commit in diff_commits:
                commits_data.append({
                    'id': commit.get('id'),
                    'message': commit.get('message', ''),
                    'author_name': commit.get('author_name', ''),
                    'committed_date': commit.get('committed_date', ''),
                    'short_id': commit.get('short_id', '')
                })
            
            self.cache.set(cache_key, commits_data)
            print(f"获取到 {len(commits_data)} 个差异commits")
            return commits_data
            
        except Exception as e:
            print(f"获取版本差异失败: {e}")
            return []
    
    def get_commits_cached(self, ref_name: str, page: int = 1, per_page: int = 100) -> List[Any]:
        """带缓存的commits获取"""
        cache_key = CacheKey.commits(ref_name, page, per_page)
        
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        try:
            commits = self.project.commits.list(
                ref_name=ref_name,
                page=page,
                per_page=per_page
            )
            
            # 转换为字典格式
            commits_data = []
            for commit in commits:
                commits_data.append({
                    'id': commit.id,
                    'message': commit.message,
                    'author_name': commit.author_name,
                    'committed_date': commit.committed_date,
                    'short_id': commit.short_id
                })
            
            self.cache.set(cache_key, commits_data)
            return commits_data
            
        except Exception as e:
            print(f"获取commits失败 (ref: {ref_name}, page: {page}): {e}")
            return []
    
    def get_all_commits_for_branch(self, branch_name: str, max_pages: int = 50) -> List[Dict[str, Any]]:
        """获取分支的所有commits（分页处理）"""
        cache_key = f"all_commits:{branch_name}:max{max_pages}"
        
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        all_commits = []
        page = 1
        
        print(f"正在获取分支 {branch_name} 的所有commits (最多{max_pages}页)...")
        
        while page <= max_pages:
            commits = self.get_commits_cached(branch_name, page, 100)
            
            if not commits:
                break
            
            all_commits.extend(commits)
            page += 1
            
            # 避免过于频繁的API调用
            if page % 10 == 0:
                time.sleep(0.1)
        
        self.cache.set(cache_key, all_commits)
        print(f"分支 {branch_name} 共获取到 {len(all_commits)} 个commits")
        return all_commits
    
    def get_project_tags(self) -> List[str]:
        """获取项目标签（带缓存）"""
        cache_key = CacheKey.project_tags(self.project_id)
        
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            return cached_result
        
        try:
            tags = self.project.tags.list(all=True)
            tag_names = [tag.name for tag in tags]
            
            self.cache.set(cache_key, tag_names)
            print(f"获取到 {len(tag_names)} 个项目标签")
            return tag_names
            
        except Exception as e:
            print(f"获取项目标签失败: {e}")
            return []
    
    def search_commits(self, query: str, ref: str = None) -> List[Dict[str, Any]]:
        """搜索commits（GitLab Search API）"""
        try:
            search_results = self.project.search(
                scope='commits',
                search=query,
                ref=ref
            )
            
            # 转换为统一格式
            results = []
            for result in search_results:
                results.append({
                    'id': result.get('id'),
                    'message': result.get('message', ''),
                    'author_name': result.get('author_name', ''),
                    'committed_date': result.get('committed_date', ''),
                    'short_id': result.get('short_id', '')
                })
            
            return results
            
        except Exception as e:
            print(f"搜索commits失败 (query: {query}): {e}")
            return []
    
    def finish_request(self) -> Dict[str, Any]:
        """请求结束时的清理工作"""
        return self.cache.clear_and_report()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return self.cache.get_stats()


class GitLabAPIError(Exception):
    """GitLab API错误"""
    pass


class GitLabConnectionError(GitLabAPIError):
    """GitLab连接错误"""
    pass


class GitLabProjectNotFoundError(GitLabAPIError):
    """GitLab项目未找到错误"""
    pass 