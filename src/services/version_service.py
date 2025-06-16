"""
版本比较服务 - 简化版
基于GitLab Search API的高效task检测服务
"""
import time
from typing import Dict, Any, List, Optional
from ..gitlab.gitlab_manager import GitLabManager
from ..core.task_detector import TaskLossDetector
from ..core.cache_manager import RequestCacheManager


class VersionCompareService:
    """版本比较服务 - 简化版，专注于Search API核心功能"""
    
    def __init__(self, gitlab_url: str, token: str, project_id: str):
        self.gitlab_manager = GitLabManager(gitlab_url, token, project_id)
        self.detector = TaskLossDetector(self.gitlab_manager)
        print("VersionCompareService 初始化完成 (Search API版)")
    
    def analyze_new_features(self, old_version: str, new_version: str) -> Dict[str, Any]:
        """
        分析新版本带来的新内容
        从旧版本升级到新版本时，新增了哪些tasks和功能
        """
        print(f"🆕 分析新版本内容: {old_version} -> {new_version}")
        start_time = time.time()
        
        try:
            # 获取从旧版本到新版本的差异commits（新增的内容）
            diff_commits = self.gitlab_manager.get_version_diff(old_version, new_version)
            
            if not diff_commits:
                return {
                    'new_tasks': [],
                    'new_commits': [],
                    'total_new_commits': 0,
                    'analysis': 'no_new_content',
                    'processing_time': time.time() - start_time,
                    'upgrade_direction': f"{old_version} -> {new_version}"
                }
            
            # 从新增的commits中提取新的tasks
            new_tasks = self.gitlab_manager.extract_tasks_from_commits(diff_commits)
            
            # 验证这些tasks确实是新增的（在旧版本中不存在）
            print(f"🔍 验证 {len(new_tasks)} 个tasks是否为新增...")
            if new_tasks:
                existing_in_old = self.gitlab_manager.search_specific_tasks(new_tasks, old_version)
                truly_new_tasks = [task for task in new_tasks if task not in existing_in_old]
            else:
                truly_new_tasks = []
            
            processing_time = time.time() - start_time
            
            # 分析新增内容的统计
            commit_stats = self._analyze_commit_patterns(diff_commits)
            
            print(f"✅ 新内容分析完成 ({processing_time:.2f}s): {len(truly_new_tasks)} 个新tasks")
            
            return {
                'new_tasks': truly_new_tasks,
                'new_tasks_detail': {task: existing_in_old.get(task, {}) for task in truly_new_tasks},
                'total_new_commits': len(diff_commits),
                'commit_statistics': commit_stats,
                'upgrade_direction': f"{old_version} -> {new_version}",
                'analysis': 'success',
                'processing_time': processing_time,
                'search_method': 'search_api',
                'service_version': '2.0_simplified'
            }
            
        except Exception as e:
            print(f"❌ 新内容分析失败: {e}")
            return {
                'new_tasks': [],
                'new_commits': [],
                'error': str(e),
                'analysis': 'error',
                'processing_time': time.time() - start_time,
                'upgrade_direction': f"{old_version} -> {new_version}"
            }
        
        finally:
            self.gitlab_manager.finish_request()
    
    def detect_missing_tasks(self, old_version: str, new_version: str) -> Dict[str, Any]:
        """
        检测新版本丢失的功能
        从旧版本升级到新版本时，哪些tasks/功能可能丢失了
        """
        print(f"⚠️ 检测功能丢失: {old_version} -> {new_version}")
        start_time = time.time()
        
        try:
            # 获取从新版本到旧版本的差异commits（在新版本中缺失的内容）
            diff_commits = self.gitlab_manager.get_version_diff(new_version, old_version)
            
            if not diff_commits:
                return {
                    'missing_tasks': [],
                    'potentially_lost_commits': [],
                    'total_diff_commits': 0,
                    'analysis': 'no_missing_content',
                    'processing_time': time.time() - start_time,
                    'upgrade_direction': f"{old_version} -> {new_version}",
                    'risk_level': 'low'
                }
            
            # 从差异commits中提取可能丢失的tasks
            candidate_missing_tasks = self.gitlab_manager.extract_tasks_from_commits(diff_commits)
            print(f"📋 从 {len(diff_commits)} 个差异commits中提取到 {len(candidate_missing_tasks)} 个潜在丢失task")
            
            if not candidate_missing_tasks:
                return {
                    'missing_tasks': [],
                    'potentially_lost_commits': diff_commits[:10],  # 只返回前10个作为示例
                    'total_diff_commits': len(diff_commits),
                    'analysis': 'no_tasks_in_diff',
                    'processing_time': time.time() - start_time,
                    'upgrade_direction': f"{old_version} -> {new_version}",
                    'risk_level': 'low'
                }
            
            # 验证这些tasks在新版本中是否真的不存在
            print(f"🔎 验证这些tasks在新版本 {new_version} 中是否真的丢失...")
            existing_in_new = self.gitlab_manager.search_specific_tasks(candidate_missing_tasks, new_version)
            
            # 计算真正丢失的tasks
            truly_missing_tasks = [task for task in candidate_missing_tasks if task not in existing_in_new]
            
            # 评估风险等级
            risk_level = self._assess_risk_level(len(truly_missing_tasks), len(diff_commits))
            
            processing_time = time.time() - start_time
            print(f"⚠️ 丢失检测完成 ({processing_time:.2f}s): {len(truly_missing_tasks)} 个真正丢失")
            
            return {
                'missing_tasks': truly_missing_tasks,
                'missing_tasks_detail': self._get_missing_tasks_detail(truly_missing_tasks, diff_commits),
                'existing_tasks': list(existing_in_new.keys()),
                'existing_tasks_detail': existing_in_new,
                'total_diff_commits': len(diff_commits),
                'potentially_missing_count': len(candidate_missing_tasks),
                'upgrade_direction': f"{old_version} -> {new_version}",
                'risk_level': risk_level,
                'risk_assessment': self._generate_risk_assessment(truly_missing_tasks, risk_level),
                'analysis': 'success',
                'processing_time': processing_time,
                'search_method': 'search_api',
                'service_version': '2.0_simplified'
            }
            
        except Exception as e:
            print(f"❌ 丢失检测失败: {e}")
            return {
                'missing_tasks': [],
                'existing_tasks': [],
                'error': str(e),
                'analysis': 'error',
                'processing_time': time.time() - start_time,
                'upgrade_direction': f"{old_version} -> {new_version}",
                'risk_level': 'unknown'
            }
        
        finally:
            self.gitlab_manager.finish_request()
    
    def _analyze_commit_patterns(self, commits: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析commits的模式和统计"""
        if not commits:
            return {}
        
        stats = {
            'total_commits': len(commits),
            'authors': {},
            'commit_types': {},
            'date_range': {
                'earliest': None,
                'latest': None
            }
        }
        
        for commit in commits:
            # 统计作者
            author = commit.get('author_name', 'Unknown')
            stats['authors'][author] = stats['authors'].get(author, 0) + 1
            
            # 分析commit类型
            message = commit.get('message', '').lower()
            if 'feat' in message or '新增' in message:
                commit_type = 'feature'
            elif 'fix' in message or '修复' in message:
                commit_type = 'bugfix'
            elif 'docs' in message or '文档' in message:
                commit_type = 'documentation'
            else:
                commit_type = 'other'
            
            stats['commit_types'][commit_type] = stats['commit_types'].get(commit_type, 0) + 1
            
            # 记录日期范围
            commit_date = commit.get('committed_date')
            if commit_date:
                if not stats['date_range']['earliest'] or commit_date < stats['date_range']['earliest']:
                    stats['date_range']['earliest'] = commit_date
                if not stats['date_range']['latest'] or commit_date > stats['date_range']['latest']:
                    stats['date_range']['latest'] = commit_date
        
        # 排序作者（按贡献数量）
        stats['top_authors'] = dict(sorted(stats['authors'].items(), key=lambda x: x[1], reverse=True)[:5])
        
        return stats
    
    def _assess_risk_level(self, missing_count: int, total_commits: int) -> str:
        """评估升级风险等级"""
        if missing_count == 0:
            return 'low'
        elif missing_count <= 5:
            return 'medium'
        elif missing_count <= 20:
            return 'high'
        else:
            return 'critical'
    
    def _generate_risk_assessment(self, missing_tasks: List[str], risk_level: str) -> Dict[str, Any]:
        """生成风险评估报告"""
        assessments = {
            'low': {
                'message': '升级风险较低，未发现功能丢失',
                'recommendation': '可以安全升级',
                'action': 'proceed'
            },
            'medium': {
                'message': f'发现 {len(missing_tasks)} 个可能丢失的功能，建议谨慎升级',
                'recommendation': '建议先在测试环境验证这些功能',
                'action': 'test_first'
            },
            'high': {
                'message': f'发现 {len(missing_tasks)} 个丢失的功能，升级风险较高',
                'recommendation': '强烈建议详细测试所有相关功能',
                'action': 'careful_testing'
            },
            'critical': {
                'message': f'发现 {len(missing_tasks)} 个丢失的功能，升级风险极高',
                'recommendation': '不建议直接升级，需要详细分析每个丢失的功能',
                'action': 'do_not_upgrade'
            }
        }
        
        return assessments.get(risk_level, assessments['medium'])
    
    def _get_missing_tasks_detail(self, missing_tasks: List[str], commits: List[Dict[str, Any]]) -> Dict[str, Any]:
        """获取丢失tasks的详细信息"""
        details = {}
        
        for task in missing_tasks:
            # 找到包含这个task的commits
            related_commits = []
            for commit in commits:
                if task in commit.get('message', ''):
                    related_commits.append({
                        'commit_id': commit.get('id'),
                        'short_id': commit.get('short_id'),
                        'message': commit.get('message', '')[:100] + '...',
                        'author': commit.get('author_name'),
                        'date': commit.get('committed_date')
                    })
            
            details[task] = {
                'related_commits': related_commits[:3],  # 只保留前3个相关commits
                'total_related_commits': len(related_commits)
            }
        
        return details
    
    def analyze_specific_tasks(self, task_ids: List[str], branch_name: str) -> Dict[str, Any]:
        """分析特定tasks的详细信息"""
        print(f"🔍 分析特定tasks: {len(task_ids)} 个tasks 在分支 {branch_name}")
        
        try:
            task_details = self.detector.analyze_task_details(task_ids, branch_name)
            
            return {
                'task_details': task_details,
                'total_tasks': len(task_ids),
                'found_tasks': len([t for t in task_details.values() if t.get('status') != 'not_found']),
                'missing_tasks': len([t for t in task_details.values() if t.get('status') == 'not_found']),
                'analysis_method': 'search_api'
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'analysis': 'analysis_error'
            }
    
    def get_task_statistics(self, from_version: str, to_version: str) -> Dict[str, Any]:
        """获取版本差异的task统计信息"""
        try:
            # 获取版本差异commits
            diff_commits = self.gitlab_manager.get_version_diff(from_version, to_version)
            
            if not diff_commits:
                return {
                    'total_commits': 0,
                    'task_statistics': {},
                    'analysis': 'no_commits'
                }
            
            # 获取统计信息
            stats = self.detector.get_task_statistics(diff_commits)
            
            return {
                'total_commits': len(diff_commits),
                'task_statistics': stats,
                'analysis': 'success'
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'analysis': 'stats_error'
            }
    
    def search_tasks_in_version(self, version: str, task_pattern: str = "GALAXY-") -> Dict[str, Any]:
        """在特定版本中搜索tasks"""
        try:
            print(f"🔍 在版本 {version} 中搜索 {task_pattern} tasks")
            
            # 使用Search API搜索
            tasks = self.gitlab_manager.search_tasks_in_branch(version, task_pattern)
            
            return {
                'version': version,
                'pattern': task_pattern,
                'found_tasks': tasks,
                'total_found': len(tasks),
                'search_method': 'search_api'
            }
            
        except Exception as e:
            return {
                'error': str(e),
                'analysis': 'search_error'
            }
    
    def validate_versions(self, versions: List[str]) -> Dict[str, Any]:
        """验证版本是否存在"""
        validation_results = {}
        
        for version in versions:
            try:
                # 尝试获取版本信息
                commit = self.gitlab_manager.project.commits.get(version)
                validation_results[version] = {
                    'exists': True,
                    'commit_id': commit.id,
                    'committed_date': commit.committed_date,
                    'short_id': commit.short_id
                }
            except Exception as e:
                validation_results[version] = {
                    'exists': False,
                    'error': str(e)
                }
        
        return {
            'validation_results': validation_results,
            'total_versions': len(versions),
            'valid_versions': len([v for v in validation_results.values() if v['exists']]),
            'invalid_versions': len([v for v in validation_results.values() if not v['exists']])
        }
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return self.gitlab_manager.get_cache_stats()
    
    def clear_cache(self) -> Dict[str, Any]:
        """清理缓存"""
        stats_before = self.gitlab_manager.get_cache_stats()
        self.detector.clear_cache()
        stats_after = self.gitlab_manager.get_cache_stats()
        
        return {
            'cache_cleared': True,
            'stats_before': stats_before,
            'stats_after': stats_after
        }


class VersionCompareError(Exception):
    """版本比较服务错误"""
    pass


class VersionNotFoundError(VersionCompareError):
    """版本未找到错误"""
    pass


class GitLabConnectionError(VersionCompareError):
    """GitLab连接错误"""
    pass 