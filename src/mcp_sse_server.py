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
from starlette.routing import Route
import uvicorn

from services.version_service import VersionComparisonService

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
        old_version = arguments.get("old_version")
        new_version = arguments.get("new_version") 
        
        if not old_version or not new_version:
            return [types.TextContent(
                type="text",
                text="错误: 缺少必需的参数 old_version 或 new_version"
            )]
        
        if name == "analyze-new-features":
            # 调用新增功能分析（同步方法）
            result = version_service.analyze_new_features(old_version, new_version)
            
            # 格式化结果为JSON字符串
            formatted_result = json.dumps(result, indent=2, ensure_ascii=False)
            
            return [types.TextContent(
                type="text",
                text=f"版本 {old_version} -> {new_version} 新增功能分析结果:\n\n{formatted_result}"
            )]
            
        elif name == "detect-missing-tasks":
            # 调用缺失任务检测（同步方法）
            result = version_service.detect_missing_tasks(old_version, new_version)
            
            # 格式化结果为JSON字符串
            formatted_result = json.dumps(result, indent=2, ensure_ascii=False)
            
            return [types.TextContent(
                type="text",
                text=f"版本 {old_version} -> {new_version} 缺失任务检测结果:\n\n{formatted_result}"
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
    sse_transport = SseServerTransport("/messages")
    
    # 创建Starlette应用
    app = Starlette(
        routes=[
            Route("/health", health_check),
            *sse_transport.routes
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
    logger.info(f"📡 MCP SSE端点: http://localhost:{port}/messages")
    
    # 在后台运行MCP服务器
    async def run_mcp_server():
        await server.run(
            sse_transport.read_stream,
            sse_transport.write_stream,
            InitializationOptions(
                server_name="version-compare-tool",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )
    
    # 启动MCP服务器任务
    mcp_task = asyncio.create_task(run_mcp_server())
    
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