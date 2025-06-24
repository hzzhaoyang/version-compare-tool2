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

echo "📡 服务端口: $PORT (Web API + MCP 集成)"
echo "🔧 调试模式: $DEBUG"
echo "📊 日志级别: $LOG_LEVEL"
echo "🌍 运行环境: $ENVIRONMENT"
echo "🔗 MCP SSE 端点: http://localhost:$PORT/api/mcp/sse"
echo "🔗 MCP 健康检查: http://localhost:$PORT/api/mcp/health"

echo "🚀 启动集成 MCP 的 Web API 服务..."
# 启动集成了MCP的Web API服务
exec uvicorn src.api.main:app \
    --host 0.0.0.0 \
    --port $PORT \
    --workers 2 \
    --log-level ${LOG_LEVEL,,} 