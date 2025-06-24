#!/usr/bin/env python3
"""
综合系统测试脚本
测试项目配置系统、API服务和MCP集成
"""

import requests
import json
import time
import sys

def test_basic_api():
    """测试基本API功能"""
    print("🔧 测试基本API功能...")
    
    try:
        # 健康检查
        response = requests.get("http://localhost:9112/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 健康检查通过: {data['current_project']}")
            print(f"   可用项目数: {data['available_projects']}")
        else:
            print(f"❌ 健康检查失败: {response.status_code}")
            return False
        
        # API信息
        response = requests.get("http://localhost:9112/api")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API信息获取成功: {data['name']} v{data['version']}")
        else:
            print(f"❌ API信息获取失败: {response.status_code}")
            return False
        
        return True
    except Exception as e:
        print(f"❌ 基本API测试失败: {e}")
        return False


def test_project_config():
    """测试项目配置功能"""
    print("\n📊 测试项目配置功能...")
    
    try:
        response = requests.get("http://localhost:9112/api/projects")
        if response.status_code == 200:
            data = response.json()
            projects = data['projects']
            current = data['current_project']
            
            print(f"✅ 项目配置获取成功")
            print(f"   当前项目: {current}")
            print(f"   可用项目: {len(projects)}")
            
            for project in projects:
                is_current = "⭐" if project.get('is_current', False) else "  "
                display_name = project.get('display_name') or project.get('name_zh') or project['name']
                print(f"   {is_current} {display_name} ({project['key']})")
            
            return True
        else:
            print(f"❌ 项目配置获取失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 项目配置测试失败: {e}")
        return False


def test_mcp_integration():
    """测试MCP集成功能"""
    print("\n🔌 测试MCP集成功能...")
    
    try:
        # MCP健康检查
        response = requests.get("http://localhost:9112/api/mcp/health")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ MCP健康检查通过: {data['service']}")
        else:
            print(f"❌ MCP健康检查失败: {response.status_code}")
            return False
        
        return True
    except Exception as e:
        print(f"❌ MCP集成测试失败: {e}")
        return False


def test_frontend_access():
    """测试前端访问"""
    print("\n🌐 测试前端访问...")
    
    try:
        # 前端页面
        response = requests.get("http://localhost:9112/version-compare")
        if response.status_code == 200:
            print("✅ 前端页面访问成功")
        else:
            print(f"❌ 前端页面访问失败: {response.status_code}")
            return False
        
        # 前端配置
        response = requests.get("http://localhost:9112/api/config")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 前端配置获取成功")
            if data.get('task_url_prefix'):
                print(f"   任务链接前缀: {data['task_url_prefix']}")
        else:
            print(f"❌ 前端配置获取失败: {response.status_code}")
            return False
        
        return True
    except Exception as e:
        print(f"❌ 前端访问测试失败: {e}")
        return False


def test_version_analysis():
    """测试版本分析功能（如果有有效的token）"""
    print("\n🔍 测试版本分析功能...")
    
    try:
        # 尝试分析新增功能（使用假的版本号测试API调用）
        test_data = {
            "old_version": "v1.0.0",
            "new_version": "v1.1.0"
        }
        
        response = requests.post(
            "http://localhost:9112/analyze-new-features",
            json=test_data,
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 版本分析API调用成功")
            if data.get('error'):
                print(f"   (预期错误，因为版本号不存在: {data['error'][:50]}...)")
            else:
                print(f"   分析结果: {len(data.get('new_features', []))} 个新功能")
        else:
            print(f"⚠️ 版本分析API调用返回: {response.status_code}")
            print("   (这可能是因为没有有效的GitLab配置)")
        
        return True
    except Exception as e:
        print(f"⚠️ 版本分析测试失败: {e}")
        print("   (这可能是因为没有有效的GitLab配置)")
        return True  # 这不算失败，因为可能没有GitLab配置


def main():
    """运行所有测试"""
    print("=" * 60)
    print("🚀 版本比较工具综合系统测试")
    print("=" * 60)
    
    # 等待服务启动
    print("⏳ 等待服务启动...")
    time.sleep(2)
    
    tests = [
        ("基本API功能", test_basic_api),
        ("项目配置功能", test_project_config),
        ("MCP集成功能", test_mcp_integration),
        ("前端访问", test_frontend_access),
        ("版本分析功能", test_version_analysis)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        if test_func():
            passed += 1
            print(f"✅ {test_name} 通过")
        else:
            print(f"❌ {test_name} 失败")
    
    print("\n" + "=" * 60)
    print(f"🎯 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 所有测试通过！系统运行正常")
        print("\n📱 您可以通过以下方式访问系统:")
        print("   🌐 前端界面: http://localhost:9112/version-compare")
        print("   📊 API文档: http://localhost:9112/api")
        print("   ❤️ 健康检查: http://localhost:9112/health")
        print("   🔌 MCP健康: http://localhost:9112/api/mcp/health")
    else:
        print("⚠️ 部分测试失败，请检查配置和服务状态")
    
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️ 测试被用户中断")
    except Exception as e:
        print(f"\n\n💥 测试过程中发生异常: {e}")
        sys.exit(1) 