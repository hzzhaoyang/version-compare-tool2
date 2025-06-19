#!/usr/bin/env python3
"""
分析partially_missing_tasks变成completely_missing_tasks的逻辑问题
模拟数据测试版本
"""
import sys
import os
from typing import Dict, Any, Set, List

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def simulate_task_classification_logic():
    """模拟任务分类逻辑分析"""
    print("🔍 模拟分析任务分类逻辑问题")
    print("="*80)
    
    # 模拟旧版本的commits和tasks
    print("📊 模拟数据设置:")
    
    # 模拟旧版本的commit-task映射
    old_commit_task_map = {
        "GALAXY-12345||GALAXY-12345 修复用户登录问题": "GALAXY-12345",
        "GALAXY-12345||GALAXY-12345 增加单元测试": "GALAXY-12345",
        "GALAXY-12345||GALAXY-12345 修复代码格式问题": "GALAXY-12345",
        "GALAXY-23456||GALAXY-23456 新增报表功能": "GALAXY-23456",
        "GALAXY-23456||GALAXY-23456 修复报表样式": "GALAXY-23456",
        "GALAXY-34567||GALAXY-34567 优化数据库查询": "GALAXY-34567",
        "GALAXY-45678||GALAXY-45678 修复API接口问题": "GALAXY-45678",
        "GALAXY-45678||GALAXY-45678 增加API文档": "GALAXY-45678",
        "GALAXY-45678||GALAXY-45678 修复API性能问题": "GALAXY-45678",
    }
    
    # 模拟新版本的commit-task映射 - 某些任务完全缺失，某些任务部分缺失
    new_commit_task_map = {
        # GALAXY-12345 部分缺失 - 缺少"修复代码格式问题"这个commit
        "GALAXY-12345||GALAXY-12345 修复用户登录问题": "GALAXY-12345",
        "GALAXY-12345||GALAXY-12345 增加单元测试": "GALAXY-12345",
        
        # GALAXY-23456 部分缺失 - 缺少"修复报表样式"这个commit
        "GALAXY-23456||GALAXY-23456 新增报表功能": "GALAXY-23456",
        
        # GALAXY-34567 完全缺失 - 新版本完全没有这个任务
        
        # GALAXY-45678 完全保留 - 所有commits都在
        "GALAXY-45678||GALAXY-45678 修复API接口问题": "GALAXY-45678",
        "GALAXY-45678||GALAXY-45678 增加API文档": "GALAXY-45678",
        "GALAXY-45678||GALAXY-45678 修复API性能问题": "GALAXY-45678",
        
        # 新增任务
        "GALAXY-56789||GALAXY-56789 新增AI功能": "GALAXY-56789",
    }
    
    print(f"  旧版本commits: {len(old_commit_task_map)}")
    print(f"  新版本commits: {len(new_commit_task_map)}")
    
    # 提取任务集合
    old_tasks = set(old_commit_task_map.values())
    new_tasks = set(new_commit_task_map.values())
    
    print(f"  旧版本tasks: {len(old_tasks)} = {sorted(old_tasks)}")
    print(f"  新版本tasks: {len(new_tasks)} = {sorted(new_tasks)}")
    
    # 执行分类逻辑（复制自TaskLossDetector的逻辑）
    print(f"\n🧮 执行任务分类逻辑:")
    
    # 找出旧版本有但新版本没有的commit messages
    old_messages = set(old_commit_task_map.keys())
    new_messages = set(new_commit_task_map.keys())
    missing_messages = old_messages - new_messages
    
    print(f"  缺失的commit messages: {len(missing_messages)}")
    for msg in sorted(missing_messages):
        readable = msg.split('||')[1] if '||' in msg else msg
        print(f"    - {readable}")
    
    # 从缺失的commit messages中提取对应的task IDs
    missing_commit_tasks = {}  # {task_id: [missing_commit_messages]}
    for msg in missing_messages:
        task_id = old_commit_task_map[msg]
        if task_id not in missing_commit_tasks:
            missing_commit_tasks[task_id] = []
        missing_commit_tasks[task_id].append(msg)
    
    print(f"\n  缺失commits按任务分组:")
    for task_id, commits in missing_commit_tasks.items():
        print(f"    {task_id}: {len(commits)} 个commits")
        for commit in commits:
            readable = commit.split('||')[1] if '||' in commit else commit
            print(f"      - {readable}")
    
    # 分类分析缺失情况
    completely_missing_tasks = set()  # 完全缺失的tasks
    partially_missing_tasks = {}     # 部分缺失的tasks
    
    for task_id, missing_commits in missing_commit_tasks.items():
        if task_id not in new_tasks:
            # 新版本完全没有这个task
            completely_missing_tasks.add(task_id)
            print(f"    ✅ {task_id} -> 完全缺失 (新版本完全没有)")
        else:
            # 新版本有这个task，但缺少某些commits
            partially_missing_tasks[task_id] = missing_commits
            print(f"    ✅ {task_id} -> 部分缺失 (新版本有但缺少某些commits)")
    
    print(f"\n🎯 分类结果:")
    print(f"  完全缺失任务: {len(completely_missing_tasks)} = {sorted(completely_missing_tasks)}")
    print(f"  部分缺失任务: {len(partially_missing_tasks)} = {sorted(partially_missing_tasks.keys())}")
    
    # 分析为什么可能出现所有任务都是完全缺失的情况
    print(f"\n🔍 问题分析:")
    print(f"  如果实际运行中所有任务都被归类为完全缺失，可能原因:")
    print(f"  1. 新版本的任务集合为空或获取失败")
    print(f"  2. 新版本的commits获取失败或格式不正确")
    print(f"  3. 任务ID提取正则表达式不匹配")
    print(f"  4. 版本标签指向了错误的commits")
    
    return {
        'old_tasks': old_tasks,
        'new_tasks': new_tasks,
        'completely_missing_tasks': completely_missing_tasks,
        'partially_missing_tasks': partially_missing_tasks,
        'missing_commit_tasks': missing_commit_tasks
    }

