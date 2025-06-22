#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
版本比较工具 API
基于FastAPI的高性能版本比较服务，支持多项目配置
"""
import os
import sys
import time
import logging
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, HTTPException, Query, Path
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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
    description="基于GitLab的高性能版本比较和task分析工具，支持多项目配置",
    version="2.1.0"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件服务 - 为前端静态资源提供服务
app.mount("/static", StaticFiles(directory="."), name="static")

# 全局服务实例缓存
version_services: Dict[str, VersionComparisonService] = {}


def get_version_service(project_key: Optional[str] = None) -> VersionComparisonService:
    """获取版本服务实例（支持多项目）"""
    # 如果没有指定项目，使用第一个可用的服务
    if project_key is None:
        if version_services:
            return list(version_services.values())[0]
        # 创建默认服务
        service = VersionComparisonService()
        version_services[service.current_project.project_key] = service
        return service
    
    # 检查是否已存在该项目的服务
    if project_key in version_services:
        return version_services[project_key]
    
    # 创建新的服务实例
    try:
        service = VersionComparisonService(project_key)
        version_services[project_key] = service
        return service
    except Exception as e:
        logger.error(f"❌ 创建项目服务失败 {project_key}: {e}")
        raise HTTPException(status_code=400, detail=f"无法创建项目服务: {project_key}")


class VersionRequest(BaseModel):
    old_version: str
    new_version: str
    project_key: Optional[str] = None


class TaskAnalysisRequest(BaseModel):
    task_ids: List[str]
    version: str
    project_key: Optional[str] = None


class TaskSearchRequest(BaseModel):
    task_id: str
    version: Optional[str] = None
    project_key: Optional[str] = None


class VersionValidationRequest(BaseModel):
    versions: List[str]
    project_key: Optional[str] = None


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
    project_info: Dict[str, str]


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
    project_info: Dict[str, str]


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化默认服务"""
    try:
        logger.info("🚀 初始化版本比较服务...")
        # 创建默认服务实例
        default_service = VersionComparisonService()
        version_services[default_service.current_project.project_key] = default_service
        logger.info("✅ 版本比较服务初始化完成")
    except Exception as e:
        logger.error(f"❌ 服务初始化失败: {e}")
        raise


@app.get("/version-compare")
async def serve_frontend():
    """根路径 - 返回前端网页"""
    import os
    current_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
    return FileResponse(os.path.join(current_dir, "index.html"))

@app.get("/api")
async def api_info():
    """API信息"""
    return {
        "name": "版本比较工具 API",
        "version": "2.1.0",
        "description": "基于GitLab的高性能版本比较和task分析工具，支持多项目配置",
        "features": [
            "并发分页获取commits",
            "二分查找探测总页数", 
            "本地内存分析tasks",
            "详细的性能监控和日志",
            "多项目支持",
            "项目动态切换"
        ],
        "endpoints": {
            "GET /": "前端静态网页",
            "GET /api": "API信息",
            "GET /api/config": "前端配置信息",
            "GET /api/projects": "获取可用项目列表",
            "GET /health": "健康检查",
            "POST /analyze-new-features": "分析新增features",
            "POST /detect-missing-tasks": "检测缺失tasks",
            "POST /analyze-tasks": "分析tasks",
            "POST /search-tasks": "搜索tasks",
            "POST /validate-versions": "验证版本",
            "GET /statistics/{from_version}/{to_version}": "获取统计信息"
        }
    }

@app.get("/api/config")
async def get_frontend_config():
    """获取前端配置信息"""
    return {
        "task_url_prefix": os.getenv("TASK_URL_PREFIX", "")
    }


@app.get("/api/projects")
async def get_available_projects():
    """获取可用的项目列表"""
    try:
        # 获取默认服务实例以获取项目列表
        service = get_version_service()
        projects = service.get_available_projects()
        
        # 添加当前选中的项目标识
        for project in projects:
            project['is_current'] = project['key'] == service.current_project.project_key
        
        return {
            "projects": projects,
            "current_project": service.current_project.project_key
        }
    except Exception as e:
        logger.error(f"❌ 获取项目列表失败: {e}")
        raise HTTPException(status_code=500, detail=f"获取项目列表失败: {str(e)}")


