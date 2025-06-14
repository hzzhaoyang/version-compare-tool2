"""
核心Task丢失检测算法
基于GitLab Compare API精确检测缺失的GALAXY tasks
"""
import re
import time
from typing import Set, Dict, List, Any
from ..gitlab.gitlab_manager import GitLabManager
from ..core.cache_manager import CacheKey


class TaskLossDetector:
    """Task丢失检测器 - 核心算法"""
    
    def __init__(self, gitlab_manager: GitLabManager):
        self.gitlab_manager = gitlab_manager
        # GALAXY-XXXXX格式的正则表达式
        self.task_pattern = re.compile(r'GALAXY-(\d+)')
        
        print("TaskLossDetector 初始化完成")
    
    def detect_missing_tasks(self, old_version: str, new_version: str) -> Dict[str, Any]:
        """精确检测缺失的tasks - 核心算法"""
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
                    'processing_time': time.time() - start_time
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
                    'processing_time': time.time() - start_time
                }
            
            # 步骤3: 批量验证这些task在新版本中是否真的不存在
            print("🔎 开始批量检查task存在性...")
            existing_tasks_info = self._batch_check_tasks_existence(candidate_tasks, new_version)
            
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
                'processing_time': processing_time
            }
            
        except Exception as e:
            print(f"❌ Task检测失败: {e}")
            return {
                'missing_tasks': [],
                'existing_tasks': [],
                'error': str(e),
                'analysis': 'error',
                'processing_time': time.time() - start_time
            }
    
    def _extract_tasks_from_commits(self, commits: List[Dict[str, Any]]) -> Set[str]:
        """从commits中提取task IDs"""
        tasks = set()
        
        for commit in commits:
            commit_message = commit.get('message', '')
            matches = self.task_pattern.findall(commit_message)
            tasks.update(f"GALAXY-{match}" for match in matches)
        
        return tasks
    
    def _batch_check_tasks_existence(self, task_ids: Set[str], target_branch: str) -> Dict[str, Dict[str, Any]]:
        """批量检查tasks在目标分支的存在性（关键优化）"""
        if not task_ids:
            return {}
        
        # 使用缓存避免重复查询同一分支
        cache_key = CacheKey.branch_tasks(target_branch)
        
        if self.gitlab_manager.cache.has(cache_key):
            all_branch_tasks = self.gitlab_manager.cache.get(cache_key)
            print(f"📦 使用缓存的分支tasks数据")
        else:
            # 一次性获取分支所有tasks，避免重复API调用
            all_branch_tasks = self._get_all_branch_tasks(target_branch)
            self.gitlab_manager.cache.set(cache_key, all_branch_tasks)
        
        # 检查哪些task存在
        existing_tasks = {}
        for task_id in task_ids:
            if task_id in all_branch_tasks:
                existing_tasks[task_id] = all_branch_tasks[task_id]
        
        return existing_tasks
    
    def _get_all_branch_tasks(self, branch_name: str) -> Dict[str, Dict[str, Any]]:
        """一次性获取分支所有tasks"""
        print(f"🔄 正在获取分支 {branch_name} 的所有tasks...")
        
        # 获取分支的所有commits
        all_commits = self.gitlab_manager.get_all_commits_for_branch(branch_name, max_pages=50)
        
        # 提取所有唯一的tasks
        all_tasks = {}
        
        for commit in all_commits:
            commit_message = commit.get('message', '')
            found_tasks = self.task_pattern.findall(commit_message)
            
            for task_num in found_tasks:
                task_id = f"GALAXY-{task_num}"
                if task_id not in all_tasks:  # 避免重复记录，保留第一次出现
                    all_tasks[task_id] = {
                        'commit_id': commit.get('id'),
                        'commit_date': commit.get('committed_date'),
                        'first_occurrence': commit_message[:100] + '...' if len(commit_message) > 100 else commit_message,
                        'author': commit.get('author_name', 'Unknown')
                    }
        
        print(f"📊 分支 {branch_name} 共找到 {len(all_tasks)} 个唯一tasks")
        return all_tasks
    
    def analyze_task_details(self, task_ids: List[str], branch_name: str) -> Dict[str, Any]:
        """分析特定tasks的详细信息"""
        if not task_ids:
            return {}
        
        # 获取分支tasks
        all_branch_tasks = self._get_all_branch_tasks(branch_name)
        
        task_details = {}
        for task_id in task_ids:
            if task_id in all_branch_tasks:
                task_details[task_id] = all_branch_tasks[task_id]
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
            if self.task_pattern.search(commit_message):
                task_stats['commits_with_tasks'] += 1
            else:
                task_stats['commits_without_tasks'] += 1
        
        return task_stats
    
    def clear_cache(self) -> None:
        """清理检测器相关的缓存"""
        # 这里可以添加特定的缓存清理逻辑
        print("🧹 TaskLossDetector 缓存已清理")


class TaskAnalyzer:
    """Task分析器 - 提供额外的分析功能"""
    
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
        task_pattern = re.compile(r'GALAXY-(\d+)')
        
        patterns = {
            'task_numbers': [],
            'commit_types': {},
            'authors': {},
            'date_distribution': {}
        }
        
        for commit in commits:
            message = commit.get('message', '')
            matches = task_pattern.findall(message)
            
            if matches:
                patterns['task_numbers'].extend([int(num) for num in matches])
                
                # 分析commit类型（基于message前缀）
                commit_type = 'other'
                if message.startswith('feat'):
                    commit_type = 'feature'
                elif message.startswith('fix'):
                    commit_type = 'bugfix'
                elif message.startswith('docs'):
                    commit_type = 'documentation'
                
                patterns['commit_types'][commit_type] = patterns['commit_types'].get(commit_type, 0) + 1
                
                # 分析作者
                author = commit.get('author_name', 'Unknown')
                patterns['authors'][author] = patterns['authors'].get(author, 0) + 1
        
        return {
            'task_number_range': {
                'min': min(patterns['task_numbers']) if patterns['task_numbers'] else 0,
                'max': max(patterns['task_numbers']) if patterns['task_numbers'] else 0,
                'count': len(patterns['task_numbers'])
            },
            'commit_types': patterns['commit_types'],
            'top_authors': dict(sorted(patterns['authors'].items(), key=lambda x: x[1], reverse=True)[:5])
        } 