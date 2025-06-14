# 智能版本比较工具

基于GitLab API和AI技术的智能版本比较工具，专门用于检测GALAXY任务系统的版本升级风险。

## 🎯 核心功能

- **精确Task检测**: 基于GitLab Compare API精确检测缺失的GALAXY tasks
- **AI智能分析**: 使用OpenAI提供智能的版本升级风险评估
- **请求级缓存**: 高效的缓存机制，大幅提升性能
- **钉钉机器人**: 支持自然语言查询版本升级信息
- **RESTful API**: 完整的Web API接口

## 🚀 快速开始

### 环境要求

- Python 3.9+
- GitLab访问权限
- OpenAI API密钥（可选，用于AI分析）

### 安装步骤

1. **克隆项目**
```bash
git clone <repository-url>
cd version-compare-tool
```

2. **安装依赖**
```bash
pip install -r requirements.txt
```

3. **配置环境变量**
```bash
cp env.example .env
# 编辑 .env 文件，填入你的配置
```

4. **启动服务**
```bash
python run.py
```

### Docker部署

```bash
# 构建镜像
docker-compose build

# 启动服务
docker-compose up -d
```

## 📋 API接口

### 版本比较
```bash
POST /compare
{
    "from_version": "7.2.0",
    "to_version": "7.2.1",
    "include_ai_analysis": true
}
```

### 批量比较
```bash
POST /batch-compare
{
    "version_pairs": [
        ["7.2.0", "7.2.1"],
        ["7.2.1", "7.2.2"]
    ],
    "include_ai_analysis": true
}
```

### 健康检查
```bash
GET /health
```

### 版本建议
```bash
GET /versions/suggestions?current_version=7.2.0&max_suggestions=5
```

## 🤖 钉钉机器人

支持自然语言查询：
- "版本比较 7.2.0 到 7.2.1"
- "升级检查 6.3.0-hf7 到 patch-7.2.0-hf2"

## 🏗️ 架构设计

```
├── src/
│   ├── core/           # 核心算法
│   │   ├── task_detector.py    # Task丢失检测
│   │   └── cache_manager.py    # 缓存管理
│   ├── gitlab/         # GitLab集成
│   │   └── gitlab_manager.py   # GitLab API封装
│   ├── ai/             # AI分析
│   │   └── ai_analyzer.py      # AI版本分析
│   ├── services/       # 业务服务
│   │   └── version_service.py  # 版本比较服务
│   └── api/            # Web接口
│       └── main.py             # Flask API
├── Dockerfile          # Docker配置
├── docker-compose.yml  # 容器编排
└── requirements.txt    # Python依赖
```

## 🔧 核心算法

### Task丢失检测流程

1. **获取版本差异**: 使用GitLab Compare API获取两版本间的实际差异commits
2. **提取Task ID**: 从差异commits中提取GALAXY-XXXXX格式的task IDs
3. **批量验证**: 一次性获取目标分支所有tasks，批量验证存在性
4. **精确结果**: 计算真正缺失的tasks，剔除误报

### 性能优化

- **请求级缓存**: 同一请求内避免重复API调用
- **批量处理**: 批量验证task存在性，减少API调用
- **智能降级**: 多层降级策略确保系统鲁棒性

## 📊 性能指标

- **API调用减少**: 80%+
- **处理时间**: 从30-60分钟降低到2-5分钟
- **缓存命中率**: 通常>70%

## 🔒 安全考虑

- 使用非root用户运行容器
- 环境变量管理敏感信息
- API访问控制和错误处理
- 健康检查和监控

## 🛠️ 开发指南

### 本地开发

```bash
# 安装开发依赖
pip install -r requirements.txt

# 启动开发服务器
DEBUG=true python run.py
```

### 测试

```bash
# 健康检查
curl http://localhost:5000/health

# 版本比较测试
curl -X POST http://localhost:5000/compare \
  -H "Content-Type: application/json" \
  -d '{"from_version": "7.2.0", "to_version": "7.2.1"}'
```

## 📝 配置说明

### 必需配置
- `GITLAB_URL`: GitLab服务器地址
- `GITLAB_TOKEN`: GitLab访问令牌
- `GITLAB_PROJECT_ID`: 项目ID

### 可选配置
- `OPENAI_API_KEY`: OpenAI API密钥（用于AI分析）
- `PORT`: 服务端口（默认5000）
- `DEBUG`: 调试模式（默认false）

## 🤝 贡献指南

1. Fork项目
2. 创建功能分支
3. 提交变更
4. 发起Pull Request

## 📄 许可证

MIT License

## 🆘 支持

如有问题，请提交Issue或联系开发团队。 