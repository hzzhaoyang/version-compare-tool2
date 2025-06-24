#!/usr/bin/env python3
"""
测试集成的 MCP 服务
"""
import requests
import json

def test_integrated_mcp():
    """测试集成在 Web API 中的 MCP 服务"""
    base_url = "http://localhost:9112"
    
    print("🔍 测试集成的 MCP 服务")
    print("=" * 50)
    
    # 1. 测试 MCP 健康检查
    try:
        print("1. 测试 MCP 健康检查...")
        response = requests.get(f"{base_url}/api/mcp/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ MCP 健康检查成功: {data}")
        else:
            print(f"❌ MCP 健康检查失败: {response.status_code}")
    except Exception as e:
        print(f"❌ MCP 健康检查异常: {e}")
    
    # 2. 测试 Web API 健康检查
    try:
        print("\n2. 测试 Web API 健康检查...")
        response = requests.get(f"{base_url}/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Web API 健康检查成功: {data}")
        else:
            print(f"❌ Web API 健康检查失败: {response.status_code}")
    except Exception as e:
        print(f"❌ Web API 健康检查异常: {e}")
    
    # 3. 测试 API 信息
    try:
        print("\n3. 测试 API 信息...")
        response = requests.get(f"{base_url}/api")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API 信息获取成功")
            print(f"📡 可用端点:")
            for endpoint, desc in data["endpoints"].items():
                print(f"   - {endpoint}: {desc}")
        else:
            print(f"❌ API 信息获取失败: {response.status_code}")
    except Exception as e:
        print(f"❌ API 信息获取异常: {e}")
    
    # 4. 测试前端页面
    try:
        print("\n4. 测试前端页面...")
        response = requests.get(f"{base_url}/version-compare")
        if response.status_code == 200:
            print(f"✅ 前端页面访问成功 (长度: {len(response.text)} 字符)")
        else:
            print(f"❌ 前端页面访问失败: {response.status_code}")
    except Exception as e:
        print(f"❌ 前端页面访问异常: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 集成测试完成！")
    print("📝 说明:")
    print("   - Web 界面: http://localhost:9112/version-compare")
    print("   - API 文档: http://localhost:9112/docs")
    print("   - MCP 健康检查: http://localhost:9112/api/mcp/health")
    print("   - MCP SSE 端点: http://localhost:9112/api/mcp/sse")

if __name__ == "__main__":
    test_integrated_mcp() 