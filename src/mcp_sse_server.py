#!/usr/bin/env python3
"""
版本比较工具的MCP SSE服务器实现
支持通过HTTP和Server-Sent Events进行通信
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.sse import SseServerTransport
from mcp import types
from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route, Mount
import uvicorn

import sys
import os
# 添加项目根目录到Python路径，以支持绝对导入
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# 加载环境变量
from dotenv import load_dotenv
load_dotenv()

from src.services.version_service import VersionComparisonService

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建MCP服务器实例
server = Server("version-compare-tool")

# 全局版本服务实例
version_service: Optional[VersionComparisonService] = None


def initialize_version_service():
    """初始化版本服务"""
    global version_service
    try:
        # 从环境变量获取配置
        gitlab_url = os.getenv("GITLAB_URL", "https://gitlab.example.com")
        gitlab_token = os.getenv("GITLAB_TOKEN", "")
        project_id = os.getenv("GITLAB_PROJECT_ID", "")
        
        if not gitlab_token or not project_id:
            logger.warning("GitLab配置缺失，使用默认配置")
            gitlab_token = "demo_token"
            project_id = "demo_project"
        
        # 创建版本服务实例
        version_service = VersionComparisonService()
        logger.info("版本服务初始化成功")
        
    except Exception as e:
        logger.error(f"版本服务初始化失败: {e}")
        # 创建一个模拟的版本服务用于演示
        version_service = VersionComparisonService()


@server.list_tools()
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


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: Dict[str, Any]
) -> List[types.TextContent]:
    """处理工具调用"""
    
    if not version_service:
        initialize_version_service()
    
    try:
        if name == "list-supported-projects":
            # 获取支持的项目列表
            projects = version_service.get_available_projects()
            current_project = version_service.current_project
            
            # 格式化项目信息
            project_info = {
                "current_project": {
                    "key": current_project.project_key,
                    "name": current_project.name,
                    "project_id": current_project.project_id
                },
                "all_projects": projects,
                "gitlab_url": version_service.gitlab_url
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
        
        # 如果指定了项目，切换到该项目
        if project_key and project_key != version_service.current_project.project_key:
            success = version_service.switch_project(project_key)
            if not success:
                return [types.TextContent(
                    type="text",
                    text=f"错误: 无法切换到项目 {project_key}，请检查项目配置"
                )]
        
        if name == "analyze-new-features":
            # 调用新增功能分析（同步方法）
            result = version_service.analyze_new_features(old_version, new_version)
            
            # 截断过大的响应
            truncated_result = truncate_large_response(result)
            
            # 格式化结果为JSON字符串
            formatted_result = json.dumps(truncated_result, indent=2, ensure_ascii=False)
            
            project_info = f"项目: {version_service.current_project.name}"
            
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
            # 调用缺失任务检测（同步方法）
            result = version_service.detect_missing_tasks(old_version, new_version)
            
            # 截断过大的响应
            truncated_result = truncate_large_response(result)
            
            # 格式化结果为JSON字符串
            formatted_result = json.dumps(truncated_result, indent=2, ensure_ascii=False)
            
            project_info = f"项目: {version_service.current_project.name}"
            
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
        logger.error(f"工具调用失败: {e}")
        return [types.TextContent(
            type="text",
            text=f"工具调用失败: {str(e)}"
        )]


async def health_check(request):
    """健康检查端点"""
    return JSONResponse({"status": "healthy", "service": "version-compare-mcp-sse"})


async def main():
    """主函数"""
    # 初始化版本服务
    initialize_version_service()
    
    # 获取端口配置
    port = int(os.getenv("MCP_PORT", "3000"))
    
    # 创建SSE传输
    sse_transport = SseServerTransport("/messages/")
    
    # SSE连接处理函数
    async def handle_sse(request):
        async with sse_transport.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await server.run(
                streams[0], streams[1], server.create_initialization_options()
            )
        # 返回一个空响应，因为SSE连接已经在上面处理完毕
        from starlette.responses import Response
        return Response()
    
    # 创建Starlette应用
    app = Starlette(
        routes=[
            Route("/health", health_check),
            Route("/sse", handle_sse),
            Mount("/messages/", sse_transport.handle_post_message)
        ]
    )
    
    # 添加CORS中间件
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    logger.info(f"🚀 启动MCP SSE服务器在端口 {port}")
    logger.info(f"🔗 健康检查: http://localhost:{port}/health")
    logger.info(f"📡 MCP SSE端点: http://localhost:{port}/sse")
    
    # 启动HTTP服务器
    config = uvicorn.Config(
        app=app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
    
    server_instance = uvicorn.Server(config)
    await server_instance.serve()


if __name__ == "__main__":
    asyncio.run(main()) 