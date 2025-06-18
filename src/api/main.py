#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
版本比较工具 API
基于FastAPI的高性能版本比较服务
"""
import os
import sys
import time
import logging
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 导入版本比较服务
from src.services.version_service import VersionComparisonService

# 加载环境变量
load_dotenv()

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 创建FastAPI应用
app = FastAPI(
    title="版本比较工具 API",
    description="基于GitLab的高性能版本比较和task分析工具",
    version="2.0.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局服务实例
version_service: Optional[VersionComparisonService] = None


class VersionRequest(BaseModel):
    old_version: str
    new_version: str


class TaskAnalysisRequest(BaseModel):
    task_ids: List[str]
    version: str


class TaskSearchRequest(BaseModel):
    task_id: str
    version: Optional[str] = None


class VersionValidationRequest(BaseModel):
    versions: List[str]


class MissingTasksDetailedAnalysis(BaseModel):
    """专门用于缺失tasks检测的详细分析"""
    completely_missing_tasks: List[str]
    partially_missing_tasks: Dict[str, List[str]]
    missing_commit_count: int


class NewFeaturesDetailedAnalysis(BaseModel):
    """专门用于新增features分析的详细分析"""
    completely_new_tasks: List[str]
    partially_new_tasks: Dict[str, List[str]]
    new_commit_count: int


class MissingTasksResponse(BaseModel):
    missing_tasks: List[str]
    analysis: str
    total_time: float
    error: Optional[str]
    old_commits_count: int
    new_commits_count: int
    old_tasks_count: int
    new_tasks_count: int
    detailed_analysis: Optional[MissingTasksDetailedAnalysis]
    service_stats: Dict[str, Any]
    api_stats: Dict[str, Any]


class NewFeaturesResponse(BaseModel):
    new_features: List[str]  # 直接返回commit message文本列表
    analysis: str
    total_time: float
    error: Optional[str]
    old_commits_count: int
    new_commits_count: int
    old_tasks_count: int
    new_tasks_count: int
    detailed_analysis: Optional[NewFeaturesDetailedAnalysis]
    service_stats: Dict[str, Any]
    api_stats: Dict[str, Any]


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化服务"""
    global version_service
    try:
        logger.info("🚀 初始化版本比较服务...")
        version_service = VersionComparisonService()
        logger.info("✅ 版本比较服务初始化完成")
    except Exception as e:
        logger.error(f"❌ 服务初始化失败: {e}")
        raise


@app.get("/")
async def root():
    """根路径 - API信息"""
    return {
        "name": "版本比较工具 API",
        "version": "2.0.0",
        "description": "基于GitLab的高性能版本比较和task分析工具",
        "features": [
            "并发分页获取commits",
            "二分查找探测总页数", 
            "本地内存分析tasks",
            "详细的性能监控和日志",
            "去掉缓存，简化逻辑"
        ],
        "endpoints": {
            "GET /": "API信息",
            "GET /health": "健康检查",
            "POST /analyze-new-features": "分析新增features",
            "POST /detect-missing-tasks": "检测缺失tasks",
            "POST /analyze-tasks": "分析tasks",
            "POST /search-tasks": "搜索tasks",
            "POST /validate-versions": "验证版本",
            "GET /statistics/{from_version}/{to_version}": "获取统计信息"
        }
    }


@app.get("/health")
async def health_check():
    """健康检查"""
    if version_service is None:
        raise HTTPException(status_code=503, detail="服务未初始化")
    
    return {
        "status": "healthy",
        "service_version": "2.0.0",
        "timestamp": time.time()
    }


