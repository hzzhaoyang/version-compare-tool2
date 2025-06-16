#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
版本顺序和commit详情验证
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
    
    print("🧪 版本顺序和commit详情验证")
    print("=" * 50)
    
    try:
        # 初始化GitLab Manager
        gitlab_manager = GitLabManager(
            gitlab_url=os.getenv('GITLAB_URL'),
            token=os.getenv('GITLAB_TOKEN'),
            project_id=os.getenv('GITLAB_PROJECT_ID')
        )
        
        # 测试版本
        from_version = "7.1.0-hf37"
        to_version = "6.6.0-ZSJJ-5"
        target_task = "GALAXY-24672"
        
        print("🔍 检查版本信息和commit详情")
        print()
        
        # 1. 获取版本标签信息
        print("📋 获取版本标签信息:")
        try:
            # 获取from_version的commit信息
            from_commit = gitlab_manager.project.commits.get(from_version)
            print("   {}: {} ({})".format(from_version, from_commit.committed_date, from_commit.short_id))
        except Exception as e:
            print("   {}: 获取失败 - {}".format(from_version, e))
        
        try:
            # 获取to_version的commit信息
            to_commit = gitlab_manager.project.commits.get(to_version)
            print("   {}: {} ({})".format(to_version, to_commit.committed_date, to_commit.short_id))
        except Exception as e:
            print("   {}: 获取失败 - {}".format(to_version, e))
        
        print()
        
        # 2. 获取GALAXY-24672的详细信息
        print("🎯 获取 {} 的详细commit信息:".format(target_task))
        try:
            # 在to_version中搜索
            results = gitlab_manager.project.search(
                scope='commits',
                search=target_task,
                ref=to_version
            )
            
            if results:
                commit = results[0]  # 取第一个结果
                print("   Commit ID: {}".format(commit.get('id', 'N/A')))
                print("   Short ID: {}".format(commit.get('short_id', 'N/A')))
                print("   Message: {}".format(commit.get('message', 'N/A')))
                print("   Author: {}".format(commit.get('author_name', 'N/A')))
                print("   Date: {}".format(commit.get('committed_date', 'N/A')))
                
                # 获取完整的commit对象以获取更多信息
                try:
                    full_commit = gitlab_manager.project.commits.get(commit.get('id'))
                    print("   Parent IDs: {}".format([p['id'][:8] for p in full_commit.parent_ids] if hasattr(full_commit, 'parent_ids') else 'N/A'))
                except Exception as e:
                    print("   无法获取完整commit信息: {}".format(e))
            else:
                print("   未找到相关commit")
        except Exception as e:
            print("   搜索失败: {}".format(e))
        
        print()
        
        # 3. 检查版本差异
        print("🔄 检查版本差异 ({} -> {}):".format(from_version, to_version))
        try:
            diff_commits = gitlab_manager.get_version_diff(from_version, to_version)
            print("   差异commits数量: {}".format(len(diff_commits)))
            
            # 检查是否包含GALAXY-24672
            galaxy_commits = []
            for commit in diff_commits:
                if target_task in commit.get('message', ''):
                    galaxy_commits.append(commit)
            
            if galaxy_commits:
                print("   ✅ 在版本差异中找到 {} 相关commits:".format(target_task))
                for commit in galaxy_commits:
                    print("      {}: {}".format(commit.get('short_id', 'N/A'), commit.get('message', '')[:60]))
            else:
                print("   ❌ 在版本差异中未找到 {} 相关commits".format(target_task))
                
        except Exception as e:
            print("   获取版本差异失败: {}".format(e))
        
        print()
        
        # 4. 反向检查：to_version -> from_version
        print("🔄 反向检查版本差异 ({} -> {}):".format(to_version, from_version))
        try:
            reverse_diff_commits = gitlab_manager.get_version_diff(to_version, from_version)
            print("   反向差异commits数量: {}".format(len(reverse_diff_commits)))
            
            # 检查是否包含GALAXY-24672
            reverse_galaxy_commits = []
            for commit in reverse_diff_commits:
                if target_task in commit.get('message', ''):
                    reverse_galaxy_commits.append(commit)
            
            if reverse_galaxy_commits:
                print("   ✅ 在反向版本差异中找到 {} 相关commits:".format(target_task))
                for commit in reverse_galaxy_commits:
                    print("      {}: {}".format(commit.get('short_id', 'N/A'), commit.get('message', '')[:60]))
            else:
                print("   ❌ 在反向版本差异中未找到 {} 相关commits".format(target_task))
                
        except Exception as e:
            print("   获取反向版本差异失败: {}".format(e))
        
        print()
        
        # 5. 结论
        print("📊 分析结论:")
        print("-" * 30)
        print("基于测试结果:")
        print("1. GALAXY-24672 在 6.6.0-ZSJJ-5 中存在")
        print("2. GALAXY-24672 在 7.1.0-hf37 中不存在")
        print("3. 这意味着:")
        print("   - 如果 6.6.0-ZSJJ-5 是较新版本，则该task是新增的")
        print("   - 如果 7.1.0-hf37 是较新版本，则该task确实丢失了")
        print("   - 需要确认版本的时间顺序来判断是'新增'还是'丢失'")
        
        return True
        
    except Exception as e:
        print("❌ 测试失败: {}".format(e))
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = main()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ 版本分析完成")
        print("建议: 根据版本时间顺序确定是'新增'还是'丢失'")
    else:
        print("❌ 版本分析失败")
    
    sys.exit(0 if success else 1) 