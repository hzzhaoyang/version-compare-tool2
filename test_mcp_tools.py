#!/usr/bin/env python3
"""
测试 MCP 工具功能
"""
import requests
import json

def test_mcp_projects():
    """测试 MCP 项目列表工具"""
    print("🔍 测试 MCP 项目列表工具")
    
    # 模拟 MCP 消息
    mcp_message = {
        "method": "tools/call",
        "params": {
            "name": "list-supported-projects",
            "arguments": {}
        }
    }
    
    try:
        response = requests.post(
            "http://localhost:9112/api/mcp/messages/",
            json=mcp_message,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print("✅ MCP 项目列表工具调用成功")
            result = response.json()
            print(f"📋 响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
        else:
            print(f"❌ MCP 项目列表工具调用失败: {response.status_code}")
            print(f"错误信息: {response.text}")
    except Exception as e:
        print(f"❌ MCP 项目列表工具调用异常: {e}")

def test_mcp_version_analysis():
    """测试 MCP 版本分析工具"""
    print("\n🔍 测试 MCP 版本分析工具")
    
    # 模拟 MCP 消息 - 分析新增功能
    mcp_message = {
        "method": "tools/call", 
        "params": {
            "name": "analyze-new-features",
            "arguments": {
                "old_version": "7.0.0-hf20",
                "new_version": "7.1.0-hf37"
            }
        }
    }
    
    try:
        print("测试 analyze-new-features 工具...")
        response = requests.post(
            "http://localhost:9112/api/mcp/messages/",
            json=mcp_message,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            print("✅ MCP 新增功能分析工具调用成功")
            result = response.json()
            print(f"📋 响应摘要: 获得 {len(str(result))} 字符的响应")
        else:
            print(f"❌ MCP 新增功能分析工具调用失败: {response.status_code}")
            print(f"错误信息: {response.text}")
    except Exception as e:
        print(f"❌ MCP 新增功能分析工具调用异常: {e}")

def main():
    """主测试函数"""
    print("🚀 开始测试 MCP 工具功能")
    print("=" * 50)
    
    # 1. 测试项目列表工具
    test_mcp_projects()
    
    # 2. 测试版本分析工具（这个可能需要很长时间，先跳过）
    # test_mcp_version_analysis()
    
    print("\n" + "=" * 50)
    print("🎉 MCP 工具测试完成！")
    print("💡 注意：版本分析工具测试需要较长时间，已跳过")

if __name__ == "__main__":
    main() 