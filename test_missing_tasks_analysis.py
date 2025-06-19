#!/usr/bin/env python3
"""
分析partially_missing_tasks变成completely_missing_tasks的问题
测试版本: 6.6.0-ZSJJ-5 到 7.1.0-hf37
"""
import sys
import os
import json
import time
from typing import Dict, Any, Set, List

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.gitlab.gitlab_manager import GitLabManager
from src.core.task_detector import TaskLossDetector

def analyze_task_classification_issue():
    """分析任务分类问题"""
    print("🔍 开始分析partially_missing_tasks变成completely_missing_tasks的问题")
    print("="*80)
    
    # 初始化管理器
    gitlab_token = os.getenv('GITLAB_TOKEN')
    if not gitlab_token:
        print("❌ 请设置GITLAB_TOKEN环境变量")
        return
    
    gitlab_manager = GitLabManager(
        gitlab_url="https://gitlab.mayidata.com/",
        token=gitlab_token,
        project_id="130"
    )
    
    detector = TaskLossDetector(gitlab_manager)
    
    # 测试版本
    old_version = "6.6.0-ZSJJ-5"
    new_version = "7.1.0-hf37"
    
    print(f"📊 分析版本: {old_version} -> {new_version}")
    print("-"*60)
    
    # 获取详细分析结果
    start_time = time.time()
    result = detector.detect_missing_tasks(old_version, new_version)
    analysis_time = time.time() - start_time
    
    print(f"⏱️ 分析耗时: {analysis_time:.2f}s")
    print(f"📊 总体统计:")
    print(f"  - 旧版本commits: {result.get('old_commits_count', 0)}")
    print(f"  - 新版本commits: {result.get('new_commits_count', 0)}")
    print(f"  - 旧版本tasks: {len(result.get('old_tasks', []))}")
    print(f"  - 新版本tasks: {len(result.get('new_tasks', []))}")
    print(f"  - 缺失tasks总数: {len(result.get('missing_tasks', []))}")
    
    # 获取详细分析
    detailed_analysis = result.get('detailed_analysis', {})
    if not detailed_analysis:
        print("❌ 未获取到详细分析数据")
        return
    
    completely_missing = detailed_analysis.get('completely_missing_tasks', [])
    partially_missing = detailed_analysis.get('partially_missing_tasks', {})
    
    print(f"\n🔍 任务分类详情:")
    print(f"  - 完全缺失任务: {len(completely_missing)}")  
    print(f"  - 部分缺失任务: {len(partially_missing)}")
    
    # 深入分析为什么没有部分缺失任务
    print(f"\n🧮 深入分析任务分类逻辑:")
    
    # 获取原始的任务集合
    old_tasks = set(result.get('old_tasks', []))
    new_tasks = set(result.get('new_tasks', []))
    
    print(f"  - 旧版本任务数: {len(old_tasks)}")
    print(f"  - 新版本任务数: {len(new_tasks)}")
    print(f"  - 共同任务数: {len(old_tasks & new_tasks)}")
    print(f"  - 旧版本独有: {len(old_tasks - new_tasks)}")
    print(f"  - 新版本独有: {len(new_tasks - old_tasks)}")
    
    # 分析具体的任务
    missing_tasks = old_tasks - new_tasks
    print(f"\n📋 缺失任务示例 (前10个):")
    for i, task in enumerate(sorted(list(missing_tasks))[:10]):
        print(f"  {i+1}. {task}")
    
    # 检查是否有任务既在旧版本也在新版本中，但有不同的commits
    print(f"\n🔍 检查共同任务的commit差异:")
    common_tasks = old_tasks & new_tasks
    if common_tasks:
        print(f"  - 找到 {len(common_tasks)} 个共同任务")
        
        # 这里需要更深入的分析 - 获取原始的commit-task映射
        print("  - 正在分析共同任务的commit差异...")
        analyze_common_tasks_commits(gitlab_manager, old_version, new_version, list(common_tasks)[:5])
    else:
        print("  - ⚠️ 没有共同任务！这可能是问题的根源")
        print("  - 这意味着所有旧版本的任务在新版本中都完全不存在")
        print("  - 这很可能是版本获取或任务提取逻辑的问题")
    
    # 保存详细结果到文件
    save_analysis_results(result, old_version, new_version)
    
    return result

