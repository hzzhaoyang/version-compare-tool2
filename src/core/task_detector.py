"""
核心Task丢失检测算法 - 简化版
基于GitLab Search API的精确检测，经过实际验证的可靠方案
"""
import time
from typing import Set, Dict, List, Any
from ..gitlab.gitlab_manager import GitLabManager
from ..core.cache_manager import CacheKey


class TaskLossDetector:
    """Task丢失检测器 - 简化版，专注于Search API核心功能"""
    
    def __init__(self, gitlab_manager: GitLabManager):
        self.gitlab_manager = gitlab_manager
        print("TaskLossDetector 初始化完成 (Search API版)")
    
    def detect_missing_tasks(self, old_version: str, new_version: str) -> Dict[str, Any]:
        """
        精确检测缺失的tasks - 基于GitLab Search API
        这是经过验证的可靠方法
        """
        print(f"🔍 开始检测版本差异: {old_version} -> {new_version}")
        start_time = time.time()
        
        try:
            # 步骤1: 获取两版本间的实际差异commits
            diff_commits = self.gitlab_manager.get_version_diff(old_version, new_version)
            
            if not diff_commits:
                return {
                    'missing_tasks': [],
                    'existing_tasks': [],
                    'total_diff_commits': 0,
                    'analysis': 'no_diff_commits',
                    'processing_time': time.time() - start_time,
                    'search_method': 'search_api'
                }
            
            # 步骤2: 从差异commits提取涉及的task_id
            candidate_tasks = self._extract_tasks_from_commits(diff_commits)
            print(f"📋 从 {len(diff_commits)} 个差异commits中提取到 {len(candidate_tasks)} 个潜在缺失task")
            
            if not candidate_tasks:
                return {
                    'missing_tasks': [],
                    'existing_tasks': [],
                    'total_diff_commits': len(diff_commits),
                    'analysis': 'no_tasks_in_diff',
                    'processing_time': time.time() - start_time,
                    'search_method': 'search_api'
                }
            
            # 步骤3: 使用Search API批量验证这些task在新版本中是否真的不存在
            print("🔎 使用Search API检查task存在性...")
            existing_tasks_info = self.gitlab_manager.search_specific_tasks(
                list(candidate_tasks), 
                new_version
            )
            
            # 步骤4: 计算真正缺失的tasks
            existing_tasks = set(existing_tasks_info.keys())
            truly_missing_tasks = candidate_tasks - existing_tasks
            
            processing_time = time.time() - start_time
            print(f"✅ 分析完成 ({processing_time:.2f}s): {len(truly_missing_tasks)} 个真正缺失, {len(existing_tasks)} 个已存在")
            
            return {
                'missing_tasks': sorted(list(truly_missing_tasks)),
                'existing_tasks': sorted(list(existing_tasks)),
                'existing_tasks_detail': existing_tasks_info,
                'total_diff_commits': len(diff_commits),
                'potentially_missing_count': len(candidate_tasks),
                'analysis': 'success',
                'processing_time': processing_time,
                'search_method': 'search_api'
            }
            
        except Exception as e:
            print(f"❌ Task检测失败: {e}")
            return {
                'missing_tasks': [],
                'existing_tasks': [],
                'error': str(e),
                'analysis': 'error',
                'processing_time': time.time() - start_time,
                'search_method': 'search_api'
            }
    
    def _extract_tasks_from_commits(self, commits: List[Dict[str, Any]]) -> Set[str]:
        """从commits中提取task IDs"""
        return set(self.gitlab_manager.extract_tasks_from_commits(commits))
    
    def search_specific_tasks_in_branch(self, task_ids: List[str], branch_name: str) -> Dict[str, Dict[str, Any]]:
        """
        精确搜索特定tasks在分支中的存在情况
        直接调用GitLab Manager的搜索功能
        """
        if not task_ids:
            return {}
        
        print(f"🎯 精确搜索模式：在分支 {branch_name} 中查找 {len(task_ids)} 个特定tasks")
        return self.gitlab_manager.search_specific_tasks(task_ids, branch_name)
    
    def analyze_task_details(self, task_ids: List[str], branch_name: str) -> Dict[str, Any]:
        """分析特定tasks的详细信息"""
        if not task_ids:
            return {}
        
        # 使用Search API获取task详情
        found_tasks = self.gitlab_manager.search_specific_tasks(task_ids, branch_name)
        
        task_details = {}
        for task_id in task_ids:
            if task_id in found_tasks:
                task_details[task_id] = found_tasks[task_id]
            else:
                task_details[task_id] = {
                    'status': 'not_found',
                    'message': f'Task {task_id} 在分支 {branch_name} 中未找到'
                }
        
        return task_details
    
    def get_task_statistics(self, commits: List[Dict[str, Any]]) -> Dict[str, Any]:
        """获取commits中的task统计信息"""
        all_tasks = self._extract_tasks_from_commits(commits)
        
        # 按task类型分类（如果有特定模式）
        task_stats = {
            'total_unique_tasks': len(all_tasks),
            'task_list': sorted(list(all_tasks)),
            'commits_with_tasks': 0,
            'commits_without_tasks': 0
        }
        
        for commit in commits:
            commit_message = commit.get('message', '')
            if self.gitlab_manager.task_pattern.search(commit_message):
                task_stats['commits_with_tasks'] += 1
            else:
                task_stats['commits_without_tasks'] += 1
        
        return task_stats
    
    def clear_cache(self) -> None:
        """清理检测器相关的缓存"""
        print("🧹 TaskLossDetector 缓存已清理")


