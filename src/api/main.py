"""
版本比较工具 Web API
提供RESTful接口供钉钉机器人和前端调用
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import os
from dotenv import load_dotenv
import traceback
from typing import Dict, Any

from ..services.version_service import VersionCompareService, VersionCompareError

# 加载环境变量
load_dotenv()

app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 全局服务实例
version_service = None


def init_service():
    """初始化版本比较服务"""
    global version_service
    
    if version_service is None:
        try:
            gitlab_url = os.getenv('GITLAB_URL')
            gitlab_token = os.getenv('GITLAB_TOKEN')
            project_id = os.getenv('GITLAB_PROJECT_ID')
            openai_api_key = os.getenv('OPENAI_API_KEY')
            
            if not all([gitlab_url, gitlab_token, project_id]):
                raise ValueError("缺少必要的环境变量: GITLAB_URL, GITLAB_TOKEN, GITLAB_PROJECT_ID")
            
            version_service = VersionCompareService(
                gitlab_url=gitlab_url,
                gitlab_token=gitlab_token,
                project_id=project_id,
                openai_api_key=openai_api_key
            )
            
            print("✅ 版本比较服务初始化成功")
            
        except Exception as e:
            print(f"❌ 服务初始化失败: {e}")
            raise


def create_error_response(message: str, status_code: int = 500, details: str = None) -> tuple:
    """创建错误响应"""
    response = {
        'success': False,
        'error': message,
        'status_code': status_code
    }
    
    if details:
        response['details'] = details
    
    return jsonify(response), status_code


def create_success_response(data: Any, message: str = "操作成功") -> Dict[str, Any]:
    """创建成功响应"""
    return jsonify({
        'success': True,
        'message': message,
        'data': data
    })


@app.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    try:
        if version_service is None:
            init_service()
        
        health_status = version_service.health_check()
        return create_success_response(health_status, "服务健康检查完成")
        
    except Exception as e:
        return create_error_response(f"健康检查失败: {str(e)}", 503)


@app.route('/compare', methods=['POST'])
def compare_versions():
    """版本比较接口"""
    try:
        if version_service is None:
            init_service()
        
        data = request.get_json()
        if not data:
            return create_error_response("请求体不能为空", 400)
        
        from_version = data.get('from_version')
        to_version = data.get('to_version')
        include_ai = data.get('include_ai_analysis', True)
        
        if not from_version or not to_version:
            return create_error_response("缺少必要参数: from_version, to_version", 400)
        
        # 执行版本比较
        result = version_service.compare_versions(
            from_version=from_version,
            to_version=to_version,
            include_ai_analysis=include_ai
        )
        
        if result.get('analysis_status') == 'error':
            return create_error_response(
                f"版本比较失败: {result.get('error', 'Unknown error')}", 
                500,
                result
            )
        
        return create_success_response(result, f"版本比较完成: {from_version} -> {to_version}")
        
    except VersionCompareError as e:
        return create_error_response(f"版本比较错误: {str(e)}", 400)
    except Exception as e:
        print(f"❌ 版本比较接口异常: {e}")
        print(traceback.format_exc())
        return create_error_response(f"服务器内部错误: {str(e)}", 500)


@app.route('/batch-compare', methods=['POST'])
def batch_compare_versions():
    """批量版本比较接口"""
    try:
        if version_service is None:
            init_service()
        
        data = request.get_json()
        if not data:
            return create_error_response("请求体不能为空", 400)
        
        version_pairs = data.get('version_pairs', [])
        include_ai = data.get('include_ai_analysis', True)
        
        if not version_pairs:
            return create_error_response("缺少版本对列表: version_pairs", 400)
        
        # 验证版本对格式
        for pair in version_pairs:
            if not isinstance(pair, list) or len(pair) != 2:
                return create_error_response("版本对格式错误，应为 [from_version, to_version]", 400)
        
        # 执行批量比较
        result = version_service.batch_compare_versions(
            version_pairs=[(pair[0], pair[1]) for pair in version_pairs],
            include_ai_analysis=include_ai
        )
        
        return create_success_response(result, f"批量版本比较完成，共处理 {len(version_pairs)} 个版本对")
        
    except Exception as e:
        print(f"❌ 批量版本比较接口异常: {e}")
        print(traceback.format_exc())
        return create_error_response(f"服务器内部错误: {str(e)}", 500)


@app.route('/versions/suggestions', methods=['GET'])
def get_version_suggestions():
    """获取版本升级建议"""
    try:
        if version_service is None:
            init_service()
        
        current_version = request.args.get('current_version')
        max_suggestions = int(request.args.get('max_suggestions', 5))
        
        if not current_version:
            return create_error_response("缺少参数: current_version", 400)
        
        suggestions = version_service.get_version_suggestions(current_version, max_suggestions)
        
        return create_success_response({
            'current_version': current_version,
            'suggestions': suggestions,
            'count': len(suggestions)
        }, "版本建议获取成功")
        
    except Exception as e:
        print(f"❌ 版本建议接口异常: {e}")
        return create_error_response(f"服务器内部错误: {str(e)}", 500)


@app.route('/tasks/analyze', methods=['POST'])
def analyze_task_details():
    """分析特定tasks的详细信息"""
    try:
        if version_service is None:
            init_service()
        
        data = request.get_json()
        if not data:
            return create_error_response("请求体不能为空", 400)
        
        task_ids = data.get('task_ids', [])
        branch_name = data.get('branch_name')
        
        if not task_ids or not branch_name:
            return create_error_response("缺少必要参数: task_ids, branch_name", 400)
        
        result = version_service.analyze_task_details(task_ids, branch_name)
        
        return create_success_response(result, f"Task分析完成，共分析 {len(task_ids)} 个任务")
        
    except Exception as e:
        print(f"❌ Task分析接口异常: {e}")
        return create_error_response(f"服务器内部错误: {str(e)}", 500)


@app.route('/statistics', methods=['GET'])
def get_task_statistics():
    """获取版本间的task统计信息"""
    try:
        if version_service is None:
            init_service()
        
        from_version = request.args.get('from_version')
        to_version = request.args.get('to_version')
        
        if not from_version or not to_version:
            return create_error_response("缺少必要参数: from_version, to_version", 400)
        
        result = version_service.get_task_statistics(from_version, to_version)
        
        if 'error' in result:
            return create_error_response(f"统计获取失败: {result['error']}", 500)
        
        return create_success_response(result, "Task统计获取成功")
        
    except Exception as e:
        print(f"❌ Task统计接口异常: {e}")
        return create_error_response(f"服务器内部错误: {str(e)}", 500)


@app.route('/cache/clear', methods=['POST'])
def clear_caches():
    """清理所有缓存"""
    try:
        if version_service is None:
            init_service()
        
        result = version_service.clear_all_caches()
        
        if result.get('status') == 'error':
            return create_error_response(result.get('message', '缓存清理失败'), 500, result)
        
        return create_success_response(result, "缓存清理成功")
        
    except Exception as e:
        print(f"❌ 缓存清理接口异常: {e}")
        return create_error_response(f"服务器内部错误: {str(e)}", 500)


@app.route('/dingtalk/webhook', methods=['POST'])
def dingtalk_webhook():
    """钉钉机器人webhook接口"""
    try:
        if version_service is None:
            init_service()
        
        data = request.get_json()
        if not data:
            return create_error_response("请求体不能为空", 400)
        
        # 解析钉钉消息
        msg_type = data.get('msgtype')
        
        if msg_type == 'text':
            content = data.get('text', {}).get('content', '')
            
            # 简单的命令解析
            if '版本比较' in content or '升级检查' in content:
                # 提取版本信息（这里需要根据实际消息格式调整）
                # 示例: "版本比较 7.2.0 到 7.2.1"
                parts = content.split()
                if len(parts) >= 4:
                    from_ver = parts[1]
                    to_ver = parts[3]
                    
                    result = version_service.compare_versions(from_ver, to_ver)
                    
                    # 生成钉钉回复消息
                    ai_analysis = result.get('ai_analysis', {})
                    missing_count = len(result.get('missing_tasks', []))
                    
                    reply_text = f"""版本升级分析报告
