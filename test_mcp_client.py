#!/usr/bin/env python3
"""
版本比较工具MCP测试脚本 (已废弃)
⚠️ 注意：独立的MCP服务器已集成到Web API中，请使用 test_integrated_mcp.py 进行测试
"""

import asyncio
import os


async def test_legacy_mcp():
    """提示用户使用新的测试方式"""
    print("⚠️ 独立MCP服务器已废弃")
    print("🔄 MCP功能已集成到统一的Web API服务中")
    print("")
    print("📌 新的测试方式:")
    print("   1. 启动服务: python3 run.py")
    print("   2. 运行测试: python3 test_integrated_mcp.py")
    print("")
    print("🌐 或直接访问Web界面: http://localhost:9112/version-compare")
    print("📖 API文档: http://localhost:9112/docs")
    print("🔗 MCP健康检查: http://localhost:9112/api/mcp/health")


async def test_integrated_mcp():
    """测试集成的MCP服务器"""
    import httpx
    
    print("🌐 测试集成的MCP服务器...")
    
    # 测试健康检查
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:9112/api/mcp/health")
            if response.status_code == 200:
                print("✅ 集成MCP服务器健康检查通过")
                print(f"响应: {response.json()}")
                
                # 测试Web API
                print("\n🌐 测试Web API...")
                api_response = await client.get("http://localhost:9112/health")
                if api_response.status_code == 200:
                    print("✅ Web API健康检查通过")
                    print(f"响应: {api_response.json()}")
                
            else:
                print(f"❌ 集成MCP服务器健康检查失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 无法连接到集成服务器: {e}")
        print("请先启动服务: python3 run.py")


if __name__ == "__main__":
    print("🧪 版本比较工具MCP测试 (已更新)")
    print("=" * 50)
    
    # 显示架构变更信息
    print("\n📢 架构更新说明")
    asyncio.run(test_legacy_mcp())
    
    # 测试集成的MCP服务器
    print("\n🔍 测试集成服务器")
    asyncio.run(test_integrated_mcp()) 