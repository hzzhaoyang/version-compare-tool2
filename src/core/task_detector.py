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
            
            # 阶段3: 基于commit message精确比对计算差异（可检测同一task的部分commits缺失）
            logger.info(f"[{self._timestamp()}] 🧮 阶段3: 基于commit message精确比对计算差异...")
            
            # 获取commit message集合和task ID集合
            old_messages = set(old_commit_task_map.keys())
            new_messages = set(new_commit_task_map.keys())
            old_tasks = set(old_commit_task_map.values())
            new_tasks = set(new_commit_task_map.values())
            
            # 找出旧版本有但新版本没有的commit messages
            missing_messages = old_messages - new_messages
            
            # 找出新版本有但旧版本没有的commit messages  
            new_messages_only = new_messages - old_messages
            
            # 从缺失的commit messages中提取对应的task IDs
            missing_commit_tasks = {}  # {task_id: [missing_commit_messages]}
            for msg in missing_messages:
                task_id = old_commit_task_map[msg]
                if task_id not in missing_commit_tasks:
                    missing_commit_tasks[task_id] = []
                missing_commit_tasks[task_id].append(msg)
            
            # 从新增的commit messages中提取对应的task IDs
            new_commit_tasks = {}  # {task_id: [new_commit_messages]}
            for msg in new_messages_only:
                task_id = new_commit_task_map[msg]
                if task_id not in new_commit_tasks:
                    new_commit_tasks[task_id] = []
                new_commit_tasks[task_id].append(msg)
            
            # 分类分析缺失情况
            completely_missing_tasks = set()  # 完全缺失的tasks（新版本完全没有）
            partially_missing_tasks = {}     # 部分缺失的tasks（新版本有但缺少某些commits）
            
            for task_id, missing_commits in missing_commit_tasks.items():
                if task_id not in new_tasks:
                    # 新版本完全没有这个task
                    completely_missing_tasks.add(task_id)
                else:
                    # 新版本有这个task，但缺少某些commits
                    partially_missing_tasks[task_id] = missing_commits
            
            # 计算新增的tasks（完全新增的和部分新增的）
            completely_new_tasks = new_tasks - old_tasks  # 完全新增的tasks
            partially_new_tasks = {}  # 已存在但有新commits的tasks
            
            for task_id, new_commits in new_commit_tasks.items():
                if task_id in old_tasks:
                    # 旧版本也有这个task，但有新的commits
                    partially_new_tasks[task_id] = new_commits
            
            # 计算共同的tasks
            common_tasks = old_tasks & new_tasks
            
            # 合并所有缺失的tasks（完全缺失 + 部分缺失）
            all_missing_tasks = completely_missing_tasks | set(partially_missing_tasks.keys())
            
            # 合并所有新增的tasks（完全新增 + 部分新增）
            all_new_tasks = completely_new_tasks | set(partially_new_tasks.keys())
            
            # 构建new_features_with_commits: 包含每个新增task及其对应的commit messages
            new_features_with_commits = {}
            
            # 处理完全新增的tasks
            for task_id in completely_new_tasks:
                # 从新版本的commit messages中找到属于这个task的所有commits
                task_commits = []
                for msg, msg_task_id in new_commit_task_map.items():
                    if msg_task_id == task_id:
                        task_commits.append(msg)
                new_features_with_commits[task_id] = task_commits
            
            # 处理部分新增的tasks（已存在但有新commits）
            for task_id, commit_messages in partially_new_tasks.items():
                new_features_with_commits[task_id] = commit_messages
            
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
            logger.info(f"    🔍 缺失tasks: {len(all_missing_tasks)} 个")
            logger.info(f"      - 完全缺失: {len(completely_missing_tasks)} 个")
            logger.info(f"      - 部分缺失: {len(partially_missing_tasks)} 个")
            logger.info(f"    🆕 新增tasks: {len(all_new_tasks)} 个")
            logger.info(f"      - 完全新增: {len(completely_new_tasks)} 个")
            logger.info(f"      - 部分新增: {len(partially_new_tasks)} 个")
            logger.info(f"    ✅ 共同tasks: {len(common_tasks)} 个")
            logger.info(f"    📝 基于commit message精确比对 (优化后的逻辑)")
            logger.info(f"    📝 缺失commit messages: {len(missing_messages)} 个")
            logger.info(f"    📝 新增commit messages: {len(new_messages_only)} 个")
            
            # 打印详细的task信息
            if completely_missing_tasks:
                missing_list = sorted(list(completely_missing_tasks))
                logger.info(f"    🔍 完全缺失tasks: {missing_list[:10]}{'...' if len(missing_list) > 10 else ''}")
            
            if partially_missing_tasks:
                partial_list = sorted(list(partially_missing_tasks.keys()))
                logger.info(f"    🔍 部分缺失tasks: {partial_list[:10]}{'...' if len(partial_list) > 10 else ''}")
                # 显示部分缺失的详细信息
                for task_id in partial_list[:3]:  # 只显示前3个的详细信息
                    missing_count = len(partially_missing_tasks[task_id])
                    logger.info(f"      - {task_id}: 缺失 {missing_count} 个commits")
            
            if completely_new_tasks:
                new_list = sorted(list(completely_new_tasks))
                logger.info(f"    🆕 完全新增tasks: {new_list[:10]}{'...' if len(new_list) > 10 else ''}")
            
            if partially_new_tasks:
                partial_new_list = sorted(list(partially_new_tasks.keys()))
                logger.info(f"    🆕 部分新增tasks: {partial_new_list[:10]}{'...' if len(partial_new_list) > 10 else ''}")
            
            logger.info(f"[{self._timestamp()}] " + "="*80)
            
            return {
                'old_tasks': old_tasks,
                'new_tasks': new_tasks,
                'missing_tasks': all_missing_tasks,
                'new_features': new_features_with_commits,
                'common_tasks': common_tasks,
                'analysis': 'success',
                'total_time': total_time,
                'performance_improvement': performance_improvement,
                'fetch_time': fetch_time,
                'analysis_time': analysis_time,
                'old_commits_count': len(old_commits),
                'new_commits_count': len(new_commits),
                # 新增详细分析结果
                'detailed_analysis': {
                    'completely_missing_tasks': completely_missing_tasks,
                    'partially_missing_tasks': partially_missing_tasks,
                    'completely_new_tasks': completely_new_tasks,
                    'partially_new_tasks': partially_new_tasks,
                    'missing_commit_messages': missing_messages,
                    'new_commit_messages': new_messages_only
                }
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
        
        # 返回缺失tasks的结果，包含完整的分析数据
        return {
            'missing_tasks': result['missing_tasks'],
            'old_tasks': result['old_tasks'],
            'new_tasks': result['new_tasks'],
            'new_features': result['new_features'],
            'common_tasks': result['common_tasks'],
            'analysis': result['analysis'],
            'total_time': result['total_time'],
            'error': result.get('error'),
            'old_commits_count': result.get('old_commits_count', 0),
            'new_commits_count': result.get('new_commits_count', 0),
            'detailed_analysis': result.get('detailed_analysis')
        }

    def analyze_new_features(self, old_version: str, new_version: str) -> Dict[str, Any]:
        """
        分析新增features：新版本有但旧版本没有的tasks
        """
        logger.info(f"[{self._timestamp()}] 🆕 开始分析新增features: {old_version} -> {new_version}")
        
        # 调用核心分析方法
        result = self._analyze_version_tasks(old_version, new_version)
        
        # 只返回新增features相关的结果
        detailed_analysis = result.get('detailed_analysis', {})
        filtered_detailed_analysis = {
            'completely_new_tasks': detailed_analysis.get('completely_new_tasks', set()),
            'partially_new_tasks': detailed_analysis.get('partially_new_tasks', {}),
            'new_commit_messages': detailed_analysis.get('new_commit_messages', set())
        }
        
        # 处理新增的commit messages，优化格式：从 "GALAXY-25259||GALAXY-25259【Bug】thirdparty data router add" 
        # 优化为 "GALAXY-25259【Bug】thirdparty data router add"
        new_commit_messages = []
        for commit_msg in detailed_analysis.get('new_commit_messages', set()):
            if '||' in commit_msg:
                # 格式是 "task_id||first_line"，提取第一行
                first_line = commit_msg.split('||', 1)[1]
                new_commit_messages.append(first_line)
            else:
                # 没有 '||' 分隔符，直接使用原始message
                new_commit_messages.append(commit_msg)
        
        return {
            'new_features': new_commit_messages,  # 返回优化后的commit message列表
            'new_commit_messages': new_commit_messages,  # 保持兼容性
            'old_tasks': result['old_tasks'],
            'new_tasks': result['new_tasks'],
            'common_tasks': result['common_tasks'],
            'analysis': result['analysis'],
            'total_time': result['total_time'],
            'error': result.get('error'),
            'old_commits_count': result.get('old_commits_count', 0),
            'new_commits_count': result.get('new_commits_count', 0),
            'detailed_analysis': filtered_detailed_analysis
        } 