📋 版本: {from_ver} -> {to_ver}
🎯 风险等级: {ai_analysis.get('risk_level', 'unknown').upper()}
⚠️ 缺失任务: {missing_count}个
💡 建议: {ai_analysis.get('recommendation', '请查看详细报告')}"""
                    
                    return jsonify({
                        'msgtype': 'text',
                        'text': {
                            'content': reply_text
                        }
                    })
        
        return jsonify({
            'msgtype': 'text',
            'text': {
                'content': '请使用格式: 版本比较 [源版本] 到 [目标版本]'
            }
        })
        
    except Exception as e:
        print(f"❌ 钉钉webhook异常: {e}")
        return jsonify({
            'msgtype': 'text',
            'text': {
                'content': f'处理失败: {str(e)}'
            }
        })


@app.errorhandler(404)
def not_found(error):
    """404错误处理"""
    return create_error_response("接口不存在", 404)


@app.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    return create_error_response("服务器内部错误", 500)


if __name__ == '__main__':
    # 开发环境启动
    try:
        init_service()
        print("🚀 启动版本比较工具API服务...")
        app.run(
            host='0.0.0.0',
            port=int(os.getenv('PORT', 5000)),
            debug=os.getenv('DEBUG', 'False').lower() == 'true'
        )
    except Exception as e:
        print(f"❌ 服务启动失败: {e}")
        exit(1) 