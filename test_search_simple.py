#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化的GitLab Search API测试
专门测试GALAXY-24672在不同版本中的存在情况
"""
import os
import sys
from dotenv import load_dotenv

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.gitlab.gitlab_manager import GitLabManager


def main():
    """主测试函数"""
    # 加载环境变量
    load_dotenv()
    
    print("🧪 GitLab Search API 简化测试")
    print("=" * 50)
    
    # 检查环境变量
    required_vars = ['GITLAB_URL', 'GITLAB_TOKEN', 'GITLAB_PROJECT_ID']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print("❌ 缺少必要的环境变量: {}".format(', '.join(missing_vars)))
        return False
    
    try:
        # 初始化GitLab Manager
        gitlab_manager = GitLabManager(
            gitlab_url=os.getenv('GITLAB_URL'),
            token=os.getenv('GITLAB_TOKEN'),
            project_id=os.getenv('GITLAB_PROJECT_ID')
        )
        
        # 测试目标
        target_task = "GALAXY-24672"
        from_version = "7.1.0-hf37"
        to_version = "6.6.0-ZSJJ-5"
        
        print("🎯 测试目标: {}".format(target_task))
        print("📋 版本对比: {} -> {}".format(from_version, to_version))
        print()
        
        # 测试1: 在from_version中搜索
        print("🔍 测试1: 在 {} 中搜索 {}".format(from_version, target_task))
        try:
            from_results = gitlab_manager.project.search(
                scope='commits',
                search=target_task,
                ref=from_version
            )
            
            print("   搜索结果数量: {}".format(len(from_results)))
            if from_results:
                print("   ✅ 在 {} 中找到 {}".format(from_version, target_task))
                for i, commit in enumerate(from_results[:2]):  # 显示前2个结果
                    msg = commit.get('message', '')[:60] + "..." if len(commit.get('message', '')) > 60 else commit.get('message', '')
                    print("      [{}] {}: {}".format(i+1, commit.get('short_id', 'N/A'), msg))
            else:
                print("   ❌ 在 {} 中未找到 {}".format(from_version, target_task))
                
        except Exception as e:
            print("   ❌ 搜索 {} 失败: {}".format(from_version, e))
            from_results = []
        
        print()
        
        # 测试2: 在to_version中搜索
        print("🔍 测试2: 在 {} 中搜索 {}".format(to_version, target_task))
        try:
            to_results = gitlab_manager.project.search(
                scope='commits',
                search=target_task,
                ref=to_version
            )
            
            print("   搜索结果数量: {}".format(len(to_results)))
            if to_results:
                print("   ✅ 在 {} 中找到 {}".format(to_version, target_task))
                for i, commit in enumerate(to_results[:2]):  # 显示前2个结果
                    msg = commit.get('message', '')[:60] + "..." if len(commit.get('message', '')) > 60 else commit.get('message', '')
                    print("      [{}] {}: {}".format(i+1, commit.get('short_id', 'N/A'), msg))
            else:
                print("   ❌ 在 {} 中未找到 {}".format(to_version, target_task))
                
        except Exception as e:
            print("   ❌ 搜索 {} 失败: {}".format(to_version, e))
            to_results = []
        
        print()
        
        # 测试3: 全局搜索
        print("🔍 测试3: 全局搜索 {} (不指定版本)".format(target_task))
        try:
            global_results = gitlab_manager.project.search(
                scope='commits',
                search=target_task
            )
            
            print("   全局搜索结果数量: {}".format(len(global_results)))
            if global_results:
                print("   ✅ 全局搜索找到 {}".format(target_task))
                for i, commit in enumerate(global_results[:3]):  # 显示前3个结果
                    msg = commit.get('message', '')[:50] + "..." if len(commit.get('message', '')) > 50 else commit.get('message', '')
                    print("      [{}] {}: {}".format(i+1, commit.get('short_id', 'N/A'), msg))
            else:
                print("   ❌ 全局搜索未找到 {}".format(target_task))
                
        except Exception as e:
            print("   ❌ 全局搜索失败: {}".format(e))
            global_results = []
        
        print()
        
        # 分析结果
        print("📊 结果分析:")
        print("-" * 30)
        
        from_found = len(from_results) > 0
        to_found = len(to_results) > 0
        global_found = len(global_results) > 0
        
        print("   {}: {}".format(from_version, "✅ 存在" if from_found else "❌ 不存在"))
        print("   {}: {}".format(to_version, "✅ 存在" if to_found else "❌ 不存在"))
        print("   全局搜索: {}".format("✅ 存在" if global_found else "❌ 不存在"))
        
        # 判断预期结果
        if from_found and not to_found:
            print("\n🎯 结果符合预期:")
            print("   {} 在 {} 中存在，在 {} 中不存在".format(target_task, from_version, to_version))
            print("   这意味着该task在版本升级过程中丢失了")
            print("   ✅ GitLab Search API 实现是正确的")
            return True
        elif not from_found and to_found:
            print("\n⚠️ 结果与预期相反:")
            print("   {} 在 {} 中不存在，在 {} 中存在".format(target_task, from_version, to_version))
            print("   这可能意味着该task是在新版本中新增的")
            return False
        elif from_found and to_found:
            print("\n🤔 两个版本都存在:")
            print("   {} 在两个版本中都存在".format(target_task))
            print("   这意味着该task没有丢失，可能是其他问题")
            return False
        else:
            print("\n❌ 两个版本都不存在:")
            print("   {} 在两个版本中都不存在".format(target_task))
            if global_found:
                print("   但全局搜索能找到，可能是版本标签问题")
            else:
                print("   全局搜索也找不到，可能task ID不正确或权限问题")
            return False
            
    except Exception as e:
        print("❌ 测试失败: {}".format(e))
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ 验证完成，Search API方案可行")
        print("建议: 简化实现，只保留Search API方案")
    else:
        print("❌ 验证失败，需要进一步调查问题")
    
    sys.exit(0 if success else 1) 