def analyze_common_tasks_commits(gitlab_manager: GitLabManager, old_version: str, new_version: str, sample_tasks: List[str]):
    """分析共同任务的commit差异"""
    print(f"    正在分析 {len(sample_tasks)} 个样本任务的commit差异...")
    
    try:
        # 获取两个版本的commits
        old_commits = gitlab_manager.get_all_tag_commits_concurrent(old_version)
        new_commits = gitlab_manager.get_all_tag_commits_concurrent(new_version)
        
        # 提取commit-task映射
        old_commit_task_map = gitlab_manager.extract_commit_messages_with_tasks(old_commits)
        new_commit_task_map = gitlab_manager.extract_commit_messages_with_tasks(new_commits)
        
        print(f"    旧版本commit-task映射: {len(old_commit_task_map)} 条")
        print(f"    新版本commit-task映射: {len(new_commit_task_map)} 条")
        
        # 分析每个样本任务
        for task_id in sample_tasks:
            # 找到该任务在两个版本中的所有commits
            old_task_commits = []
            new_task_commits = []
            
            for commit_key, task in old_commit_task_map.items():
                if task == task_id:
                    old_task_commits.append(commit_key)
            
            for commit_key, task in new_commit_task_map.items():
                if task == task_id:
                    new_task_commits.append(commit_key)
            
            if old_task_commits or new_task_commits:
                print(f"      任务 {task_id}:")
                print(f"        旧版本commits: {len(old_task_commits)}")
                print(f"        新版本commits: {len(new_task_commits)}")
                
                # 检查是否有缺失的commits
                old_commits_set = set(old_task_commits)
                new_commits_set = set(new_task_commits)
                missing_commits = old_commits_set - new_commits_set
                
                if missing_commits:
                    print(f"        缺失commits: {len(missing_commits)}")
                    for commit in list(missing_commits)[:2]:  # 只显示前2个
                        # 提取commit的可读部分
                        if '||' in commit:
                            readable_part = commit.split('||')[1][:50] + "..."
                        else:
                            readable_part = commit[:50] + "..."
                        print(f"          - {readable_part}")
                else:
                    print(f"        ✅ 没有缺失commits")
    
    except Exception as e:
        print(f"    ❌ 分析commit差异时出错: {e}")

def save_analysis_results(result: Dict[str, Any], old_version: str, new_version: str):
    """保存分析结果到文件"""
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"analysis_result_{old_version.replace('.', '_')}_{new_version.replace('.', '_')}_{timestamp}.json"
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2, default=str)
        print(f"\n💾 详细结果已保存到: {filename}")
    except Exception as e:
        print(f"\n❌ 保存结果失败: {e}")

def compare_with_previous_logic():
    """对比之前的逻辑"""
    print(f"\n🔍 分析逻辑变更:")
    print(f"  根据代码分析，partially_missing_tasks的判断逻辑是:")
    print(f"  1. 某个任务在旧版本中有commits")
    print(f"  2. 该任务在新版本中也存在")  
    print(f"  3. 但新版本中缺少该任务的某些commits")
    print(f"")
    print(f"  如果所有任务都被归类为completely_missing_tasks，说明:")
    print(f"  - 所有旧版本的任务在新版本中都完全不存在")
    print(f"  - 或者任务提取/匹配逻辑有问题")
    print(f"  - 或者版本标签指向了错误的commits")

if __name__ == "__main__":
    print("🚀 开始任务分类问题分析...")
    
    # 检查环境变量
    if not os.getenv('GITLAB_TOKEN'):
        print("❌ 请先设置GITLAB_TOKEN环境变量")
        print("   export GITLAB_TOKEN='your_gitlab_token'")
        sys.exit(1)
    
    try:
        result = analyze_task_classification_issue()
        compare_with_previous_logic()
        
        print(f"\n" + "="*80)
        print(f"✅ 分析完成！")
        print(f"如果问题依然存在，请检查:")
        print(f"1. 版本标签是否正确: 6.6.0-ZSJJ-5 和 7.1.0-hf37")
        print(f"2. GitLab API是否正常返回数据")
        print(f"3. 任务ID提取正则表达式是否正确")
        print(f"4. 最近的代码修改是否影响了逻辑")
        
    except KeyboardInterrupt:
        print(f"\n👋 分析已取消")
    except Exception as e:
        print(f"\n❌ 分析过程中出错: {e}")
        import traceback
        traceback.print_exc() 