.PHONY: help build up up-dev down logs clean deploy health test

# 显示帮助信息
help:
	@echo "🚀 版本比较工具 Docker 部署命令"
	@echo "================================="
	@echo "build      - 构建Docker镜像"
	@echo "up         - 启动服务（生产模式）"
	@echo "up-dev     - 启动服务（开发模式）"
	@echo "down       - 停止服务"
	@echo "logs       - 查看日志"
	@echo "clean      - 清理所有容器和镜像"
	@echo "deploy     - 一键部署（交互式）"
	@echo "health     - 健康检查"
	@echo "test       - 测试API"

# 构建镜像
build:
	@echo "🔨 构建Docker镜像..."
	docker-compose build

# 生产模式启动
up:
	@echo "🏭 启动生产模式..."
	docker-compose up -d --build
	@echo "✅ 服务已启动"
	@echo "📡 访问地址: http://localhost:9112"

# 开发模式启动
up-dev:
	@echo "🔧 启动开发模式..."
	docker-compose up --build

# 停止服务
down:
	@echo "⏹️  停止服务..."
	docker-compose down

# 查看日志
logs:
	@echo "📋 查看服务日志..."
	docker-compose logs -f version-compare-api

# 清理
clean:
	@echo "🧹 清理容器和镜像..."
	docker-compose down --rmi all -v --remove-orphans
	docker system prune -f

# 一键部署
deploy:
	@echo "🚀 检查环境..."
	@if [ ! -f ".env" ]; then \
		echo "❌ 未找到.env文件，请先创建:"; \
		echo "   cp env.example .env"; \
		exit 1; \
	fi
	@chmod +x deploy.sh docker-entrypoint.sh
	@./deploy.sh

# 健康检查
health:
	@echo "🔍 执行健康检查..."
	@curl -f http://localhost:9112/health || echo "❌ 健康检查失败"

# API测试
test:
	@echo "🧪 测试API..."
	@curl -s http://localhost:9112/api | python3 -m json.tool || echo "❌ API测试失败" 