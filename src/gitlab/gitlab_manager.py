#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitLab API管理器 v2
基于并发分页获取的高性能版本，简化逻辑，增强日志
"""
import re
import time
import logging
from typing import List, Dict, Any, Optional, Set
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import requests

# 确保导入正确的gitlab包，避免与本地模块冲突
import sys
import importlib
# 临时移除本地路径，确保导入python-gitlab包
current_path = sys.path[:]
sys.path = [p for p in sys.path if not p.endswith('src')]
gitlab = importlib.import_module('gitlab')
sys.path = current_path


logger = logging.getLogger(__name__)


class GitLabManager:
    """GitLab API管理器 - 高性能版本"""
    
    def __init__(self, gitlab_url: str, token: str, project_id: str):
        self.gitlab_url = gitlab_url
        self.token = token
        self.project_id = project_id
        
        # 初始化GitLab连接
        self.gitlab = gitlab.Gitlab(gitlab_url, private_token=token)
        self.project = self.gitlab.projects.get(project_id)
        
        # Task正则表达式 - 支持GALAXY-XXX和OP-XXX格式
        self.task_pattern = re.compile(r'(GALAXY-\d+|OP-\d+)')
        
        # 性能配置
        self.config = {
            'per_page': 100,        # 每页commits数量，降低到100避免超时
            'max_workers': 8,       # 并发工作线程数，降低避免过载
            'timeout': 30,          # 请求超时时间
            'retry_attempts': 3,    # 重试次数
        }
        
        # 用于直接API调用的headers
        self.headers = {
            'PRIVATE-TOKEN': token,
            'Content-Type': 'application/json'
        }
        
        logger.info(f"[{self._timestamp()}] 🚀 GitLabManager初始化完成: {gitlab_url}, 项目ID: {project_id}")
        logger.info(f"[{self._timestamp()}] ⚙️ 配置: 每页{self.config['per_page']}个commits, {self.config['max_workers']}个并发worker")
    
    def _timestamp(self) -> str:
        """生成带毫秒的时间戳"""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    
    def get_all_tag_commits(self, tag_name: str) -> List[Dict[str, Any]]:
        """
        获取tag的所有commits - 简化版本，逐页获取直到没有数据
        """
        start_time = time.time()
        logger.info(f"[{self._timestamp()}] 📥 开始获取tag commits: {tag_name}")
        
        all_commits = []
        page = 1
        total_pages = 0
        
        while True:
            logger.info(f"[{self._timestamp()}] 📄 正在获取第 {page} 页...")
            
            page_commits = self._fetch_single_page(tag_name, page)
            
            if not page_commits:
                logger.info(f"[{self._timestamp()}] 🏁 第 {page} 页没有数据，获取完成")
                total_pages = page - 1
                break
            
            all_commits.extend(page_commits)
            logger.info(f"[{self._timestamp()}] ✅ 第 {page} 页获取到 {len(page_commits)} 个commits，累计 {len(all_commits)} 个")
            
            # 如果这一页的数据少于每页配置数量，说明是最后一页
            if len(page_commits) < self.config['per_page']:
                logger.info(f"[{self._timestamp()}] 🏁 第 {page} 页数据不足 {self.config['per_page']} 个，确认为最后一页")
                total_pages = page
                break
            
            page += 1
            
            # 安全检查，避免无限循环
            if page > 1000:
                logger.warning(f"[{self._timestamp()}] ⚠️ 页数超过1000，强制停止")
                total_pages = page - 1
                break
        
        elapsed = time.time() - start_time
        logger.info(f"[{self._timestamp()}] 🎯 获取完成统计:")
        logger.info(f"    📊 Tag: {tag_name}")
        logger.info(f"    📊 总页数: {total_pages}")
        logger.info(f"    📊 总commits: {len(all_commits)}")
        logger.info(f"    📊 耗时: {elapsed:.2f}s")
        logger.info(f"    📊 速度: {len(all_commits)/elapsed:.1f} commits/s")
        
        return all_commits
    
    def _fetch_single_page(self, ref_name: str, page: int) -> List[Dict[str, Any]]:
        """获取单页commits"""
        url = f"{self.gitlab_url}/api/v4/projects/{self.project_id}/repository/commits"
        params = {
            'ref_name': ref_name,
            'per_page': self.config['per_page'],
            'page': page
        }
        
        for attempt in range(self.config['retry_attempts']):
            try:
                logger.debug(f"[{self._timestamp()}] 🔗 请求第 {page} 页 (尝试 {attempt + 1}/{self.config['retry_attempts']})")
                
                response = requests.get(
                    url, 
                    headers=self.headers, 
                    params=params, 
                    timeout=self.config['timeout']
                )
                
                if response.status_code == 200:
                    commits = response.json()
                    
                    # 简化commit数据，只保留必要字段
                    simplified_commits = []
                    for commit in commits:
                        simplified_commits.append({
                            'id': commit.get('id'),
                            'message': commit.get('message', ''),
                            'author_name': commit.get('author_name', ''),
                            'committed_date': commit.get('committed_date', ''),
                            'short_id': commit.get('short_id', '')
                        })
                    
                    logger.debug(f"[{self._timestamp()}] ✅ 第 {page} 页请求成功，获取 {len(simplified_commits)} 个commits")
                    return simplified_commits
                    
                elif response.status_code == 404:
                    logger.warning(f"[{self._timestamp()}] ⚠️ 第 {page} 页返回404，可能已到末尾")
                    return []
                    
                else:
                    logger.warning(f"[{self._timestamp()}] ⚠️ 第 {page} 页请求失败: HTTP {response.status_code}")
                    if attempt == self.config['retry_attempts'] - 1:
                        return []
                    time.sleep(0.5 * (attempt + 1))
                    
            except Exception as e:
                logger.warning(f"[{self._timestamp()}] ⚠️ 第 {page} 页请求异常: {e}")
                if attempt == self.config['retry_attempts'] - 1:
                    return []
                time.sleep(0.5 * (attempt + 1))
        
        return []
    
    def get_all_tag_commits_concurrent(self, tag_name: str) -> List[Dict[str, Any]]:
        """
        并发获取tag的所有commits - 先探测总页数，再并发获取
        """
        start_time = time.time()
        logger.info(f"[{self._timestamp()}] 📥 开始并发获取tag commits: {tag_name}")
        
        # 第一步：探测总页数
        logger.info(f"[{self._timestamp()}] 🔍 第一步：探测总页数...")
        total_pages = self._detect_total_pages(tag_name)
        
        if total_pages == 0:
            logger.warning(f"[{self._timestamp()}] ⚠️ 未检测到任何页面，tag可能不存在或没有commits")
            return []
        
        logger.info(f"[{self._timestamp()}] 📊 检测到总页数: {total_pages}")
        
        # 第二步：并发获取所有页面
        logger.info(f"[{self._timestamp()}] 🚀 第二步：并发获取 {total_pages} 页...")
        all_commits = self._fetch_all_pages_concurrent(tag_name, total_pages)
        
        elapsed = time.time() - start_time
        logger.info(f"[{self._timestamp()}] 🎯 并发获取完成统计:")
        logger.info(f"    📊 Tag: {tag_name}")
        logger.info(f"    📊 总页数: {total_pages}")
        logger.info(f"    📊 总commits: {len(all_commits)}")
        logger.info(f"    📊 耗时: {elapsed:.2f}s")
        logger.info(f"    📊 速度: {len(all_commits)/elapsed:.1f} commits/s")
        
        return all_commits
    
    def _detect_total_pages(self, ref_name: str) -> int:
        """探测总页数 - 简单方案，逐页检查直到没有数据"""
        logger.info(f"[{self._timestamp()}] 🔍 开始探测 {ref_name} 的总页数...")
        
        # 先检查第1页
        first_page = self._fetch_single_page(ref_name, 1)
        if not first_page:
            logger.info(f"[{self._timestamp()}] 📊 第1页没有数据，总页数: 0")
            return 0
        
        if len(first_page) < self.config['per_page']:
            logger.info(f"[{self._timestamp()}] 📊 第1页只有 {len(first_page)} 个commits，总页数: 1")
            return 1
        
        # 使用二分查找快速定位最后一页
        left, right = 1, 500  # 假设最多500页
        last_valid_page = 1
        
        logger.info(f"[{self._timestamp()}] 🔍 使用二分查找探测最后一页 (范围: 1-{right})")
        
        while left <= right:
            mid = (left + right) // 2
            logger.debug(f"[{self._timestamp()}] 🔍 检查第 {mid} 页...")
            
            page_data = self._fetch_single_page(ref_name, mid)
            
            if page_data:  # 这一页有数据
                last_valid_page = mid
                left = mid + 1
                logger.debug(f"[{self._timestamp()}] ✅ 第 {mid} 页有 {len(page_data)} 个commits，继续向右查找")
            else:  # 这一页没数据，说明超出了
                right = mid - 1
                logger.debug(f"[{self._timestamp()}] ❌ 第 {mid} 页没有数据，向左查找")
        
        logger.info(f"[{self._timestamp()}] 📊 探测完成，总页数: {last_valid_page}")
        return last_valid_page
    
    def _fetch_all_pages_concurrent(self, ref_name: str, total_pages: int) -> List[Dict[str, Any]]:
        """并发获取所有页面的commits"""
        all_commits = []
        
        logger.info(f"[{self._timestamp()}] 🔄 启动 {self.config['max_workers']} 个并发worker处理 {total_pages} 页")
        
        with ThreadPoolExecutor(max_workers=self.config['max_workers']) as executor:
            # 提交所有任务
            futures = []
            for page in range(1, total_pages + 1):
                future = executor.submit(self._fetch_single_page, ref_name, page)
                futures.append((page, future))
            
            # 收集结果
            successful_pages = 0
            failed_pages = 0
            
            for page_num, future in futures:
                try:
                    commits = future.result()
                    if commits:
                        all_commits.extend(commits)
                        successful_pages += 1
                        logger.debug(f"[{self._timestamp()}] ✅ 第 {page_num} 页成功获取 {len(commits)} 个commits")
                    else:
                        failed_pages += 1
                        logger.warning(f"[{self._timestamp()}] ❌ 第 {page_num} 页获取失败")
                except Exception as e:
                    failed_pages += 1
                    logger.error(f"[{self._timestamp()}] ❌ 第 {page_num} 页处理异常: {e}")
        
        logger.info(f"[{self._timestamp()}] 📊 并发获取统计: 成功 {successful_pages} 页, 失败 {failed_pages} 页")
        
        return all_commits
    
    def extract_commit_messages_with_tasks(self, commits: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        从commits中提取包含task的commit message
        基于task ID和message第一行的组合来判断，忽略cherry-pick等差异
        
        Args:
            commits: commit列表
            
        Returns:
            Dict[str, str]: {task_id_with_first_line: primary_task_id} 映射
        """
        start_time = time.time()
        logger.info(f"[{self._timestamp()}] 🧮 开始从 {len(commits)} 个commits中提取task相关的commit messages...")
        
        commit_task_map = {}
        
        for i, commit in enumerate(commits):
            message = commit.get('message', '').strip()
            # 查找包含task ID的commit message
            found_tasks = self.task_pattern.findall(message)
            if found_tasks:
                # 提取message的第一行
                first_line = message.split('\n')[0].strip()
                
                # 为每个找到的task ID都创建一个记录
                # 这样可以处理一个commit包含多个task的情况
                for task_id in found_tasks:
                    # 使用task ID + 第一行作为唯一标识，这样可以：
                    # 1. 避免cherry-pick信息的干扰
                    # 2. 保留核心的功能描述信息
                    # 3. 同一个task的不同commit仍然能被区分
                    # 4. 一个commit包含多个task时，每个task都能被正确识别
                    task_with_first_line = f"{task_id}||{first_line}"
                    commit_task_map[task_with_first_line] = task_id
            
            if (i + 1) % 1000 == 0:  # 每1000个commits打印一次进度
                logger.debug(f"[{self._timestamp()}] 📊 已处理 {i + 1}/{len(commits)} 个commits，当前找到 {len(commit_task_map)} 个task相关commits")
        
        elapsed = time.time() - start_time
        logger.info(f"[{self._timestamp()}] 🎯 Commit message提取完成:")
        logger.info(f"    📊 处理commits: {len(commits)} 个")
        logger.info(f"    📊 包含task的commits: {len(commit_task_map)} 个")
        logger.info(f"    📊 耗时: {elapsed:.3f}s")
        logger.info(f"    📊 使用task ID + 第一行组合 (忽略cherry-pick和其他差异)")
        
        if commit_task_map:
            # 显示前几个示例
            sample_items = list(commit_task_map.items())[:5]
            logger.info(f"    📊 前5个示例:")
            for key, task in sample_items:
                # 提取第一行用于显示
                first_line = key.split('||')[1] if '||' in key else key
                short_msg = first_line[:50] + "..." if len(first_line) > 50 else first_line
                logger.info(f"        {task}: {short_msg}")
        
        return commit_task_map
    
    def extract_tasks_from_commits(self, commits: List[Dict[str, Any]]) -> Set[str]:
        """
        从commits中提取tasks（兼容旧接口）
        """
        commit_task_map = self.extract_commit_messages_with_tasks(commits)
        return set(commit_task_map.values())
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """获取性能统计"""
        return {
            'config': self.config,
            'gitlab_url': self.gitlab_url,
            'project_id': self.project_id
        }
    
    def _normalize_commit_message(self, message: str) -> str:
        """
        标准化commit message，移除cherry-pick等信息以便准确比较
        
        Args:
            message: 原始commit message
            
        Returns:
            标准化后的commit message
        """
        # 移除cherry-pick信息
        # 格式: (cherry picked from commit xxx)
        import re
        
        # 移除cherry-pick行及其前面的空行
        normalized = re.sub(r'\n*\(cherry picked from commit [a-f0-9]+\)\s*$', '', message, flags=re.MULTILINE)
        
        # 移除末尾的多余空白字符
        normalized = normalized.rstrip()
        
        return normalized 