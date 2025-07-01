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
from fastapi import FastAPI, HTTPException, Query, Path, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import json
import asyncio

# MCP 相关导入
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.sse import SseServerTransport
from mcp import types
from starlette.responses import JSONResponse

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

# 创建MCP服务器实例
mcp_server = Server("version-compare-tool")
sse_transport = SseServerTransport("/api/mcp/messages/")


@mcp_server.list_tools()
async def handle_list_tools() -> List[types.Tool]:
    """列出可用的工具"""
    return [
        types.Tool(
            name="list-supported-projects",
            description="列出所有支持的GitLab项目配置",
            inputSchema={
                "type": "object",
                "properties": {},
                "required": []
            }
        ),
        types.Tool(
            name="analyze-new-features",
            description="分析两个版本之间的新增功能和特性",
            inputSchema={
                "type": "object",
                "properties": {
                    "old_version": {
                        "type": "string",
                        "description": "旧版本号"
                    },
                    "new_version": {
                        "type": "string", 
                        "description": "新版本号"
                    },
                    "project": {
                        "type": "string",
                        "description": "项目key (可选，不指定则使用默认项目)",
                        "default": ""
                    }
                },
                "required": ["old_version", "new_version"]
            }
        ),
        types.Tool(
            name="detect-missing-tasks",
            description="检测两个版本之间缺失的任务和功能",
            inputSchema={
                "type": "object",
                "properties": {
                    "old_version": {
                        "type": "string",
                        "description": "旧版本号"
                    },
                    "new_version": {
                        "type": "string",
                        "description": "新版本号"
                    },
                    "project": {
                        "type": "string",
                        "description": "项目key (可选，不指定则使用默认项目)",
                        "default": ""
                    }
                },
                "required": ["old_version", "new_version"]
            }
        )
    ]


