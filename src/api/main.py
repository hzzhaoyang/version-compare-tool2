"""
FastAPI 主服务 - 简化版
基于GitLab Search API的高效版本比较服务
"""
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Dict, Any, List, Optional
import os
from dotenv import load_dotenv

from ..services.version_service import VersionCompareService

# 加载环境变量
load_dotenv()

app = FastAPI(
    title="Version Compare Tool - Simplified",
    description="基于GitLab Search API的高效版本比较和task检测服务",
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

# 请求模型
class VersionUpgradeRequest(BaseModel):
    old_version: str = Field(..., description="旧版本标识")
    new_version: str = Field(..., description="新版本标识")

class TaskAnalysisRequest(BaseModel):
    task_ids: List[str] = Field(..., description="要分析的task ID列表")
    branch_name: str = Field(..., description="目标分支名称")

class SearchTasksRequest(BaseModel):
    version: str = Field(..., description="版本标识")
    task_pattern: str = Field(default="GALAXY-", description="搜索模式")

class ValidateVersionsRequest(BaseModel):
    versions: List[str] = Field(..., description="要验证的版本列表")

# 依赖注入：获取服务实例
def get_version_service() -> VersionCompareService:
    """获取版本比较服务实例"""
    gitlab_url = os.getenv('GITLAB_URL')
    gitlab_token = os.getenv('GITLAB_TOKEN') 
    project_id = os.getenv('GITLAB_PROJECT_ID')
    
    if not all([gitlab_url, gitlab_token, project_id]):
        raise HTTPException(
            status_code=500, 
            detail="缺少必要的环境变量配置"
        )
    
    try:
        return VersionCompareService(gitlab_url, gitlab_token, project_id)
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"服务初始化失败: {str(e)}"
        )

@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "Version Compare Tool - Simplified Edition",
        "version": "2.0.0",
        "description": "基于GitLab Search API的高效版本比较服务",
        "features": [
            "GitLab Search API集成",
            "新功能分析",
            "功能丢失检测",
            "智能风险评估"
        ],
        "endpoints": {
            "analyze_new_features": "分析新版本带来的新内容",
            "detect_missing_tasks": "检测新版本丢失的功能",
            "analyze_tasks": "分析特定tasks详情",
            "search_tasks": "在版本中搜索tasks"
        }
    }

@app.get("/health")
async def health_check():
    """健康检查"""
    try:
        # 检查环境变量
        required_vars = ['GITLAB_URL', 'GITLAB_TOKEN', 'GITLAB_PROJECT_ID']
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            return {
                "status": "unhealthy",
                "error": f"缺少环境变量: {', '.join(missing_vars)}"
            }
        
        return {
            "status": "healthy",
            "version": "2.0.0",
            "api_method": "gitlab_search_api",
            "gitlab_url": os.getenv('GITLAB_URL'),
            "project_id": os.getenv('GITLAB_PROJECT_ID')
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@app.post("/analyze-new-features")
async def analyze_new_features(
    request: VersionUpgradeRequest,
    service: VersionCompareService = Depends(get_version_service)
) -> Dict[str, Any]:
    """
    分析新版本带来的新内容
    
    从旧版本升级到新版本时，新增了哪些tasks和功能。
    帮助了解升级后会获得什么新功能。
    """
    try:
        result = service.analyze_new_features(request.old_version, request.new_version)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/detect-missing-tasks")
async def detect_missing_tasks(
    request: VersionUpgradeRequest,
    service: VersionCompareService = Depends(get_version_service)
) -> Dict[str, Any]:
    """
    检测新版本丢失的功能
    
    从旧版本升级到新版本时，哪些tasks/功能可能丢失了。
    用于提醒防止盲目升级导致功能回退给用户造成困扰。
    包含风险评估和升级建议。
    """
    try:
        result = service.detect_missing_tasks(request.old_version, request.new_version)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze-tasks")
async def analyze_tasks(
    request: TaskAnalysisRequest,
    service: VersionCompareService = Depends(get_version_service)
) -> Dict[str, Any]:
    """分析特定tasks的详细信息"""
    try:
        result = service.analyze_specific_tasks(request.task_ids, request.branch_name)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search-tasks")
async def search_tasks(
    request: SearchTasksRequest,
    service: VersionCompareService = Depends(get_version_service)
) -> Dict[str, Any]:
    """在特定版本中搜索tasks"""
    try:
        result = service.search_tasks_in_version(request.version, request.task_pattern)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/validate-versions")
async def validate_versions(
    request: ValidateVersionsRequest,
    service: VersionCompareService = Depends(get_version_service)
) -> Dict[str, Any]:
    """验证版本是否存在"""
    try:
        result = service.validate_versions(request.versions)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/statistics/{from_version}/{to_version}")
async def get_statistics(
    from_version: str,
    to_version: str,
    service: VersionCompareService = Depends(get_version_service)
) -> Dict[str, Any]:
    """获取版本差异的统计信息"""
    try:
        result = service.get_task_statistics(from_version, to_version)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/cache/stats")
async def get_cache_stats(
    service: VersionCompareService = Depends(get_version_service)
) -> Dict[str, Any]:
    """获取缓存统计信息"""
    try:
        result = service.get_cache_statistics()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cache/clear")
async def clear_cache(
    service: VersionCompareService = Depends(get_version_service)
) -> Dict[str, Any]:
    """清理缓存"""
    try:
        result = service.clear_cache()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 开发环境启动
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 