#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Task检测器 v2
基于并发分页获取的高性能版本，增强日志，简化逻辑
"""
import time
import logging
from typing import Dict, Any, List, Set
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from ..gitlab.gitlab_manager import GitLabManager


logger = logging.getLogger(__name__)


class TaskLossDetector:
    """
    Task缺失检测器 v2
    
    核心优化:
    1. 并发分页获取commits
    2. 本地内存分析tasks
    3. 详细的性能监控和日志
    4. 去掉缓存，简化逻辑
    """
    
    def __init__(self, gitlab_manager: GitLabManager):
        self.gitlab_manager = gitlab_manager
        logger.info(f"[{self._timestamp()}] 🚀 TaskLossDetector 初始化完成")
    
    def _timestamp(self) -> str:
        """生成带毫秒的时间戳"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    def _analyze_version_tasks(self, old_version: str, new_version: str) -> Dict[str, Any]:
        """
        核心方法：分析两个版本的task差异
        """
        start_time = time.time()
        logger.info(f"[{self._timestamp()}] 🚀 开始版本task分析: {old_version} -> {new_version}")
        logger.info(f"[{self._timestamp()}] " + "="*80)
        
        try:
            # 阶段1: 并发获取两个版本的全部commits
            fetch_start = time.time()
            logger.info(f"[{self._timestamp()}] 📥 阶段1: 并发获取两个版本的全部commits...")
            
            with ThreadPoolExecutor(max_workers=2) as executor:
                # 并发获取两个版本的commits
                logger.info(f"[{self._timestamp()}] 🔄 启动2个并发任务获取commits...")
                
                future_old = executor.submit(
                    self.gitlab_manager.get_all_tag_commits_concurrent, 
                    old_version
                )
                future_new = executor.submit(
                    self.gitlab_manager.get_all_tag_commits_concurrent, 
                    new_version
                )
                
                logger.info(f"[{self._timestamp()}] ⏳ 等待旧版本 {old_version} 的commits...")
                old_commits = future_old.result()
                
                logger.info(f"[{self._timestamp()}] ⏳ 等待新版本 {new_version} 的commits...")
                new_commits = future_new.result()
            
            fetch_time = time.time() - fetch_start
            logger.info(f"[{self._timestamp()}] ✅ 阶段1完成:")
            logger.info(f"    📊 旧版本 {old_version}: {len(old_commits)} commits")
            logger.info(f"    📊 新版本 {new_version}: {len(new_commits)} commits")
            logger.info(f"    📊 获取耗时: {fetch_time:.2f}s")
            
            # 更细致的错误检查
            if not old_commits and not new_commits:
                return {
                    'old_tasks': set(),
                    'new_tasks': set(),
                    'missing_tasks': set(),
                    'new_features': set(),
                    'common_tasks': set(),
                    'analysis': 'both_versions_failed',
                    'total_time': time.time() - start_time,
                    'error': f'无法获取两个版本的commits。请检查: 1) GITLAB_TOKEN环境变量是否有效 2) 版本标签 {old_version}, {new_version} 是否存在'
                }
            elif not old_commits:
                logger.warning(f"[{self._timestamp()}] ⚠️ 无法获取旧版本 {old_version} 的commits，但新版本正常")
                return {
                    'old_tasks': set(),
                    'new_tasks': set(),
                    'missing_tasks': set(),
                    'new_features': set(),
                    'common_tasks': set(),
                    'analysis': 'old_version_failed',
                    'total_time': time.time() - start_time,
                    'error': f'无法获取旧版本 {old_version} 的commits。请检查版本标签是否存在'
                }
            elif not new_commits:
                logger.warning(f"[{self._timestamp()}] ⚠️ 无法获取新版本 {new_version} 的commits，但旧版本正常")
                return {
                    'old_tasks': set(),
                    'new_tasks': set(),
                    'missing_tasks': set(),
                    'new_features': set(),
                    'common_tasks': set(),
                    'analysis': 'new_version_failed',
                    'total_time': time.time() - start_time,
                    'error': f'无法获取新版本 {new_version} 的commits。请检查版本标签是否存在'
                }
            
            # 阶段2: 提取commit messages和对应的tasks
            analysis_start = time.time()
            logger.info(f"[{self._timestamp()}] 🧮 阶段2: 提取commit messages和tasks...")
            
            logger.info(f"[{self._timestamp()}] 🔍 解析旧版本 {old_version} 的commit messages...")
            old_commit_task_map = self.gitlab_manager.extract_commit_messages_with_tasks(old_commits)
            
            logger.info(f"[{self._timestamp()}] 🔍 解析新版本 {new_version} 的commit messages...")
            new_commit_task_map = self.gitlab_manager.extract_commit_messages_with_tasks(new_commits)
            
            # 阶段3: 基于task ID比对计算差异（而不是commit message比对）
            logger.info(f"[{self._timestamp()}] 🧮 阶段3: 基于task ID比对计算差异...")
            
            # 获取task ID集合
            old_tasks = set(old_commit_task_map.values())
            new_tasks = set(new_commit_task_map.values())
            
            # 找出旧版本有但新版本没有的task IDs
            missing_tasks = old_tasks - new_tasks
            
            # 找出新版本有但旧版本没有的task IDs
            new_features = new_tasks - old_tasks
            
            # 计算共同的tasks
            common_tasks = old_tasks & new_tasks
            
            # 为了调试，也计算commit message差异
            old_messages = set(old_commit_task_map.keys())
            new_messages = set(new_commit_task_map.keys())
            missing_messages = old_messages - new_messages
            
            analysis_time = time.time() - analysis_start
            total_time = time.time() - start_time
            performance_improvement = 262.30 / total_time if total_time > 0 else 0
            
            logger.info(f"[{self._timestamp()}] ✅ 阶段2&3完成: 分析耗时={analysis_time:.3f}s")
            logger.info(f"[{self._timestamp()}] " + "="*80)
            logger.info(f"[{self._timestamp()}] 🎯 版本task分析完成:")
            logger.info(f"    📊 总耗时: {total_time:.2f}s (原版262.30s)")
            logger.info(f"    ⚡ 性能提升: {performance_improvement:.1f}x 倍速")
            logger.info(f"    📊 旧版本 {old_version}: {len(old_tasks)} 个tasks")
            logger.info(f"    📊 新版本 {new_version}: {len(new_tasks)} 个tasks")
            logger.info(f"    🔍 缺失tasks: {len(missing_tasks)} 个")
            logger.info(f"    🆕 新增features: {len(new_features)} 个")
            logger.info(f"    ✅ 共同tasks: {len(common_tasks)} 个")
            logger.info(f"    📝 基于task ID比对 (修复后的逻辑)")
            logger.info(f"    📝 commit message差异: {len(missing_messages)} 个 (仅供参考)")
            
            # 打印详细的task信息
            if missing_tasks:
                missing_list = sorted(list(missing_tasks))
                logger.info(f"    🔍 缺失tasks详情: {missing_list[:20]}{'...' if len(missing_list) > 20 else ''}")
            
            if new_features:
                new_list = sorted(list(new_features))
                logger.info(f"    🆕 新增features详情: {new_list[:20]}{'...' if len(new_list) > 20 else ''}")
            
            logger.info(f"[{self._timestamp()}] " + "="*80)
            
            return {
                'old_tasks': old_tasks,
                'new_tasks': new_tasks,
                'missing_tasks': missing_tasks,
                'new_features': new_features,
                'common_tasks': common_tasks,
                'analysis': 'success',
                'total_time': total_time,
                'performance_improvement': performance_improvement,
                'fetch_time': fetch_time,
                'analysis_time': analysis_time,
                'old_commits_count': len(old_commits),
                'new_commits_count': len(new_commits)
            }
            
        except Exception as e:
            total_time = time.time() - start_time
            logger.error(f"[{self._timestamp()}] ❌ 版本task分析失败: {e}, 耗时: {total_time:.2f}s")
            import traceback
            logger.error(f"[{self._timestamp()}] 📍 错误堆栈: {traceback.format_exc()}")
            return {
                'old_tasks': set(),
                'new_tasks': set(),
                'missing_tasks': set(),
                'new_features': set(),
                'common_tasks': set(),
                'error': str(e),
                'analysis': 'error',
                'total_time': total_time
            }

    def detect_missing_tasks(self, old_version: str, new_version: str) -> Dict[str, Any]:
        """
        检测缺失的tasks：旧版本有但新版本没有的tasks
        """
        logger.info(f"[{self._timestamp()}] 🔍 开始检测缺失tasks: {old_version} -> {new_version}")
        
        # 调用核心分析方法
        result = self._analyze_version_tasks(old_version, new_version)
        
        # 返回缺失tasks的结果
        return {
            'missing_tasks': sorted(list(result['missing_tasks'])),
            'analysis': result['analysis'],
            'total_time': result['total_time'],
            'error': result.get('error'),
            'old_commits_count': result.get('old_commits_count', 0),
            'new_commits_count': result.get('new_commits_count', 0),
            'old_tasks_count': len(result['old_tasks']),
            'new_tasks_count': len(result['new_tasks'])
        }

    def analyze_new_features(self, old_version: str, new_version: str) -> Dict[str, Any]:
        """
        分析新增features：新版本有但旧版本没有的tasks
        """
        logger.info(f"[{self._timestamp()}] 🆕 开始分析新增features: {old_version} -> {new_version}")
        
        # 调用核心分析方法
        result = self._analyze_version_tasks(old_version, new_version)
        
        # 返回新增features的结果
        return {
            'new_features': sorted(list(result['new_features'])),
            'analysis': result['analysis'],
            'total_time': result['total_time'],
            'error': result.get('error'),
            'old_commits_count': result.get('old_commits_count', 0),
            'new_commits_count': result.get('new_commits_count', 0),
            'old_tasks_count': len(result['old_tasks']),
            'new_tasks_count': len(result['new_tasks'])
        } 