# 添加响应截断处理函数
def truncate_large_response(result: Dict[str, Any], max_chars: int = 130000) -> Dict[str, Any]:
    """
    截断过大的响应数据，避免超出LLM输入长度限制
    
    Args:
        result: 原始响应数据
        max_chars: 最大字符数限制（默认130,000字符，留出安全边界）
        
    Returns:
        截断后的响应数据，包含截断标记
    """
    # 先序列化检查长度
    full_json = json.dumps(result, ensure_ascii=False)
    
    if len(full_json) <= max_chars:
        # 未超出限制，直接返回
        result['_response_truncated'] = False
        result['_response_size'] = len(full_json)
        return result
    
    logger.warning(f"⚠️ 响应数据过大 ({len(full_json)} 字符)，开始激进截断处理...")
    
    # 创建精简的响应结构
    truncated_result = {
        '_response_truncated': True,
        '_original_size': len(full_json),
        '_truncation_info': {
            'reason': 'Response too large for LLM processing',
            'original_size': len(full_json),
            'max_allowed': max_chars,
            'truncated_fields': []
        }
    }
    
    # 保留基本信息
    basic_fields = ['analysis', 'total_time', 'old_commits_count', 'new_commits_count', 
                   'old_tasks_count', 'new_tasks_count', 'error']
    for field in basic_fields:
        if field in result:
            truncated_result[field] = result[field]
    
    # 激进截断 new_features 字段 - 只保留前10个
    if 'new_features' in result and isinstance(result['new_features'], list):
        original_count = len(result['new_features'])
        if original_count > 0:
            # 只保留前10个，并简化内容
            truncated_features = []
            for i, feature in enumerate(result['new_features'][:10]):
                # 截断每个feature的长度到200字符
                if isinstance(feature, str) and len(feature) > 200:
                    truncated_features.append(feature[:200] + "...")
                else:
                    truncated_features.append(feature)
            
            truncated_result['new_features'] = truncated_features
            truncated_result['_truncation_info']['truncated_fields'].append({
                'field': 'new_features',
                'original_count': original_count,
                'truncated_count': len(truncated_features),
                'message': f'新功能列表已截断：显示前{len(truncated_features)}项，共{original_count}项'
            })
    
    # 激进截断 missing_tasks 字段 - 只保留前10个
    if 'missing_tasks' in result and isinstance(result['missing_tasks'], list):
        original_count = len(result['missing_tasks'])
        if original_count > 0:
            truncated_result['missing_tasks'] = result['missing_tasks'][:10]
            truncated_result['_truncation_info']['truncated_fields'].append({
                'field': 'missing_tasks',
                'original_count': original_count,
                'truncated_count': min(10, original_count),
                'message': f'缺失任务列表已截断：显示前{min(10, original_count)}项，共{original_count}项'
            })
    
    # 极简化 detailed_analysis 字段
    if 'detailed_analysis' in result and isinstance(result['detailed_analysis'], dict):
        detailed = result['detailed_analysis']
        simple_analysis = {}
        
        # 只保留任务数量统计，不保留具体列表
        if 'completely_new_tasks' in detailed:
            simple_analysis['completely_new_tasks_count'] = len(detailed.get('completely_new_tasks', []))
            if simple_analysis['completely_new_tasks_count'] > 0:
                # 只保留前5个任务ID
                simple_analysis['completely_new_tasks_sample'] = list(detailed.get('completely_new_tasks', []))[:5]
        
        if 'partially_new_tasks' in detailed:
            simple_analysis['partially_new_tasks_count'] = len(detailed.get('partially_new_tasks', {}))
            if simple_analysis['partially_new_tasks_count'] > 0:
                # 只保留前3个任务的简化信息
                sample_tasks = {}
                for i, (task_id, commits) in enumerate(detailed.get('partially_new_tasks', {}).items()):
                    if i >= 3:
                        break
                    # 只保留任务ID和commit数量
                    sample_tasks[task_id] = f"{len(commits)} commits"
                simple_analysis['partially_new_tasks_sample'] = sample_tasks
        
        if 'completely_missing_tasks' in detailed:
            simple_analysis['completely_missing_tasks_count'] = len(detailed.get('completely_missing_tasks', []))
            if simple_analysis['completely_missing_tasks_count'] > 0:
                simple_analysis['completely_missing_tasks_sample'] = list(detailed.get('completely_missing_tasks', []))[:5]
        
        if 'partially_missing_tasks' in detailed:
            simple_analysis['partially_missing_tasks_count'] = len(detailed.get('partially_missing_tasks', {}))
            if simple_analysis['partially_missing_tasks_count'] > 0:
                sample_tasks = {}
                for i, (task_id, commits) in enumerate(detailed.get('partially_missing_tasks', {}).items()):
                    if i >= 3:
                        break
                    sample_tasks[task_id] = f"{len(commits)} commits"
                simple_analysis['partially_missing_tasks_sample'] = sample_tasks
        
        if 'new_commit_count' in detailed:
            simple_analysis['new_commit_count'] = detailed['new_commit_count']
        if 'missing_commit_count' in detailed:
            simple_analysis['missing_commit_count'] = detailed['missing_commit_count']
        
        truncated_result['detailed_analysis'] = simple_analysis
        truncated_result['_truncation_info']['truncated_fields'].append({
            'field': 'detailed_analysis',
            'message': '详细分析已简化：只保留统计数据和少量样本'
        })
    
    # 简化 service_stats - 只保留关键性能指标
    if 'service_stats' in result:
        stats = result.get('service_stats', {})
        truncated_result['service_stats'] = {
            'total_time': stats.get('total_time', 0),
            'commits_processed': stats.get('commits_processed', 0),
            'performance_improvement': stats.get('performance_improvement', 'N/A')
        }
    
    # 检查截断后的大小，如果还是太大，进一步缩减
    truncated_json = json.dumps(truncated_result, ensure_ascii=False)
    if len(truncated_json) > max_chars:
        logger.warning(f"⚠️ 第一次截断后仍然过大 ({len(truncated_json)} 字符)，进行二次截断...")
        
        # 进一步缩减 new_features 到前5个
        if 'new_features' in truncated_result:
            original_count = len(truncated_result['new_features'])
            truncated_result['new_features'] = truncated_result['new_features'][:5]
            # 更新截断信息
            for field_info in truncated_result['_truncation_info']['truncated_fields']:
                if field_info['field'] == 'new_features':
                    field_info['truncated_count'] = min(5, original_count)
                    field_info['message'] = f'新功能列表已截断：显示前{min(5, original_count)}项，共{field_info["original_count"]}项'
        
        # 进一步缩减 missing_tasks 到前5个
        if 'missing_tasks' in truncated_result:
            original_count = len(truncated_result['missing_tasks'])
            truncated_result['missing_tasks'] = truncated_result['missing_tasks'][:5]
            # 更新截断信息
            for field_info in truncated_result['_truncation_info']['truncated_fields']:
                if field_info['field'] == 'missing_tasks':
                    field_info['truncated_count'] = min(5, original_count)
                    field_info['message'] = f'缺失任务列表已截断：显示前{min(5, original_count)}项，共{field_info["original_count"]}项'
        
        # 进一步简化 detailed_analysis
        if 'detailed_analysis' in truncated_result:
            analysis = truncated_result['detailed_analysis']
            # 只保留计数，移除样本
            simplified_analysis = {}
            for key, value in analysis.items():
                if key.endswith('_count'):
                    simplified_analysis[key] = value
            truncated_result['detailed_analysis'] = simplified_analysis
        
        # 移除非关键字段
        non_essential_fields = ['service_stats']
        for field in non_essential_fields:
            if field in truncated_result:
                del truncated_result[field]
                truncated_result['_truncation_info']['truncated_fields'].append({
                    'field': field,
                    'message': f'{field} 字段已移除以减少响应大小'
                })
    
    # 最终检查
    final_json = json.dumps(truncated_result, ensure_ascii=False)
    truncated_result['_response_size'] = len(final_json)
    
    logger.info(f"✅ 激进截断完成：{len(full_json)} -> {len(final_json)} 字符 ({len(truncated_result['_truncation_info']['truncated_fields'])} 个字段被处理)")
    
    return truncated_result


