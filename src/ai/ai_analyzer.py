"""
AI分析服务
基于OpenAI API提供智能版本分析和报告生成
"""
import openai
import json
from typing import Dict, List, Any, Optional
import os


class AIVersionAnalyzer:
    """AI版本分析器"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if self.api_key:
            openai.api_key = self.api_key
            print("✅ AI分析服务已初始化")
        else:
            print("⚠️ 未找到OpenAI API密钥，AI分析功能将使用备用方案")
    
    def analyze_version_changes(self, task_diff_data: Dict[str, Any]) -> Dict[str, Any]:
        """AI分析版本变更"""
        missing_tasks = task_diff_data.get('missing_tasks', [])
        existing_tasks = task_diff_data.get('existing_tasks', [])
        total_diff_commits = task_diff_data.get('total_diff_commits', 0)
        
        # 如果没有显著变更，返回简单分析
        if not missing_tasks and not existing_tasks:
            return {
                'summary': '无显著变更',
                'risk_level': 'low',
                'recommendation': '版本升级风险较低，可以正常进行',
                'analysis_method': 'simple'
            }
        
        # 尝试AI分析
        if self.api_key:
            try:
                return self._ai_analysis(missing_tasks, existing_tasks, total_diff_commits)
            except Exception as e:
                print(f"⚠️ AI分析失败，使用备用方案: {e}")
                return self._generate_simple_analysis(missing_tasks, existing_tasks, total_diff_commits)
        else:
            return self._generate_simple_analysis(missing_tasks, existing_tasks, total_diff_commits)
    
    def _ai_analysis(self, missing_tasks: List[str], existing_tasks: List[str], total_commits: int) -> Dict[str, Any]:
        """使用OpenAI进行智能分析"""
        prompt = self._build_analysis_prompt(missing_tasks, existing_tasks, total_commits)
        
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "你是一个专业的软件版本升级分析师，专门分析GALAXY任务系统的版本变更风险。请提供准确、实用的分析建议。"
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=800,
            temperature=0.3
        )
        
        ai_response = response.choices[0].message.content
        return self._parse_ai_response(ai_response, missing_tasks, existing_tasks)
    
    def _build_analysis_prompt(self, missing_tasks: List[str], existing_tasks: List[str], total_commits: int) -> str:
        """构建AI分析提示"""
        prompt = f"""请分析以下版本升级情况：

📊 **版本变更统计**:
- 总差异commits: {total_commits}
- 缺失的GALAXY任务: {len(missing_tasks)}个
- 已存在的GALAXY任务: {len(existing_tasks)}个

"""
        
        if missing_tasks:
            prompt += f"⚠️ **缺失的任务** ({len(missing_tasks)}个):\n"
            # 限制显示数量避免prompt过长
            display_tasks = missing_tasks[:15]
            for task in display_tasks:
                prompt += f"- {task}\n"
            if len(missing_tasks) > 15:
                prompt += f"- ... 还有{len(missing_tasks)-15}个任务\n"
            prompt += "\n"
        
        if existing_tasks:
            prompt += f"✅ **已存在的任务**: {len(existing_tasks)}个任务在新版本中已存在\n\n"
        
        prompt += """请提供以下分析：

1. **风险评估** (请从以下选择: high/medium/low)
   - high: 缺失任务超过10个或包含关键功能
   - medium: 缺失任务5-10个或影响中等
   - low: 缺失任务少于5个或影响较小

2. **主要变更总结** (50字以内)

3. **升级建议** (100字以内)

