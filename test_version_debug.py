#!/usr/bin/env python3
"""
调试版本获取问题的测试脚本
"""
import sys
import os
import requests
import json

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.gitlab.gitlab_manager import GitLabManager

def test_version_tags():
    """测试版本标签是否存在"""
    print("🔍 测试版本标签...")
    
    # 检查GitLab API直接访问
    gitlab_url = "https://gitlab.mayidata.com/"
    token = os.getenv('GITLAB_TOKEN')
    project_id = "130"
    
    if not token:
        print("❌ 请设置GITLAB_TOKEN环境变量")
        return
    
    headers = {'PRIVATE-TOKEN': token}
    
    # 测试1: 检查项目是否可访问
    print(f"\n📋 测试1: 检查项目 {project_id} 是否可访问...")
    try:
        project_url = f"{gitlab_url}/api/v4/projects/{project_id}"
        response = requests.get(project_url, headers=headers, timeout=10)
        if response.status_code == 200:
            project_info = response.json()
            print(f"✅ 项目访问成功: {project_info.get('name', 'Unknown')}")
        else:
            print(f"❌ 项目访问失败: HTTP {response.status_code}")
            return
    except Exception as e:
        print(f"❌ 项目访问异常: {e}")
        return
    
    # 测试2: 检查版本标签
    versions_to_check = ["6.6.0-ZSJJ-5", "7.1.0-hf37"]
    
    for version in versions_to_check:
        print(f"\n🏷️ 测试2: 检查版本标签 '{version}'...")
        
        # 检查标签是否存在
        tag_url = f"{gitlab_url}/api/v4/projects/{project_id}/repository/tags/{version}"
        try:
            response = requests.get(tag_url, headers=headers, timeout=10)
            if response.status_code == 200:
                tag_info = response.json()
                print(f"✅ 标签存在: {tag_info.get('name', 'Unknown')}")
                print(f"   提交ID: {tag_info.get('commit', {}).get('id', 'Unknown')[:8]}...")
                print(f"   提交时间: {tag_info.get('commit', {}).get('committed_date', 'Unknown')}")
            else:
                print(f"❌ 标签不存在: HTTP {response.status_code}")
                continue
        except Exception as e:
            print(f"❌ 标签检查异常: {e}")
            continue
        
        # 测试3: 检查该版本的commits数量
        print(f"   📊 检查该版本的commits数量...")
        commits_url = f"{gitlab_url}/api/v4/projects/{project_id}/repository/commits"
        params = {'ref_name': version, 'per_page': 1, 'page': 1}
        
        try:
            response = requests.get(commits_url, headers=headers, params=params, timeout=10)
            if response.status_code == 200:
                # 检查total header
                total_commits = response.headers.get('X-Total', 'Unknown')
                total_pages = response.headers.get('X-Total-Pages', 'Unknown')
                print(f"   📊 总commits: {total_commits}")
                print(f"   📊 总页数: {total_pages}")
                
                # 获取第一个commit
                commits = response.json()
                if commits:
                    first_commit = commits[0]
                    print(f"   📝 第一个commit: {first_commit.get('short_id', 'Unknown')}")
                    print(f"   📝 第一个commit消息: {first_commit.get('message', 'Unknown')[:50]}...")
                else:
                    print(f"   ⚠️ 没有找到commits")
            else:
                print(f"   ❌ 获取commits失败: HTTP {response.status_code}")
        except Exception as e:
            print(f"   ❌ 获取commits异常: {e}")

def test_gitlab_manager():
    """测试GitLabManager的实际获取情况"""
    print(f"\n🔧 测试GitLabManager的实际获取情况...")
    
    token = os.getenv('GITLAB_TOKEN')
    if not token:
        print("❌ 请设置GITLAB_TOKEN环境变量")
        return
    
    gitlab_manager = GitLabManager(
        gitlab_url="https://gitlab.mayidata.com/",
        token=token,
        project_id="130"
    )
    
    versions = ["6.6.0-ZSJJ-5", "7.1.0-hf37"]
    
    for version in versions:
        print(f"\n📥 使用GitLabManager获取版本 '{version}' 的commits...")
        
        try:
            commits = gitlab_manager.get_all_tag_commits_concurrent(version)
            print(f"✅ 获取成功: {len(commits)} 个commits")
            
            if commits:
                # 提取任务
                commit_task_map = gitlab_manager.extract_commit_messages_with_tasks(commits)
                tasks = set(commit_task_map.values())
                print(f"📊 提取任务数: {len(tasks)}")
                print(f"📊 commit-task映射数: {len(commit_task_map)}")
                
                # 显示前几个任务
                if tasks:
                    sample_tasks = sorted(list(tasks))[:5]
                    print(f"📋 前5个任务: {sample_tasks}")
                
                # 显示前几个commit消息
                sample_commits = list(commit_task_map.keys())[:3]
                print(f"📋 前3个commit消息:")
                for commit in sample_commits:
                    readable = commit.split('||')[1] if '||' in commit else commit
                    short_msg = readable[:50] + "..." if len(readable) > 50 else readable
                    print(f"   - {short_msg}")
            else:
                print(f"⚠️ 没有获取到任何commits")
                
        except Exception as e:
            print(f"❌ 获取失败: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    print("🚀 开始调试版本获取问题...")
    
    # 检查环境变量
    if not os.getenv('GITLAB_TOKEN'):
        print("❌ 请先设置GITLAB_TOKEN环境变量")
        print("   export GITLAB_TOKEN='your_gitlab_token'")
        sys.exit(1)
    
    try:
        # 测试版本标签
        test_version_tags()
        
        # 测试GitLabManager
        test_gitlab_manager()
        
        print(f"\n" + "="*80)
        print(f"✅ 调试测试完成！")
        
    except KeyboardInterrupt:
        print(f"\n👋 测试已取消")
    except Exception as e:
        print(f"\n❌ 测试过程中出错: {e}")
        import traceback
        traceback.print_exc() 