#!/usr/bin/env python3
"""
测试新的API接口
验证分析新功能和检测丢失任务的功能
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_health():
    """测试健康检查"""
    print("🏥 测试健康检查...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"状态: {response.status_code}")
    print(f"响应: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    print("-" * 50)

def test_analyze_new_features():
    """测试分析新功能接口"""
    print("🆕 测试分析新功能...")
    
    # 测试从旧版本到新版本的新增内容
    data = {
        "old_version": "6.6.0-ZSJJ-5",
        "new_version": "7.1.0-hf37"
    }
    
    print(f"请求: {json.dumps(data, ensure_ascii=False)}")
    start_time = time.time()
    
    response = requests.post(f"{BASE_URL}/analyze-new-features", json=data)
    
    print(f"状态: {response.status_code}")
    print(f"耗时: {time.time() - start_time:.2f}s")
    
    if response.status_code == 200:
        result = response.json()
        print(f"新增tasks数量: {len(result.get('new_tasks', []))}")
        print(f"新增commits数量: {result.get('total_new_commits', 0)}")
        print(f"处理时间: {result.get('processing_time', 0):.2f}s")
        
        # 显示前几个新增的tasks
        new_tasks = result.get('new_tasks', [])
        if new_tasks:
            print(f"前5个新增tasks: {new_tasks[:5]}")
        
        # 显示commit统计
        commit_stats = result.get('commit_statistics', {})
        if commit_stats:
            print(f"Commit类型分布: {commit_stats.get('commit_types', {})}")
    else:
        print(f"错误: {response.text}")
    
    print("-" * 50)

def test_detect_missing_tasks():
    """测试检测丢失任务接口"""
    print("⚠️ 测试检测丢失任务...")
    
    # 测试从旧版本升级到新版本可能丢失的功能
    data = {
        "old_version": "6.6.0-ZSJJ-5",
        "new_version": "7.1.0-hf37"
    }
    
    print(f"请求: {json.dumps(data, ensure_ascii=False)}")
    start_time = time.time()
    
    response = requests.post(f"{BASE_URL}/detect-missing-tasks", json=data)
    
    print(f"状态: {response.status_code}")
    print(f"耗时: {time.time() - start_time:.2f}s")
    
    if response.status_code == 200:
        result = response.json()
        print(f"丢失tasks数量: {len(result.get('missing_tasks', []))}")
        print(f"仍存在tasks数量: {len(result.get('existing_tasks', []))}")
        print(f"风险等级: {result.get('risk_level', 'unknown')}")
        print(f"处理时间: {result.get('processing_time', 0):.2f}s")
        
        # 显示丢失的tasks
        missing_tasks = result.get('missing_tasks', [])
        if missing_tasks:
            print(f"丢失的tasks: {missing_tasks}")
        else:
            print("✅ 未发现丢失的tasks")
        
        # 显示风险评估
        risk_assessment = result.get('risk_assessment', {})
        if risk_assessment:
            print(f"风险评估: {risk_assessment.get('message', '')}")
            print(f"建议: {risk_assessment.get('recommendation', '')}")
    else:
        print(f"错误: {response.text}")
    
    print("-" * 50)

def test_specific_task_search():
    """测试特定任务搜索"""
    print("🔍 测试特定任务搜索...")
    
    # 搜索GALAXY-24672在两个版本中的存在情况
    versions_to_test = ["6.6.0-ZSJJ-5", "7.1.0-hf37"]
    
    for version in versions_to_test:
        print(f"\n在版本 {version} 中搜索 GALAXY-24672:")
        
        data = {
            "task_ids": ["GALAXY-24672"],
            "branch_name": version
        }
        
        response = requests.post(f"{BASE_URL}/analyze-tasks", json=data)
        
        if response.status_code == 200:
            result = response.json()
            found_count = result.get('found_tasks', 0)
            missing_count = result.get('missing_tasks', 0)
            
            print(f"  找到: {found_count}, 缺失: {missing_count}")
            
            task_details = result.get('task_details', {})
            if 'GALAXY-24672' in task_details:
                detail = task_details['GALAXY-24672']
                if detail.get('status') == 'not_found':
                    print(f"  ❌ GALAXY-24672 在 {version} 中未找到")
                else:
                    print(f"  ✅ GALAXY-24672 在 {version} 中找到")
        else:
            print(f"  错误: {response.text}")
    
    print("-" * 50)

def main():
    """主测试函数"""
    print("🧪 开始测试新的API接口")
    print("=" * 50)
    
    try:
        # 1. 健康检查
        test_health()
        
        # 2. 测试分析新功能
        test_analyze_new_features()
        
        # 3. 测试检测丢失任务
        test_detect_missing_tasks()
        
        # 4. 测试特定任务搜索
        test_specific_task_search()
        
        print("✅ 所有测试完成")
        
    except requests.exceptions.ConnectionError:
        print("❌ 无法连接到服务，请确保服务正在运行在 http://localhost:8000")
    except Exception as e:
        print(f"❌ 测试失败: {e}")

if __name__ == "__main__":
    main() 