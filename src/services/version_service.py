"""
版本比较主服务
整合GitLab API、Task检测、AI分析等所有组件
"""
import time
from typing import Dict, List, Any, Optional
from ..gitlab.gitlab_manager import GitLabManager
from ..core.task_detector import TaskLossDetector, TaskAnalyzer
from ..ai.ai_analyzer import AIVersionAnalyzer


class VersionCompareService:
    """版本比较主服务"""
    
    def __init__(self, gitlab_url: str, gitlab_token: str, project_id: str, openai_api_key: Optional[str] = None):
        """初始化版本比较服务"""
        print("🚀 正在初始化版本比较服务...")
        
        # 初始化各个组件
        self.gitlab_manager = GitLabManager(gitlab_url, gitlab_token, project_id)
        self.task_detector = TaskLossDetector(self.gitlab_manager)
        self.task_analyzer = TaskAnalyzer(self.task_detector)
        self.ai_analyzer = AIVersionAnalyzer(openai_api_key)
        
        print("✅ 版本比较服务初始化完成")
    
    def compare_versions(self, from_version: str, to_version: str, include_ai_analysis: bool = True) -> Dict[str, Any]:
        """完整的版本比较分析"""
        print(f"🔄 开始版本比较: {from_version} -> {to_version}")
        start_time = time.time()
        
        try:
            # 步骤1: 检测缺失的tasks
            task_diff_result = self.task_detector.detect_missing_tasks(from_version, to_version)
            
            # 步骤2: AI分析（如果启用）
            ai_analysis = {}
            if include_ai_analysis:
                print("🤖 正在进行AI分析...")
                ai_analysis = self.ai_analyzer.analyze_version_changes(task_diff_result)
            
            # 步骤3: 整合结果
            result = {
                'from_version': from_version,
                'to_version': to_version,
                'missing_tasks': task_diff_result.get('missing_tasks', []),
                'existing_tasks': task_diff_result.get('existing_tasks', []),
                'existing_tasks_detail': task_diff_result.get('existing_tasks_detail', {}),
                'total_diff_commits': task_diff_result.get('total_diff_commits', 0),
                'potentially_missing_count': task_diff_result.get('potentially_missing_count', 0),
                'processing_time': task_diff_result.get('processing_time', 0),
                'ai_analysis': ai_analysis,
                'analysis_status': task_diff_result.get('analysis', 'unknown'),
                'timestamp': time.time()
            }
            
            # 步骤4: 生成详细报告
            if include_ai_analysis:
                result['detailed_report'] = self.ai_analyzer.generate_detailed_report(result, from_version, to_version)
            
            total_time = time.time() - start_time
            result['total_processing_time'] = total_time
            
            print(f"✅ 版本比较完成 ({total_time:.2f}s)")
            return result
            
        except Exception as e:
            print(f"❌ 版本比较失败: {e}")
            return {
                'from_version': from_version,
                'to_version': to_version,
                'error': str(e),
                'analysis_status': 'error',
                'timestamp': time.time(),
                'total_processing_time': time.time() - start_time
            }
        finally:
            # 清理缓存并报告统计
            cache_stats = self.gitlab_manager.finish_request()
            print(f"📊 缓存统计: {cache_stats}")
    
    def batch_compare_versions(self, version_pairs: List[tuple], include_ai_analysis: bool = True) -> Dict[str, Any]:
        """批量版本比较"""
        print(f"📦 开始批量版本比较: {len(version_pairs)} 个版本对")
        start_time = time.time()
        
        results = []
        failed_comparisons = []
        
        for i, (from_ver, to_ver) in enumerate(version_pairs, 1):
            print(f"🔄 处理第 {i}/{len(version_pairs)} 个比较: {from_ver} -> {to_ver}")
            
            try:
                result = self.compare_versions(from_ver, to_ver, include_ai_analysis)
                if result.get('analysis_status') == 'error':
                    failed_comparisons.append({
                        'from_version': from_ver,
                        'to_version': to_ver,
                        'error': result.get('error', 'Unknown error')
                    })
                else:
                    results.append(result)
                    
            except Exception as e:
                print(f"❌ 比较失败 {from_ver} -> {to_ver}: {e}")
                failed_comparisons.append({
                    'from_version': from_ver,
                    'to_version': to_ver,
                    'error': str(e)
                })
        
        # 生成批量分析报告
        batch_analysis = {}
        if results and include_ai_analysis:
            batch_analysis = self.ai_analyzer.analyze_multiple_versions(results)
        
        total_time = time.time() - start_time
        
        return {
            'successful_comparisons': len(results),
            'failed_comparisons': len(failed_comparisons),
            'results': results,
            'failed_details': failed_comparisons,
            'batch_analysis': batch_analysis,
            'total_processing_time': total_time,
            'timestamp': time.time()
        }
    
    def get_version_suggestions(self, current_version: str, max_suggestions: int = 5) -> List[str]:
        """获取版本升级建议"""
        try:
            # 获取所有项目标签
            all_tags = self.gitlab_manager.get_project_tags()
            
            if not all_tags:
                return []
            
            # 简单的版本排序和过滤逻辑
            # 这里可以根据实际的版本命名规则进行优化
            filtered_tags = [tag for tag in all_tags if tag > current_version]
            filtered_tags.sort()
            
            return filtered_tags[:max_suggestions]
            
        except Exception as e:
            print(f"⚠️ 获取版本建议失败: {e}")
            return []
    
    def analyze_task_details(self, task_ids: List[str], branch_name: str) -> Dict[str, Any]:
        """分析特定tasks的详细信息"""
        return self.task_detector.analyze_task_details(task_ids, branch_name)
    
    def get_task_statistics(self, from_version: str, to_version: str) -> Dict[str, Any]:
        """获取版本间的task统计信息"""
        try:
            # 获取版本差异commits
            diff_commits = self.gitlab_manager.get_version_diff(from_version, to_version)
            
            if not diff_commits:
                return {'error': '无法获取版本差异'}
            
            # 获取task统计
            task_stats = self.task_detector.get_task_statistics(diff_commits)
            
            # 添加额外的分析
            pattern_analysis = self.task_analyzer.analyze_task_patterns(diff_commits)
            
            return {
                'basic_stats': task_stats,
                'pattern_analysis': pattern_analysis,
                'total_commits': len(diff_commits),
                'from_version': from_version,
                'to_version': to_version
            }
            
        except Exception as e:
            print(f"❌ 获取task统计失败: {e}")
            return {'error': str(e)}
    
    def health_check(self) -> Dict[str, Any]:
        """服务健康检查（轻量级）"""
        health_status = {
            'service': 'healthy',
            'gitlab_connection': 'unknown',
            'ai_service': 'unknown',
            'cache_stats': {},
            'timestamp': time.time()
        }
        
        try:
            # 轻量级GitLab连接检查 - 只检查连接状态，不获取大量数据
            if hasattr(self.gitlab_manager, 'gitlab') and self.gitlab_manager.gitlab:
                health_status['gitlab_connection'] = 'healthy'
                health_status['gitlab_url'] = self.gitlab_manager.gitlab_url
                health_status['project_id'] = self.gitlab_manager.project_id
            else:
                health_status['gitlab_connection'] = 'error'
            
        except Exception as e:
            health_status['gitlab_connection'] = 'error'
            health_status['gitlab_error'] = str(e)
        
        try:
            # 检查AI服务
            if self.ai_analyzer.api_key:
                health_status['ai_service'] = 'available'
            else:
                health_status['ai_service'] = 'unavailable'
                
        except Exception as e:
            health_status['ai_service'] = 'error'
            health_status['ai_error'] = str(e)
        
        # 获取缓存统计
        try:
            health_status['cache_stats'] = self.gitlab_manager.get_cache_stats()
        except Exception as e:
            health_status['cache_error'] = str(e)
        
        return health_status
    
    def clear_all_caches(self) -> Dict[str, Any]:
        """清理所有缓存"""
        try:
            cache_report = self.gitlab_manager.finish_request()
            self.task_detector.clear_cache()
            
            return {
                'status': 'success',
                'cache_report': cache_report,
                'message': '所有缓存已清理'
            }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': '缓存清理失败'
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