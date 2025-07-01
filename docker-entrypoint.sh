#!/bin/bash
set -e

echo "🚀 启动版本比较工具服务..."

# 检查必要的环境变量
if [ -z "$GITLAB_URL" ]; then
    echo "❌ 错误: 未设置 GITLAB_URL 环境变量"
    exit 1
fi

if [ -z "$GITLAB_TOKEN" ] && [ -z "$GITLAB_TOKEN_BI_SERVER" ]; then
    echo "❌ 错误: 未设置 GitLab token 环境变量"
    exit 1
fi

# 设置默认值
export PORT=${PORT:-9112}
export DEBUG=${DEBUG:-false}
export LOG_LEVEL=${LOG_LEVEL:-INFO}
export ENVIRONMENT=${ENVIRONMENT:-production}

echo "📡 服务端口: $PORT (统一Web API + MCP服务)"
echo "🔧 调试模式: $DEBUG"
echo "📊 日志级别: $LOG_LEVEL"
echo "🌍 运行环境: $ENVIRONMENT"
echo "🌐 Web界面: http://localhost:$PORT/version-compare"
echo "🔗 MCP SSE端点: http://localhost:$PORT/api/mcp/sse"
echo "🔗 MCP健康检查: http://localhost:$PORT/api/mcp/health"
echo "📖 API文档: http://localhost:$PORT/docs"

echo "🚀 启动统一服务（Web界面 + API + MCP）..."
# 启动统一的Web API + MCP服务
exec uvicorn src.api.main:app \
    --host 0.0.0.0 \
    --port $PORT \
    --workers 2 \
    --log-level ${LOG_LEVEL,,} 