def analyze_current_issue():
    """分析当前问题"""
    print(f"\n🔍 分析当前的问题:")
    print(f"  根据你提供的数据:")
    print(f"  - 旧版本commits: 100")
    print(f"  - 新版本commits: 1 (这很可能是问题所在!)")
    print(f"  - 旧版本tasks: 57")
    print(f"  - 新版本tasks: 92")
    print(f"  - 缺失tasks: 52")
    print(f"")
    print(f"  🚨 关键问题: 新版本只有1个commit但有92个tasks！")
    print(f"  这说明:")
    print(f"  1. 新版本的commits获取失败，只获取到1个commit")
    print(f"  2. 但从这1个commit中提取出了92个tasks (可能是错误的)")
    print(f"  3. 由于新版本的commits获取不完整，导致:")
    print(f"     - 很多任务在新版本中看起来'完全不存在'")
    print(f"     - 实际上这些任务可能在新版本中存在，只是commits没有被获取到")
    print(f"")
    print(f"  🎯 解决方案:")
    print(f"  1. 检查新版本标签 '7.1.0-hf37' 是否存在")
    print(f"  2. 检查GitLab API请求是否正常")
    print(f"  3. 检查分页配置是否合理 (刚刚改为500可能导致超时)")
    print(f"  4. 增加详细的日志输出")

def simulate_fix_scenario():
    """模拟修复后的场景"""
    print(f"\n🔧 模拟修复后的场景:")
    
    # 假设新版本正确获取到了commits
    print(f"  假设新版本正确获取到了commits后:")
    
    # 更真实的新版本数据
    realistic_new_commit_task_map = {
        # GALAXY-12345 完全保留
        "GALAXY-12345||GALAXY-12345 修复用户登录问题": "GALAXY-12345",
        "GALAXY-12345||GALAXY-12345 增加单元测试": "GALAXY-12345",
        "GALAXY-12345||GALAXY-12345 修复代码格式问题": "GALAXY-12345",
        
        # GALAXY-23456 部分缺失 - 缺少"修复报表样式"
        "GALAXY-23456||GALAXY-23456 新增报表功能": "GALAXY-23456",
        
        # GALAXY-34567 完全缺失
        
        # GALAXY-45678 部分缺失 - 缺少"修复API性能问题"
        "GALAXY-45678||GALAXY-45678 修复API接口问题": "GALAXY-45678",
        "GALAXY-45678||GALAXY-45678 增加API文档": "GALAXY-45678",
        
        # 新增任务
        "GALAXY-56789||GALAXY-56789 新增AI功能": "GALAXY-56789",
        "GALAXY-67890||GALAXY-67890 优化前端性能": "GALAXY-67890",
    }
    
    realistic_new_tasks = set(realistic_new_commit_task_map.values())
    print(f"  新版本tasks: {len(realistic_new_tasks)} = {sorted(realistic_new_tasks)}")
    
    # 这种情况下应该有部分缺失任务
    old_tasks = {"GALAXY-12345", "GALAXY-23456", "GALAXY-34567", "GALAXY-45678"}
    
    completely_missing_realistic = old_tasks - realistic_new_tasks
    potentially_partial = old_tasks & realistic_new_tasks
    
    print(f"  完全缺失: {len(completely_missing_realistic)} = {sorted(completely_missing_realistic)}")
    print(f"  可能部分缺失: {len(potentially_partial)} = {sorted(potentially_partial)}")
    
    print(f"  ✅ 这种情况下就会有部分缺失任务了！")

if __name__ == "__main__":
    print("🚀 开始模拟任务分类逻辑分析...")
    
    try:
        # 模拟正常逻辑
        result = simulate_task_classification_logic()
        
        # 分析当前问题
        analyze_current_issue()
        
        # 模拟修复场景
        simulate_fix_scenario()
        
        print(f"\n" + "="*80)
        print(f"✅ 分析完成！")
        print(f"")
        print(f"🎯 结论:")
        print(f"  partially_missing_tasks变成completely_missing_tasks的根本原因是:")
        print(f"  新版本的commits获取不完整，导致新版本的任务集合不准确")
        print(f"  ")
        print(f"🔧 建议修复步骤:")
        print(f"  1. 检查版本标签 '7.1.0-hf37' 是否存在")
        print(f"  2. 将per_page从500改回100避免超时")
        print(f"  3. 增加详细日志查看commits获取过程")
        print(f"  4. 验证GitLab API返回数据的完整性")
        
    except Exception as e:
        print(f"\n❌ 分析过程中出错: {e}")
        import traceback
        traceback.print_exc() 