@app.post("/analyze-new-features", response_model=NewFeaturesResponse)
async def analyze_new_features(request: VersionRequest):
    """
    分析新增features
    """
    api_start_time = time.time()
    logger.info(f"🆕 API请求: 分析新增features {request.old_version} -> {request.new_version}")
    
    try:
        result = version_service.analyze_new_features(request.old_version, request.new_version)
        api_time = time.time() - api_start_time
        
        # 检查是否有错误
        if result.get('analysis') == 'error':
            return NewFeaturesResponse(
                new_features=[],
                analysis="error",
                total_time=result.get('total_time', 0),
                error=result.get('error', 'Unknown error'),
                old_commits_count=0,
                new_commits_count=0,
                old_tasks_count=0,
                new_tasks_count=0,
                detailed_analysis=None,
                service_stats=result.get('service_stats', {}),
                api_stats={
                    'api_time': api_time,
                    'endpoint': '/analyze-new-features',
                    'error': result.get('error', 'Unknown error')
                }
            )
        
        # 构建详细分析结果
        detailed_analysis = None
        if 'detailed_analysis' in result:
            detail = result['detailed_analysis']
            detailed_analysis = NewFeaturesDetailedAnalysis(
                completely_new_tasks=sorted(list(detail.get('completely_new_tasks', set()))),
                partially_new_tasks=detail.get('partially_new_tasks', {}),
                new_commit_count=len(detail.get('new_commit_messages', set()))
            )
        
        response = NewFeaturesResponse(
            new_features=result.get('new_features', []),  # 直接使用new_features列表
            analysis=result.get('analysis', 'success'),
            total_time=result.get('total_time', 0),
            error=None,
            old_commits_count=result.get('old_commits_count', 0),
            new_commits_count=result.get('new_commits_count', 0),
            old_tasks_count=len(result.get('old_tasks', set())),
            new_tasks_count=len(result.get('new_tasks', set())),
            detailed_analysis=detailed_analysis,
            service_stats=version_service.get_performance_stats(),
            api_stats={
                'api_time': api_time,
                'endpoint': '/analyze-new-features'
            }
        )
        
        logger.info(f"✅ API响应: 新增features分析完成，API耗时: {api_time:.2f}s")
        return response
        
    except Exception as e:
        api_time = time.time() - api_start_time
        logger.error(f"❌ API错误: {str(e)}")
        return NewFeaturesResponse(
            new_features=[],
            analysis="error",
            total_time=0,
            error=str(e),
            old_commits_count=0,
            new_commits_count=0,
            old_tasks_count=0,
            new_tasks_count=0,
            detailed_analysis=None,
            service_stats={},
            api_stats={
                'api_time': api_time,
                'endpoint': '/analyze-new-features',
                'error': str(e)
            }
        )


@app.post("/detect-missing-tasks", response_model=MissingTasksResponse)
async def detect_missing_tasks(request: VersionRequest):
    """
    检测缺失的tasks
    """
    api_start_time = time.time()
    logger.info(f"🔍 API请求: 检测缺失tasks {request.old_version} -> {request.new_version}")
    
    try:
        result = version_service.detect_missing_tasks(request.old_version, request.new_version)
        api_time = time.time() - api_start_time
        
        # 检查是否有错误
        if result.get('analysis') == 'error':
            return MissingTasksResponse(
                missing_tasks=[],
                analysis="error",
                total_time=result.get('total_time', 0),
                error=result.get('error', 'Unknown error'),
                old_commits_count=0,
                new_commits_count=0,
                old_tasks_count=0,
                new_tasks_count=0,
                detailed_analysis=None,
                service_stats=result.get('service_stats', {}),
                api_stats={
                    'api_time': api_time,
                    'endpoint': '/detect-missing-tasks',
                    'error': result.get('error', 'Unknown error')
                }
            )
        
        # 构建详细分析结果
        detailed_analysis = None
        if 'detailed_analysis' in result:
            detail = result['detailed_analysis']
            detailed_analysis = MissingTasksDetailedAnalysis(
                completely_missing_tasks=sorted(list(detail.get('completely_missing_tasks', set()))),
                partially_missing_tasks=detail.get('partially_missing_tasks', {}),
                missing_commit_count=len(detail.get('missing_commit_messages', set()))
            )
        
        response = MissingTasksResponse(
            missing_tasks=sorted(list(result.get('missing_tasks', set()))),
            analysis=result.get('analysis', 'success'),
            total_time=result.get('total_time', 0),
            error=None,
            old_commits_count=result.get('old_commits_count', 0),
            new_commits_count=result.get('new_commits_count', 0),
            old_tasks_count=len(result.get('old_tasks', set())),
            new_tasks_count=len(result.get('new_tasks', set())),
            detailed_analysis=detailed_analysis,
            service_stats=version_service.get_performance_stats(),
            api_stats={
                'api_time': api_time,
                'endpoint': '/detect-missing-tasks'
            }
        )
        
        logger.info(f"✅ API响应: 缺失tasks检测完成，API耗时: {api_time:.2f}s")
        return response
        
    except Exception as e:
        api_time = time.time() - api_start_time
        logger.error(f"❌ API错误: {str(e)}")
        return MissingTasksResponse(
            missing_tasks=[],
            analysis="error",
            total_time=0,
            error=str(e),
            old_commits_count=0,
            new_commits_count=0,
            old_tasks_count=0,
            new_tasks_count=0,
            detailed_analysis=None,
            service_stats={},
            api_stats={
                'api_time': api_time,
                'endpoint': '/detect-missing-tasks',
                'error': str(e)
            }
        )