@app.get("/health")
async def health_check():
    """健康检查"""
    try:
        service = get_version_service()
        return {
            "status": "healthy",
            "service_version": "2.1.0",
            "timestamp": time.time(),
            "current_project": service.current_project.name,
            "available_projects": len(service.get_available_projects())
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"服务未初始化: {str(e)}")


@app.post("/analyze-new-features", response_model=NewFeaturesResponse)
async def analyze_new_features(request: VersionRequest):
    """
    分析新增features
    """
    api_start_time = time.time()
    logger.info(f"🆕 API请求: 分析新增features {request.old_version} -> {request.new_version} (项目: {request.project_key})")
    
    try:
        service = get_version_service(request.project_key)
        result = service.analyze_new_features(request.old_version, request.new_version)
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
                },
                project_info={
                    'key': service.current_project.project_key,
                    'name': service.current_project.name,
                    'project_id': service.current_project.project_id
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
            service_stats=service.get_performance_stats(),
            api_stats={
                'api_time': api_time,
                'endpoint': '/analyze-new-features'
            },
            project_info={
                'key': service.current_project.project_key,
                'name': service.current_project.name,
                'project_id': service.current_project.project_id
            }
        )
        
        logger.info(f"✅ API响应: {len(response.new_features)} 个新features, 耗时 {api_time:.2f}s")
        return response
        
    except Exception as e:
        api_time = time.time() - api_start_time
        error_msg = f"分析新增features失败: {str(e)}"
        logger.error(f"❌ {error_msg}")
        
        return NewFeaturesResponse(
            new_features=[],
            analysis="error",
            total_time=0,
            error=error_msg,
            old_commits_count=0,
            new_commits_count=0,
            old_tasks_count=0,
            new_tasks_count=0,
            detailed_analysis=None,
            service_stats={},
            api_stats={
                'api_time': api_time,
                'endpoint': '/analyze-new-features',
                'error': error_msg
            },
            project_info={
                'key': request.project_key or 'unknown',
                'name': 'Unknown',
                'project_id': 'unknown'
            }
        )


@app.post("/detect-missing-tasks", response_model=MissingTasksResponse)
async def detect_missing_tasks(request: VersionRequest):
    """
    检测缺失tasks
    """
    api_start_time = time.time()
    logger.info(f"🔍 API请求: 检测缺失tasks {request.old_version} -> {request.new_version} (项目: {request.project_key})")
    
    try:
        service = get_version_service(request.project_key)
        result = service.detect_missing_tasks(request.old_version, request.new_version)
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
                },
                project_info={
                    'key': service.current_project.project_key,
                    'name': service.current_project.name,
                    'project_id': service.current_project.project_id
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
            missing_tasks=result.get('missing_tasks', []),
            analysis=result.get('analysis', 'success'),
            total_time=result.get('total_time', 0),
            error=None,
            old_commits_count=result.get('old_commits_count', 0),
            new_commits_count=result.get('new_commits_count', 0),
            old_tasks_count=len(result.get('old_tasks', set())),
            new_tasks_count=len(result.get('new_tasks', set())),
            detailed_analysis=detailed_analysis,
            service_stats=service.get_performance_stats(),
            api_stats={
                'api_time': api_time,
                'endpoint': '/detect-missing-tasks'
            },
            project_info={
                'key': service.current_project.project_key,
                'name': service.current_project.name,
                'project_id': service.current_project.project_id
            }
        )
        
        logger.info(f"✅ API响应: {len(response.missing_tasks)} 个缺失tasks, 耗时 {api_time:.2f}s")
        return response
        
    except Exception as e:
        api_time = time.time() - api_start_time
        error_msg = f"检测缺失tasks失败: {str(e)}"
        logger.error(f"❌ {error_msg}")
        
        return MissingTasksResponse(
            missing_tasks=[],
            analysis="error",
            total_time=0,
            error=error_msg,
            old_commits_count=0,
            new_commits_count=0,
            old_tasks_count=0,
            new_tasks_count=0,
            detailed_analysis=None,
            service_stats={},
            api_stats={
                'api_time': api_time,
                'endpoint': '/detect-missing-tasks',
                'error': error_msg
            },
            project_info={
                'key': request.project_key or 'unknown',
                'name': 'Unknown',
                'project_id': 'unknown'
            }
        )