@mcp_server.call_tool()
async def handle_call_tool(
    name: str, arguments: Dict[str, Any]
) -> List[types.TextContent]:
    """处理工具调用"""
    
    try:
        if name == "list-supported-projects":
            # 使用项目配置管理器获取支持的项目列表
            from src.services.version_service import ProjectConfigManager
            config_manager = ProjectConfigManager()
            projects = config_manager.get_all_projects()
            current_project_key = config_manager.get_current_project_key()
            
            # 找到当前项目信息
            current_project_info = next(
                (p for p in projects if p['key'] == current_project_key), 
                projects[0] if projects else None
            )
            
            # 格式化项目信息
            project_info = {
                "current_project": {
                    "key": current_project_info['key'],
                    "name_zh": current_project_info['name_zh'],
                    "name_en": current_project_info['name_en'],
                    "project_id": current_project_info['project_id']
                } if current_project_info else None,
                "all_projects": projects,
                "total_projects": len(projects)
            }
            
            formatted_result = json.dumps(project_info, indent=2, ensure_ascii=False)
            
            return [types.TextContent(
                type="text",
                text=f"支持的GitLab项目配置:\n\n{formatted_result}"
            )]
        
        # 处理需要版本参数的工具
        old_version = arguments.get("old_version")
        new_version = arguments.get("new_version")
        project_key = arguments.get("project", "")
        
        if not old_version or not new_version:
            return [types.TextContent(
                type="text",
                text="错误: 缺少必需的参数 old_version 或 new_version"
            )]
        
        # 获取版本服务实例
        service = get_version_service(project_key if project_key else None)
        
        if name == "analyze-new-features":
            # 调用新增功能分析
            result = service.analyze_new_features(old_version, new_version)
            
            # 截断过大的响应
            truncated_result = truncate_large_response(result)
            
            # 格式化结果为JSON字符串
            formatted_result = json.dumps(truncated_result, indent=2, ensure_ascii=False)
            
            project_info = f"项目: {service.current_project.name_zh} ({service.current_project.name_en})"
            
            # 添加截断提示信息
            truncation_notice = ""
            if truncated_result.get('_response_truncated', False):
                truncation_info = truncated_result.get('_truncation_info', {})
                truncated_fields = truncation_info.get('truncated_fields', [])
                
                if truncated_fields:
                    notices = []
                    for field_info in truncated_fields:
                        notices.append(f"• {field_info['message']}")
                    
                    truncation_notice = f"\n\n⚠️ **响应数据已截断** (原始大小: {truncation_info['original_size']} 字符):\n" + "\n".join(notices)
                    truncation_notice += f"\n\n💡 **提示**: 完整数据可通过Web界面查看，或使用更具体的查询条件。"
            
            return [types.TextContent(
                type="text",
                text=f"{project_info}\n版本 {old_version} -> {new_version} 新增功能分析结果:\n\n{formatted_result}{truncation_notice}"
            )]
            
        elif name == "detect-missing-tasks":
            # 调用缺失任务检测
            result = service.detect_missing_tasks(old_version, new_version)
            
            # 截断过大的响应
            truncated_result = truncate_large_response(result)
            
            # 格式化结果为JSON字符串
            formatted_result = json.dumps(truncated_result, indent=2, ensure_ascii=False)
            
            project_info = f"项目: {service.current_project.name_zh} ({service.current_project.name_en})"
            
            # 添加截断提示信息
            truncation_notice = ""
            if truncated_result.get('_response_truncated', False):
                truncation_info = truncated_result.get('_truncation_info', {})
                truncated_fields = truncation_info.get('truncated_fields', [])
                
                if truncated_fields:
                    notices = []
                    for field_info in truncated_fields:
                        notices.append(f"• {field_info['message']}")
                    
                    truncation_notice = f"\n\n⚠️ **响应数据已截断** (原始大小: {truncation_info['original_size']} 字符):\n" + "\n".join(notices)
                    truncation_notice += f"\n\n💡 **提示**: 完整数据可通过Web界面查看，或使用更具体的查询条件。"
            
            return [types.TextContent(
                type="text",
                text=f"{project_info}\n版本 {old_version} -> {new_version} 缺失任务检测结果:\n\n{formatted_result}{truncation_notice}"
            )]
            
        else:
            return [types.TextContent(
                type="text",
                text=f"未知工具: {name}"
            )]
            
    except Exception as e:
        logger.error(f"MCP工具调用失败: {e}")
        return [types.TextContent(
            type="text",
            text=f"工具调用失败: {str(e)}"
        )]