@app.post("/analyze-tasks")
async def analyze_tasks(request: TaskAnalysisRequest):
    """
    分析指定的tasks
    
    分析指定task IDs在指定版本中的详细信息
    """
    if version_service is None:
        raise HTTPException(status_code=503, detail="服务未初始化")
    
    logger.info(f"📊 API请求: 分析tasks {request.task_ids} in {request.version}")
    
    try:
        start_time = time.time()
        result = version_service.analyze_tasks(request.task_ids, request.version)
        api_elapsed = time.time() - start_time
        
        # 添加API层统计
        result['api_stats'] = {
            'api_version': '2.0.0',
            'api_elapsed': api_elapsed,
            'request_timestamp': start_time
        }
        
        logger.info(f"✅ API响应: tasks分析完成，API耗时: {api_elapsed:.2f}s")
        return result
        
    except Exception as e:
        logger.error(f"❌ API错误: tasks分析失败: {e}")
        raise HTTPException(status_code=500, detail=f"分析失败: {str(e)}")


@app.post("/search-tasks")
async def search_tasks(request: TaskSearchRequest):
    """
    搜索tasks
    
    在指定版本中搜索特定的task ID
    """
    if version_service is None:
        raise HTTPException(status_code=503, detail="服务未初始化")
    
    logger.info(f"🔎 API请求: 搜索task {request.task_id} in {request.version}")
    
    try:
        start_time = time.time()
        result = version_service.search_tasks(request.task_id, request.version)
        api_elapsed = time.time() - start_time
        
        # 添加API层统计
        result['api_stats'] = {
            'api_version': '2.0.0',
            'api_elapsed': api_elapsed,
            'request_timestamp': start_time
        }
        
        logger.info(f"✅ API响应: task搜索完成，API耗时: {api_elapsed:.2f}s")
        return result
        
    except Exception as e:
        logger.error(f"❌ API错误: task搜索失败: {e}")
        raise HTTPException(status_code=500, detail=f"搜索失败: {str(e)}")


@app.post("/validate-versions")
async def validate_versions(request: VersionValidationRequest):
    """
    验证版本
    
    验证指定的版本是否存在于GitLab中
    """
    if version_service is None:
        raise HTTPException(status_code=503, detail="服务未初始化")
    
    logger.info(f"✅ API请求: 验证版本 {request.versions}")
    
    try:
        start_time = time.time()
        result = version_service.validate_versions(request.versions)
        api_elapsed = time.time() - start_time
        
        # 添加API层统计
        result['api_stats'] = {
            'api_version': '2.0.0',
            'api_elapsed': api_elapsed,
            'request_timestamp': start_time
        }
        
        logger.info(f"✅ API响应: 版本验证完成，API耗时: {api_elapsed:.2f}s")
        return result
        
    except Exception as e:
        logger.error(f"❌ API错误: 版本验证失败: {e}")
        raise HTTPException(status_code=500, detail=f"验证失败: {str(e)}")


@app.get("/statistics/{from_version}/{to_version}")
async def get_statistics(
    from_version: str = Path(..., description="起始版本"),
    to_version: str = Path(..., description="目标版本")
):
    """获取版本间的统计信息"""
    if version_service is None:
        raise HTTPException(status_code=503, detail="服务未初始化")
    
    logger.info(f"📈 API请求: 获取统计信息 {from_version} -> {to_version}")
    
    try:
        start_time = time.time()
        result = version_service.get_version_statistics(from_version, to_version)
        api_elapsed = time.time() - start_time
        
        # 添加API层统计
        result['api_stats'] = {
            'api_version': '2.0.0',
            'api_elapsed': api_elapsed,
            'request_timestamp': start_time
        }
        
        logger.info(f"✅ API响应: 统计信息获取完成，API耗时: {api_elapsed:.2f}s")
        return result
        
    except Exception as e:
        logger.error(f"❌ API错误: 统计信息获取失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取失败: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 