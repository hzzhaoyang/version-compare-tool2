#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
版本比较服务 v2
使用高性能的GitLab Manager和Task Detector，支持多项目配置
"""
import os
import time
import json
import logging
from typing import Dict, Any, List, Optional
from ..gitlab.gitlab_manager import GitLabManager
from ..core.task_detector import TaskLossDetector

logger = logging.getLogger(__name__)


class ProjectConfigManager:
    """项目配置管理器 - 专门用于管理项目配置，不依赖GitLab连接"""
    
    def __init__(self):
        self.config_data = self._load_config()
    
    def _load_config(self) -> Dict[str, Any]:
        """加载项目配置文件"""
        config_path = os.path.join(os.path.dirname(__file__), '../../config/projects.json')
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"项目配置文件不存在: {config_path}，请从 projects.json.example 复制并配置")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            raise ValueError(f"加载项目配置文件失败: {e}")
    
    def get_all_projects(self) -> List[Dict[str, str]]:
        """获取所有项目列表（包括未配置环境变量的项目）"""
        projects = []
        project_definitions = self.config_data.get('projects', {})
        
        # 检查是否有统一的GitLab Token
        has_token = bool(os.getenv('GITLAB_TOKEN'))
        
        for project_key, project_info in project_definitions.items():
            projects.append({
                'key': project_key,
                'name_zh': project_info['name_zh'],
                'name_en': project_info['name_en'], 
                'project_id': project_info['project_id'],
                'has_valid_config': has_token
            })
        
        return projects
    
    def get_current_project_key(self) -> str:
        """获取当前默认项目key"""
        return self.config_data.get('default_project', 'complex-report-pro')


class ProjectConfig:
    """项目配置类"""
    def __init__(self, project_key: str, name_zh: str, name_en: str, project_id: str, token: str):
        self.project_key = project_key
        self.name_zh = name_zh  # 中文名
        self.name_en = name_en  # 英文名
        self.project_id = project_id
        self.token = token
    
    def __repr__(self):
        return f"ProjectConfig(key={self.project_key}, name_zh={self.name_zh}, name_en={self.name_en}, id={self.project_id})"


class VersionComparisonService:
    """版本比较服务 v2 - 高性能版本，支持多项目"""
    
    def __init__(self, project_key: Optional[str] = None):
        # 从环境变量获取配置
        self.gitlab_url = os.getenv('GITLAB_URL', 'https://gitlab.mayidata.com')
        
        # 支持的项目配置
        self.projects = self._load_project_configs()
        
        # 当前项目配置
        self.current_project = self._get_project_config(project_key)
        
        if not self.current_project:
            raise ValueError(f"无法找到项目配置: {project_key}")
        
        # 初始化核心组件（在演示模式下可能会失败，但不影响项目列表功能）
        try:
            self.gitlab_manager = GitLabManager(
                self.gitlab_url, 
                self.current_project.token, 
                self.current_project.project_id
            )
            self.task_detector = TaskLossDetector(self.gitlab_manager)
        except Exception as e:
            logger.warning(f"⚠️ GitLab连接失败（演示模式）: {e}")
            self.gitlab_manager = None
            self.task_detector = None
        
        logger.info(f"🚀 VersionComparisonService v2 初始化完成")
        logger.info(f"   GitLab URL: {self.gitlab_url}")
        logger.info(f"   当前项目: {self.current_project.name_zh} ({self.current_project.name_en}) (ID: {self.current_project.project_id})")
    
    def _load_project_configs(self) -> Dict[str, ProjectConfig]:
        """从JSON配置文件加载项目配置"""
        projects = {}
        
        # 加载项目配置文件
        config_path = os.path.join(os.path.dirname(__file__), '../../config/projects.json')
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"项目配置文件不存在: {config_path}，请从 projects.json.example 复制并配置")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
        except Exception as e:
            raise ValueError(f"加载项目配置文件失败: {e}")
        
        project_definitions = config_data.get('projects', {})
        if not project_definitions:
            raise ValueError("项目配置文件中未找到项目定义")
        
        # 获取统一的GitLab Token
        gitlab_token = os.getenv('GITLAB_TOKEN')
        
        # 遍历项目配置
        for project_key, project_info in project_definitions.items():
            project_id = project_info.get('project_id')
            
            if not project_id:
                logger.warning(f"⚠️ 项目配置不完整: {project_key} - 缺少project_id")
                continue
            
            # 如果没有token，使用演示模式
            token = gitlab_token if gitlab_token else 'demo_token'
            
            projects[project_key] = ProjectConfig(
                project_key=project_key,
                name_zh=project_info['name_zh'],
                name_en=project_info['name_en'],
                project_id=project_id,
                token=token
            )
            
            if gitlab_token:
                logger.info(f"✅ 加载项目配置: {project_info['name_zh']} ({project_info['name_en']}) [ID: {project_id}]")
            else:
                logger.info(f"📋 加载项目配置（演示模式）: {project_info['name_zh']} ({project_info['name_en']}) [ID: {project_id}]")
        
        if not projects:
            raise ValueError("未找到任何有效的项目配置")
        
        logger.info(f"📊 总计加载 {len(projects)} 个项目配置")
        return projects
    
    def _get_project_config(self, project_key: Optional[str]) -> Optional[ProjectConfig]:
        """获取项目配置"""
        if project_key and project_key in self.projects:
            return self.projects[project_key]
        
        # 如果没有指定项目，使用第一个可用的项目
        if self.projects:
            default_key = list(self.projects.keys())[0]
            logger.info(f"🔄 使用默认项目: {default_key}")
            return self.projects[default_key]
        
        return None
    
    def get_available_projects(self) -> List[Dict[str, str]]:
        """获取可用的项目列表"""
        return [
            {
                'key': config.project_key,
                'name_zh': config.name_zh,
                'name_en': config.name_en,
                'project_id': config.project_id
            }
            for config in self.projects.values()
        ]
    
    def switch_project(self, project_key: str) -> bool:
        """切换到指定项目"""
        if project_key not in self.projects:
            logger.error(f"❌ 项目不存在: {project_key}")
            return False
        
        old_project = self.current_project
        self.current_project = self.projects[project_key]
        
        # 重新初始化GitLab管理器（在演示模式下可能会失败，但不影响项目切换）
        try:
            self.gitlab_manager = GitLabManager(
                self.gitlab_url,
                self.current_project.token,
                self.current_project.project_id
            )
            self.task_detector = TaskLossDetector(self.gitlab_manager)
            logger.info(f"🔄 项目切换成功: {old_project.name_zh} -> {self.current_project.name_zh}")
        except Exception as e:
            logger.warning(f"⚠️ 项目切换到 {self.current_project.name_zh}，但GitLab连接失败（演示模式）: {e}")
            self.gitlab_manager = None
            self.task_detector = None
        
        return True
    
    def detect_missing_tasks(self, old_version: str, new_version: str) -> Dict[str, Any]:
        """
        检测缺失的tasks：旧版本有但新版本没有的tasks
        
        Args:
            old_version: 旧版本标签
            new_version: 新版本标签
            
        Returns:
            包含缺失tasks信息的字典
        """
        logger.info(f"🔍 开始检测缺失tasks: {old_version} -> {new_version}")
        
        start_time = time.time()
        try:
            result = self.task_detector.detect_missing_tasks(old_version, new_version)
            elapsed = time.time() - start_time
            
            logger.info(f"✅ 缺失tasks检测完成，耗时: {elapsed:.2f}s")
            
            # 添加服务层的统计信息
            result['service_stats'] = {
                'service_version': 'v2',
                'total_elapsed': elapsed,
                'gitlab_url': self.gitlab_url,
                'project_id': self.current_project.project_id
            }
            
            return result
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ 缺失tasks检测失败: {e}, 耗时: {elapsed:.2f}s")
            return {
                'missing_tasks': [],
                'analysis': 'error',
                'total_time': elapsed,
                'error': str(e),
                'service_stats': {
                    'service_version': 'v2',
                    'total_elapsed': elapsed,
                    'gitlab_url': self.gitlab_url,
                    'project_id': self.current_project.project_id
                }
            }
    
    def analyze_new_features(self, old_version: str, new_version: str) -> Dict[str, Any]:
        """
        分析新增features：新版本有但旧版本没有的tasks
        
        Args:
            old_version: 旧版本标签
            new_version: 新版本标签
            
        Returns:
            包含新增features信息的字典
        """
        logger.info(f"🆕 开始分析新增features: {old_version} -> {new_version}")
        
        start_time = time.time()
        try:
            result = self.task_detector.analyze_new_features(old_version, new_version)
            elapsed = time.time() - start_time
            
            logger.info(f"✅ 新增features分析完成，耗时: {elapsed:.2f}s")
            
            # 添加服务层的统计信息
            result['service_stats'] = {
                'service_version': 'v2',
                'total_elapsed': elapsed,
                'gitlab_url': self.gitlab_url,
                'project_id': self.current_project.project_id
            }
            
            return result
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ 新增features分析失败: {e}, 耗时: {elapsed:.2f}s")
            return {
                'new_features': [],
                'analysis': 'error',
                'total_time': elapsed,
                'error': str(e),
                'service_stats': {
                    'service_version': 'v2',
                    'total_elapsed': elapsed,
                    'gitlab_url': self.gitlab_url,
                    'project_id': self.current_project.project_id
                }
            }
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计信息"""
        return {
            'service_version': 'v2',
            'gitlab_manager_stats': self.gitlab_manager.get_performance_stats(),
            'features': [
                '并发分页获取commits',
                '二分查找探测总页数',
                '本地内存分析tasks',
                '详细的性能监控和日志',
                '去掉缓存，简化逻辑'
            ]
        }
    
    def analyze_tasks(self, task_ids: List[str], version: str) -> Dict[str, Any]:
        """
        分析指定的tasks
        
        Args:
            task_ids: 要分析的task ID列表
            version: 版本标签
            
        Returns:
            包含task分析信息的字典
        """
        logger.info(f"📊 开始分析tasks: {task_ids} in {version}")
        
        start_time = time.time()
        try:
            # 获取版本的所有commits和tasks
            commits = self.gitlab_manager.get_all_tag_commits_concurrent(version)
            commit_messages_with_tasks = self.gitlab_manager.extract_commit_messages_with_tasks(commits)
            
            # 分析指定的tasks
            found_tasks = {}
            missing_tasks = []
            
            for task_id in task_ids:
                task_commits = []
                for commit_message, extracted_task_id in commit_messages_with_tasks.items():
                    if extracted_task_id == task_id:
                        # 优化格式：从 "GALAXY-25259||GALAXY-25259【Bug】thirdparty data router add" 
                        # 优化为 "GALAXY-25259【Bug】thirdparty data router add"
                        if '||' in commit_message:
                            # 格式是 "task_id||first_line"，提取第一行
                            first_line = commit_message.split('||', 1)[1]
                            task_commits.append(first_line)
                        else:
                            # 没有 '||' 分隔符，直接使用原始message
                            task_commits.append(commit_message)
                
                if task_commits:
                    found_tasks[task_id] = {
                        'commit_count': len(task_commits),
                        'commit_messages': task_commits
                    }
                else:
                    missing_tasks.append(task_id)
            
            elapsed = time.time() - start_time
            
            result = {
                'version': version,
                'requested_tasks': task_ids,
                'found_tasks': found_tasks,
                'missing_tasks': missing_tasks,
                'total_commits': len(commits),
                'total_time': elapsed
            }
            
            logger.info(f"✅ tasks分析完成，耗时: {elapsed:.2f}s")
            return result
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ tasks分析失败: {e}, 耗时: {elapsed:.2f}s")
            return {
                'version': version,
                'requested_tasks': task_ids,
                'found_tasks': {},
                'missing_tasks': task_ids,
                'error': str(e),
                'total_time': elapsed
            }
    
    def search_tasks(self, task_id: str, version: str = None) -> Dict[str, Any]:
        """
        搜索tasks
        
        Args:
            task_id: 要搜索的task ID
            version: 版本标签，如果为None则搜索所有版本
            
        Returns:
            包含搜索结果的字典
        """
        logger.info(f"🔎 开始搜索task: {task_id} in {version or 'all versions'}")
        
        start_time = time.time()
        try:
            if version:
                # 在指定版本中搜索
                commits = self.gitlab_manager.get_all_tag_commits_concurrent(version)
                commit_messages_with_tasks = self.gitlab_manager.extract_commit_messages_with_tasks(commits)
                
                found_commits = []
                for commit_key, extracted_task_id in commit_messages_with_tasks.items():
                    if extracted_task_id == task_id:
                        # commit_key的格式是 "task_id||first_line"，提取第一行作为commit message
                        if '||' in commit_key:
                            commit_message = commit_key.split('||')[1]
                        else:
                            commit_message = commit_key
                        found_commits.append(commit_message)
                
                elapsed = time.time() - start_time
                
                result = {
                    'task_id': task_id,
                    'version': version,
                    'found': len(found_commits) > 0,
                    'commit_count': len(found_commits),
                    'commit_messages': found_commits,
                    'total_time': elapsed
                }
            else:
                # 搜索所有版本（这里可以扩展实现）
                elapsed = time.time() - start_time
                result = {
                    'task_id': task_id,
                    'version': 'all',
                    'found': False,
                    'error': '搜索所有版本功能暂未实现',
                    'total_time': elapsed
                }
            
            logger.info(f"✅ task搜索完成，耗时: {elapsed:.2f}s")
            return result
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ task搜索失败: {e}, 耗时: {elapsed:.2f}s")
            return {
                'task_id': task_id,
                'version': version,
                'found': False,
                'error': str(e),
                'total_time': elapsed
            }
    
    def validate_versions(self, versions: List[str]) -> Dict[str, Any]:
        """
        验证版本
        
        Args:
            versions: 要验证的版本列表
            
        Returns:
            包含验证结果的字典
        """
        logger.info(f"✅ 开始验证版本: {versions}")
        
        start_time = time.time()
        try:
            valid_versions = []
            invalid_versions = []
            
            for version in versions:
                try:
                    # 尝试获取版本的commits来验证版本是否存在
                    commits = self.gitlab_manager.get_all_tag_commits_concurrent(version)
                    if commits:
                        valid_versions.append({
                            'version': version,
                            'commit_count': len(commits)
                        })
                    else:
                        invalid_versions.append({
                            'version': version,
                            'reason': '版本存在但无commits'
                        })
                except Exception as e:
                    invalid_versions.append({
                        'version': version,
                        'reason': str(e)
                    })
            
            elapsed = time.time() - start_time
            
            result = {
                'requested_versions': versions,
                'valid_versions': valid_versions,
                'invalid_versions': invalid_versions,
                'total_time': elapsed
            }
            
            logger.info(f"✅ 版本验证完成，耗时: {elapsed:.2f}s")
            return result
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ 版本验证失败: {e}, 耗时: {elapsed:.2f}s")
            return {
                'requested_versions': versions,
                'valid_versions': [],
                'invalid_versions': [{'version': v, 'reason': str(e)} for v in versions],
                'error': str(e),
                'total_time': elapsed
            }
    
    def get_version_statistics(self, from_version: str, to_version: str) -> Dict[str, Any]:
        """
        获取版本间的统计信息
        
        Args:
            from_version: 起始版本
            to_version: 目标版本
            
        Returns:
            包含统计信息的字典
        """
        logger.info(f"📈 开始获取统计信息: {from_version} -> {to_version}")
        
        start_time = time.time()
        try:
            # 获取两个版本的数据
            old_commits = self.gitlab_manager.get_all_tag_commits_concurrent(from_version)
            new_commits = self.gitlab_manager.get_all_tag_commits_concurrent(to_version)
            
            old_tasks = self.gitlab_manager.extract_commit_messages_with_tasks(old_commits)
            new_tasks = self.gitlab_manager.extract_commit_messages_with_tasks(new_commits)
            
            # 计算统计信息
            old_task_ids = set(old_tasks.values())
            new_task_ids = set(new_tasks.values())
            
            missing_tasks = old_task_ids - new_task_ids
            new_features = new_task_ids - old_task_ids
            common_tasks = old_task_ids & new_task_ids
            
            elapsed = time.time() - start_time
            
            result = {
                'from_version': from_version,
                'to_version': to_version,
                'statistics': {
                    'old_version': {
                        'commit_count': len(old_commits),
                        'task_count': len(old_task_ids)
                    },
                    'new_version': {
                        'commit_count': len(new_commits),
                        'task_count': len(new_task_ids)
                    },
                    'comparison': {
                        'missing_tasks_count': len(missing_tasks),
                        'new_features_count': len(new_features),
                        'common_tasks_count': len(common_tasks)
                    }
                },
                'missing_tasks': list(missing_tasks),
                'new_features': list(new_features),
                'total_time': elapsed
            }
            
            logger.info(f"✅ 统计信息获取完成，耗时: {elapsed:.2f}s")
            return result
            
        except Exception as e:
            elapsed = time.time() - start_time
            logger.error(f"❌ 统计信息获取失败: {e}, 耗时: {elapsed:.2f}s")
            return {
                'from_version': from_version,
                'to_version': to_version,
                'error': str(e),
                'total_time': elapsed
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