请用以下JSON格式回复：
```json
{
    "risk_level": "high/medium/low",
    "summary": "主要变更总结",
    "recommendation": "具体的升级建议",
    "key_concerns": ["关键关注点1", "关键关注点2"]
}
```"""
        
        return prompt
    
    def _parse_ai_response(self, ai_response: str, missing_tasks: List[str], existing_tasks: List[str]) -> Dict[str, Any]:
        """解析AI响应"""
        try:
            # 尝试提取JSON部分
            json_start = ai_response.find('{')
            json_end = ai_response.rfind('}') + 1
            
            if json_start != -1 and json_end != -1:
                json_str = ai_response[json_start:json_end]
                parsed = json.loads(json_str)
                
                # 验证必要字段
                result = {
                    'risk_level': parsed.get('risk_level', 'medium'),
                    'summary': parsed.get('summary', '版本变更分析'),
                    'recommendation': parsed.get('recommendation', '建议仔细检查变更内容'),
                    'key_concerns': parsed.get('key_concerns', []),
                    'missing_count': len(missing_tasks),
                    'existing_count': len(existing_tasks),
                    'analysis_method': 'ai_powered'
                }
                
                return result
            else:
                raise ValueError("无法找到JSON格式的响应")
                
        except Exception as e:
            print(f"⚠️ AI响应解析失败: {e}")
            # 降级到简单分析
            return self._generate_simple_analysis(missing_tasks, existing_tasks, 0)
    
    def _generate_simple_analysis(self, missing_tasks: List[str], existing_tasks: List[str], total_commits: int) -> Dict[str, Any]:
        """生成简单分析（AI失败时的备用方案）"""
        missing_count = len(missing_tasks)
        existing_count = len(existing_tasks)
        
        # 基于规则的风险评估
        if missing_count == 0:
            risk_level = 'low'
            summary = f'无缺失任务，{existing_count}个任务已存在于新版本'
            recommendation = '版本升级风险较低，可以正常进行'
            key_concerns = []
        elif missing_count <= 5:
            risk_level = 'low'
            summary = f'检测到{missing_count}个缺失任务，影响较小'
            recommendation = '建议检查缺失任务的具体影响，通常可以安全升级'
            key_concerns = ['检查缺失任务是否为关键功能']
        elif missing_count <= 15:
            risk_level = 'medium'
            summary = f'检测到{missing_count}个缺失任务，需要关注'
            recommendation = '建议详细评估缺失任务的影响，考虑分阶段升级'
            key_concerns = ['评估缺失任务的业务影响', '考虑回滚方案']
        else:
            risk_level = 'high'
            summary = f'检测到{missing_count}个缺失任务，风险较高'
            recommendation = '强烈建议暂缓升级，详细分析所有缺失任务的影响'
            key_concerns = ['全面评估业务影响', '准备详细的回滚计划', '考虑分批次升级']
        
        return {
            'risk_level': risk_level,
            'summary': summary,
            'recommendation': recommendation,
            'key_concerns': key_concerns,
            'missing_count': missing_count,
            'existing_count': existing_count,
            'analysis_method': 'rule_based'
        }
    
    def generate_detailed_report(self, version_comparison: Dict[str, Any], from_version: str, to_version: str) -> str:
        """生成详细的版本升级报告"""
        missing_tasks = version_comparison.get('missing_tasks', [])
        existing_tasks = version_comparison.get('existing_tasks', [])
        ai_analysis = version_comparison.get('ai_analysis', {})
        processing_time = version_comparison.get('processing_time', 0)
        
        report = f"""# 版本升级分析报告

## 📋 基本信息
- **源版本**: {from_version}
- **目标版本**: {to_version}
- **分析时间**: {processing_time:.2f}秒
- **分析方法**: {ai_analysis.get('analysis_method', 'unknown')}

## 🎯 风险评估
**风险等级**: {ai_analysis.get('risk_level', 'unknown').upper()}

## 📊 变更统计
- **缺失任务**: {len(missing_tasks)}个
- **已存在任务**: {len(existing_tasks)}个
- **总差异commits**: {version_comparison.get('total_diff_commits', 0)}个

## 💡 分析总结
{ai_analysis.get('summary', '无分析总结')}

## 📋 升级建议
{ai_analysis.get('recommendation', '无具体建议')}
"""
        
        # 添加关键关注点
        key_concerns = ai_analysis.get('key_concerns', [])
        if key_concerns:
            report += "\n## ⚠️ 关键关注点\n"
            for i, concern in enumerate(key_concerns, 1):
                report += f"{i}. {concern}\n"
        
        # 添加缺失任务详情
        if missing_tasks:
            report += f"\n## 🚨 缺失任务详情 ({len(missing_tasks)}个)\n"
            for i, task in enumerate(missing_tasks[:20], 1):  # 限制显示数量
                report += f"{i}. {task}\n"
            if len(missing_tasks) > 20:
                report += f"... 还有{len(missing_tasks)-20}个任务\n"
        
        # 添加已存在任务（如果数量不多）
        if existing_tasks and len(existing_tasks) <= 10:
            report += f"\n## ✅ 已存在任务 ({len(existing_tasks)}个)\n"
            for i, task in enumerate(existing_tasks, 1):
                report += f"{i}. {task}\n"
        elif existing_tasks:
            report += f"\n## ✅ 已存在任务\n共{len(existing_tasks)}个任务在新版本中已存在\n"
        
        return report
    
    def analyze_multiple_versions(self, version_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """分析多个版本比较的结果"""
        if not version_results:
            return {'summary': '无版本比较数据'}
        
        total_missing = sum(len(result.get('missing_tasks', [])) for result in version_results)
        total_existing = sum(len(result.get('existing_tasks', [])) for result in version_results)
        avg_processing_time = sum(result.get('processing_time', 0) for result in version_results) / len(version_results)
        
        # 风险趋势分析
        risk_levels = [result.get('ai_analysis', {}).get('risk_level', 'unknown') for result in version_results]
        risk_distribution = {
            'high': risk_levels.count('high'),
            'medium': risk_levels.count('medium'),
            'low': risk_levels.count('low')
        }
        
        return {
            'total_comparisons': len(version_results),
            'total_missing_tasks': total_missing,
            'total_existing_tasks': total_existing,
            'avg_processing_time': round(avg_processing_time, 2),
            'risk_distribution': risk_distribution,
            'overall_risk': 'high' if risk_distribution['high'] > 0 else 'medium' if risk_distribution['medium'] > 0 else 'low'
        } 