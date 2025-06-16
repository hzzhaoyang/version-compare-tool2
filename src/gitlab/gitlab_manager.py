"""
GitLab API管理器 - 简化版
基于验证成功的GitLab Search API，提供高效的task检测功能
"""
import gitlab
import re
from typing import List, Dict, Any, Optional
from ..core.cache_manager import RequestCacheManager, CacheKey


class GitLabManager:
    """GitLab API管理器 - 简化版，专注于Search API"""
    
    def __init__(self, gitlab_url: str, token: str, project_id: str):
        self.gitlab_url = gitlab_url
        self.token = token
        self.project_id = project_id
        
        # 初始化GitLab连接
        self.gitlab = gitlab.Gitlab(gitlab_url, private_token=token)
        self.project = self.gitlab.projects.get(project_id)
        
        # 初始化缓存
        self.cache = RequestCacheManager()
        
        # GALAXY task正则表达式
        self.task_pattern = re.compile(r'GALAXY-(\d+)')
        
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
    
    def search_tasks_in_branch(self, branch_name: str, task_pattern: str = "GALAXY-") -> Dict[str, Dict[str, Any]]:
        """
        使用GitLab Search API搜索分支中的GALAXY tasks
        这是经过验证的高效方法
        """
        cache_key = f"search_tasks:{branch_name}:{task_pattern}"
        
        cached_result = self.cache.get(cache_key)
        if cached_result is not None:
            print(f"📦 使用缓存的搜索结果: {branch_name}")
            return cached_result
        
        print(f"🔍 使用Search API搜索分支 {branch_name} 中的 {task_pattern} tasks...")
        
        try:
            # 使用GitLab Search API直接搜索包含GALAXY-的commits
            search_results = self.project.search(
                scope='commits',
                search=task_pattern,
                ref=branch_name
            )
            
            # 提取并去重tasks
            found_tasks = {}
            
            for commit in search_results:
                commit_message = commit.get('message', '')
                matches = self.task_pattern.findall(commit_message)
                
                for match in matches:
                    task_id = f"GALAXY-{match}"
                    if task_id not in found_tasks:
                        found_tasks[task_id] = {
                            'task_id': task_id,
                            'commit_id': commit.get('id'),
                            'short_id': commit.get('short_id'),
                            'message': commit_message,
                            'author_name': commit.get('author_name', ''),
                            'committed_date': commit.get('committed_date', ''),
                            'first_found_in': branch_name
                        }
            
            print(f"✅ 在分支 {branch_name} 中找到 {len(found_tasks)} 个唯一tasks")
            self.cache.set(cache_key, found_tasks)
            return found_tasks
            
        except Exception as e:
            print(f"❌ Search API搜索失败: {e}")
            return {}
    
    def search_specific_tasks(self, task_ids: List[str], branch_name: str = None) -> Dict[str, Dict[str, Any]]:
        """
        精确搜索特定的task IDs
        经过验证，这是最高效的方法
        """
        if not task_ids:
            return {}
        
        print(f"🎯 精确搜索 {len(task_ids)} 个特定tasks" + (f" 在分支 {branch_name}" if branch_name else ""))
        
        found_tasks = {}
        
        for task_id in task_ids:
            cache_key = f"specific_task:{task_id}:{branch_name or 'all'}"
            
            cached_result = self.cache.get(cache_key)
            if cached_result is not None:
                if cached_result:  # 不是空结果
                    found_tasks[task_id] = cached_result
                continue
            
            try:
                # 搜索特定task
                search_params = {
                    'scope': 'commits',
                    'search': task_id
                }
                if branch_name:
                    search_params['ref'] = branch_name
                
                search_results = self.project.search(**search_params)
                
                if search_results:
                    # 找到匹配的commit
                    commit = search_results[0]  # 取第一个结果
                    task_info = {
                        'task_id': task_id,
                        'commit_id': commit.get('id'),
                        'short_id': commit.get('short_id'),
                        'message': commit.get('message', ''),
                        'author_name': commit.get('author_name', ''),
                        'committed_date': commit.get('committed_date', ''),
                        'found_in': branch_name or 'global'
                    }
                    found_tasks[task_id] = task_info
                    self.cache.set(cache_key, task_info)
                else:
                    # 未找到，缓存空结果
                    self.cache.set(cache_key, None)
                    
            except Exception as e:
                print(f"搜索 {task_id} 失败: {e}")
                self.cache.set(cache_key, None)
        
        print(f"🔍 精确搜索完成：找到 {len(found_tasks)}/{len(task_ids)} 个tasks")
        return found_tasks
    
    def extract_tasks_from_commits(self, commits: List[Dict[str, Any]]) -> List[str]:
        """从commits中提取task IDs"""
        tasks = set()
        
        for commit in commits:
            commit_message = commit.get('message', '')
            matches = self.task_pattern.findall(commit_message)
            tasks.update(f"GALAXY-{match}" for match in matches)
        
        return sorted(list(tasks))
    
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
    
    def finish_request(self) -> Dict[str, Any]:
        """完成请求，返回缓存统计"""
        return self.cache.get_stats()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return self.cache.get_stats()


class GitLabAPIError(Exception):
    """GitLab API基础异常"""
    pass


class GitLabConnectionError(GitLabAPIError):
    """GitLab连接异常"""
    pass


class GitLabProjectNotFoundError(GitLabAPIError):
    """GitLab项目未找到异常"""
    pass 