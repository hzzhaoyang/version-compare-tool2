#!/bin/bash

echo "🚀 版本比较工具 Docker 部署脚本"
echo "=================================="

# 检查是否存在 .env 文件
if [ ! -f ".env" ]; then
    echo "⚠️  未找到 .env 文件，请先创建配置文件"
    echo "📝 可以复制 env.example 为 .env 并修改配置"
    echo "   cp env.example .env"
    exit 1
fi

# 询问部署模式
echo "🤔 请选择部署模式:"
echo "1) 开发模式 (可以看到实时日志)"
echo "2) 生产模式 (后台运行)"
read -p "请输入选择 (1/2): " mode

case $mode in
    1)
        echo "🔧 启动开发模式..."
        docker-compose up --build
        ;;
    2)
        echo "🏭 启动生产模式..."
        docker-compose up -d --build
        echo "✅ 服务已在后台启动"
        echo "📡 服务地址: http://localhost:9112"
        echo "🔍 查看日志: docker-compose logs -f version-compare-api"
        echo "⏹️  停止服务: docker-compose down"
        ;;
    *)
        echo "❌ 无效选择"
        exit 1
        ;;
esac 