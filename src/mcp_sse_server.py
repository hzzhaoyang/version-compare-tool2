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
            
            # 格式化结果为JSON字符串
            formatted_result = json.dumps(result, indent=2, ensure_ascii=False)
            
            project_info = f"项目: {version_service.current_project.name}"
            return [types.TextContent(
                type="text",
                text=f"{project_info}\n版本 {old_version} -> {new_version} 新增功能分析结果:\n\n{formatted_result}"
            )]
            
        elif name == "detect-missing-tasks":
            # 调用缺失任务检测（同步方法）
            result = version_service.detect_missing_tasks(old_version, new_version)
            
            # 格式化结果为JSON字符串
            formatted_result = json.dumps(result, indent=2, ensure_ascii=False)
            
            project_info = f"项目: {version_service.current_project.name}"
            return [types.TextContent(
                type="text",
                text=f"{project_info}\n版本 {old_version} -> {new_version} 缺失任务检测结果:\n\n{formatted_result}"
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
    port = int(os.getenv("MCP_PORT", "9999"))
    
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