class TaskAnalyzer:
    """Task分析器 - 简化版，提供基础分析功能"""
    
    def __init__(self, task_detector: TaskLossDetector):
        self.task_detector = task_detector
    
    def compare_task_trends(self, version_pairs: List[tuple]) -> Dict[str, Any]:
        """比较多个版本对的task趋势"""
        trends = []
        
        for from_ver, to_ver in version_pairs:
            result = self.task_detector.detect_missing_tasks(from_ver, to_ver)
            trends.append({
                'version_pair': f"{from_ver} -> {to_ver}",
                'missing_count': len(result.get('missing_tasks', [])),
                'existing_count': len(result.get('existing_tasks', [])),
                'processing_time': result.get('processing_time', 0)
            })
        
        return {
            'trends': trends,
            'summary': {
                'total_comparisons': len(trends),
                'avg_missing_tasks': sum(t['missing_count'] for t in trends) / len(trends) if trends else 0,
                'avg_processing_time': sum(t['processing_time'] for t in trends) / len(trends) if trends else 0
            }
        }
    
    def analyze_task_patterns(self, commits: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析task模式"""
        task_numbers = []
        commit_types = {}
        authors = {}
        
        for commit in commits:
            message = commit.get('message', '')
            matches = self.task_detector.gitlab_manager.task_pattern.findall(message)
            
            if matches:
                task_numbers.extend([int(num) for num in matches])
                
                # 分析commit类型（基于message前缀）
                commit_type = 'other'
                if message.startswith('feat'):
                    commit_type = 'feature'
                elif message.startswith('fix'):
                    commit_type = 'bugfix'
                elif message.startswith('docs'):
                    commit_type = 'documentation'
                
                commit_types[commit_type] = commit_types.get(commit_type, 0) + 1
                
                # 分析作者
                author = commit.get('author_name', 'Unknown')
                authors[author] = authors.get(author, 0) + 1
        
        return {
            'task_number_range': {
                'min': min(task_numbers) if task_numbers else 0,
                'max': max(task_numbers) if task_numbers else 0,
                'count': len(task_numbers)
            },
            'commit_types': commit_types,
            'top_authors': dict(sorted(authors.items(), key=lambda x: x[1], reverse=True)[:5])
        } 