def create_project_info(project_config) -> Dict[str, str]:
    """创建项目信息字典，包含中英文名称"""
    return {
        'key': project_config.project_key,
        'name_zh': project_config.name_zh,
        'name_en': project_config.name_en,
        'project_id': project_config.project_id
    }


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
            "GET /statistics/{from_version}/{to_version}": "获取统计信息",
            "GET /api/mcp/health": "MCP健康检查",
            "GET /api/mcp/sse": "MCP SSE连接端点",
            "POST /api/mcp/messages/": "MCP消息处理端点"
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
        # 使用项目配置管理器获取所有项目（包括未配置的项目）
        from src.services.version_service import ProjectConfigManager
        config_manager = ProjectConfigManager()
        projects = config_manager.get_all_projects()
        current_project_key = config_manager.get_current_project_key()
        
        # 添加当前选中的项目标识
        for project in projects:
            project['is_current'] = project['key'] == current_project_key
        
        return {
            "projects": projects,
            "current_project": current_project_key
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
            "current_project": f"{service.current_project.name_zh} ({service.current_project.name_en})",
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
                project_info=create_project_info(service.current_project)
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
            project_info=create_project_info(service.current_project)
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
                'name_zh': '未知项目',
                'name_en': 'Unknown Project',
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
                project_info=create_project_info(service.current_project)
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
            project_info=create_project_info(service.current_project)
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
                'name_zh': '未知项目',
                'name_en': 'Unknown Project',
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
        result['project_info'] = create_project_info(service.current_project)
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
        result['project_info'] = create_project_info(service.current_project)
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
        result['project_info'] = create_project_info(service.current_project)
        return result
        
    except Exception as e:
        api_time = time.time() - api_start_time
        error_msg = f"验证版本失败: {str(e)}"
        logger.error(f"❌ {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)


@app.get("/api/mcp/health")
async def mcp_health_check():
    """MCP健康检查端点"""
    return JSONResponse({"status": "healthy", "service": "version-compare-mcp-integrated"})


@app.get("/api/mcp/sse")
async def handle_mcp_sse(request: Request):
    """MCP SSE连接处理函数"""
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp_server.run(
            streams[0], streams[1], mcp_server.create_initialization_options()
        )
    # 返回一个空响应，因为SSE连接已经在上面处理完毕
    from starlette.responses import Response
    return Response()


# 挂载MCP消息处理端点
app.mount("/api/mcp/messages/", sse_transport.handle_post_message)


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
        result['project_info'] = create_project_info(service.current_project)
        return result
        
    except Exception as e:
        api_time = time.time() - api_start_time
        error_msg = f"获取统计信息失败: {str(e)}"
        logger.error(f"❌ {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 9112))) 