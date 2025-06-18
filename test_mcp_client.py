#!/usr/bin/env python3
"""
MCP客户端测试脚本
用于测试版本比较工具的MCP服务器
"""

import asyncio
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_mcp_tools():
    """测试MCP工具"""
    # 配置服务器参数
    server_params = StdioServerParameters(
        command="python3",
        args=["src/mcp_server.py"],
        env={
            "GITLAB_URL": os.getenv("GITLAB_URL", "https://gitlab.example.com"),
            "GITLAB_TOKEN": os.getenv("GITLAB_TOKEN", ""),
            "GITLAB_PROJECT_ID": os.getenv("GITLAB_PROJECT_ID", "")
        }
    )
    
    print("🚀 连接到MCP服务器...")
    
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            # 初始化连接
            print("🔗 初始化连接...")
            await session.initialize()
            
            # 列出可用工具
            print("📋 列出可用工具...")
            tools = await session.list_tools()
            print(f"发现 {len(tools.tools)} 个工具:")
            for tool in tools.tools:
                print(f"  - {tool.name}: {tool.description}")
            
            # 测试列出支持的项目
            print("\n🏢 测试列出支持的项目...")
            try:
                result = await session.call_tool(
                    "list-supported-projects",
                    arguments={}
                )
                print("✅ 项目列表获取结果:")
                for content in result.content:
                    if hasattr(content, 'text'):
                        print(content.text)
                    else:
                        print(content)
            except Exception as e:
                print(f"❌ 项目列表获取失败: {e}")
            
            # 测试分析新增功能
            print("\n🆕 测试分析新增功能...")
            try:
                result = await session.call_tool(
                    "analyze-new-features",
                    arguments={
                        "old_version": "6.6.0-ZSJJ-5",
                        "new_version": "7.1.0-hf37"
                    }
                )
                print("✅ 新增功能分析结果:")
                for content in result.content:
                    if hasattr(content, 'text'):
                        print(content.text)
                    else:
                        print(content)
                        
            except Exception as e:
                print(f"❌ 新增功能分析失败: {e}")
            
            # 测试检测缺失任务
            print("\n🔍 测试检测缺失任务...")
            try:
                result = await session.call_tool(
                    "detect-missing-tasks",
                    arguments={
                        "old_version": "6.6.0-ZSJJ-5",
                        "new_version": "7.1.0-hf37"
                    }
                )
                print("✅ 缺失任务检测结果:")
                for content in result.content:
                    if hasattr(content, 'text'):
                        print(content.text)
                    else:
                        print(content)
                        
            except Exception as e:
                print(f"❌ 缺失任务检测失败: {e}")


async def test_mcp_sse():
    """测试MCP SSE服务器"""
    import httpx
    
    print("🌐 测试MCP SSE服务器...")
    
    # 测试健康检查
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:3000/health")
            if response.status_code == 200:
                print("✅ SSE服务器健康检查通过")
                print(f"响应: {response.json()}")
            else:
                print(f"❌ SSE服务器健康检查失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 无法连接到SSE服务器: {e}")
        print("请先启动SSE服务器: python3 src/mcp_sse_server.py")


if __name__ == "__main__":
    print("🧪 版本比较工具MCP客户端测试")
    print("=" * 50)
    
    # 测试标准IO MCP服务器
    print("\n📡 测试标准IO MCP服务器")
    asyncio.run(test_mcp_tools())
    
    # 测试SSE MCP服务器
    print("\n🌐 测试SSE MCP服务器")
    asyncio.run(test_mcp_sse()) 