@app.post("/analyze-tasks")
async def analyze_tasks(request: TaskAnalysisRequest):
    """
    分析指定的tasks
    """
    api_start_time = time.time()
    logger.info(f"📊 API请求: 分析tasks {request.task_ids} in {request.version} (项目: {request.project_key})")
    
    try:
        service = get_version_service(request.project_key)
        result = service.analyze_tasks(request.task_ids, request.version)
        api_time = time.time() - api_start_time
        
        logger.info(f"✅ API响应: 分析tasks完成, 耗时 {api_time:.2f}s")
        result['api_stats'] = {
            'api_time': api_time,
            'endpoint': '/analyze-tasks'
        }
        result['project_info'] = {
            'key': service.current_project.project_key,
            'name': service.current_project.name,
            'project_id': service.current_project.project_id
        }
        return result
        
    except Exception as e:
        api_time = time.time() - api_start_time
        error_msg = f"分析tasks失败: {str(e)}"
        logger.error(f"❌ {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)


@app.post("/search-tasks")
async def search_tasks(request: TaskSearchRequest):
    """
    搜索指定的task
    """
    api_start_time = time.time()
    logger.info(f"🔎 API请求: 搜索task {request.task_id} in {request.version} (项目: {request.project_key})")
    
    try:
        service = get_version_service(request.project_key)
        result = service.search_tasks(request.task_id, request.version)
        api_time = time.time() - api_start_time
        
        logger.info(f"✅ API响应: 搜索task完成, 耗时 {api_time:.2f}s")
        result['api_stats'] = {
            'api_time': api_time,
            'endpoint': '/search-tasks'
        }
        result['project_info'] = {
            'key': service.current_project.project_key,
            'name': service.current_project.name,
            'project_id': service.current_project.project_id
        }
        return result
        
    except Exception as e:
        api_time = time.time() - api_start_time
        error_msg = f"搜索tasks失败: {str(e)}"
        logger.error(f"❌ {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)


@app.post("/validate-versions")
async def validate_versions(request: VersionValidationRequest):
    """
    验证版本是否存在
    """
    api_start_time = time.time()
    logger.info(f"✔️ API请求: 验证版本 {request.versions} (项目: {request.project_key})")
    
    try:
        service = get_version_service(request.project_key)
        result = service.validate_versions(request.versions)
        api_time = time.time() - api_start_time
        
        logger.info(f"✅ API响应: 验证版本完成, 耗时 {api_time:.2f}s")
        result['api_stats'] = {
            'api_time': api_time,
            'endpoint': '/validate-versions'
        }
        result['project_info'] = {
            'key': service.current_project.project_key,
            'name': service.current_project.name,
            'project_id': service.current_project.project_id
        }
        return result
        
    except Exception as e:
        api_time = time.time() - api_start_time
        error_msg = f"验证版本失败: {str(e)}"
        logger.error(f"❌ {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)


@app.get("/statistics/{from_version}/{to_version}")
async def get_statistics(
    from_version: str = Path(..., description="起始版本"),
    to_version: str = Path(..., description="目标版本"),
    project_key: Optional[str] = Query(None, description="项目标识")
):
    """
    获取两个版本之间的统计信息
    """
    api_start_time = time.time()
    logger.info(f"📈 API请求: 获取统计信息 {from_version} -> {to_version} (项目: {project_key})")
    
    try:
        service = get_version_service(project_key)
        result = service.get_version_statistics(from_version, to_version)
        api_time = time.time() - api_start_time
        
        logger.info(f"✅ API响应: 获取统计信息完成, 耗时 {api_time:.2f}s")
        result['api_stats'] = {
            'api_time': api_time,
            'endpoint': '/statistics'
        }
        result['project_info'] = {
            'key': service.current_project.project_key,
            'name': service.current_project.name,
            'project_id': service.current_project.project_id
        }
        return result
        
    except Exception as e:
        api_time = time.time() - api_start_time
        error_msg = f"获取统计信息失败: {str(e)}"
        logger.error(f"❌ {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 9112))) 