# 版本比较工具 MCP (Model Context Protocol) 支持

本项目已集成 [Model Context Protocol (MCP)](https://github.com/modelcontextprotocol/python-sdk) 支持，可以作为MCP工具供AI助手（如Claude、ChatGPT等）调用。

## 🚀 功能特性

### MCP 工具
- **analyze-new-features**: 分析两个版本之间的新增功能和特性
- **detect-missing-tasks**: 检测两个版本之间缺失的任务和功能

### 支持的运行模式
1. **标准IO模式**: 通过stdin/stdout进行通信
2. **SSE模式**: 通过HTTP和Server-Sent Events进行通信

## 📦 安装依赖

```bash
pip install -r requirements.txt
```

## ⚙️ 配置环境变量

创建 `.env` 文件或设置环境变量：

```bash
export GITLAB_URL="https://gitlab.example.com"
export GITLAB_TOKEN="your_gitlab_token_here"
export GITLAB_PROJECT_ID="your_project_id_here"

# 可选：SSE服务器端口（默认3000）
export MCP_PORT="3000"
```

## 🔧 使用方法

### 1. 标准IO MCP服务器

直接运行MCP服务器：

```bash
python3 src/mcp_server.py
```

### 2. SSE MCP服务器

启动支持HTTP的MCP服务器：

```bash
python3 src/mcp_sse_server.py
```

服务器将在 `http://localhost:3000` 启动，提供以下端点：
- `/health`: 健康检查
- `/messages`: MCP消息处理端点（POST）
- `/sse`: SSE连接端点（GET）

### 3. 客户端测试

运行测试脚本验证功能：

```bash
python3 test_mcp_client.py
```

## 🤖 AI助手集成

### Claude Desktop 配置

在Claude Desktop的配置文件中添加：

```json
{
  "mcpServers": {
    "version-compare-tool": {
      "command": "python3",
      "args": ["path/to/src/mcp_server.py"],
      "env": {
        "GITLAB_URL": "https://gitlab.example.com",
        "GITLAB_TOKEN": "your_token_here",
        "GITLAB_PROJECT_ID": "your_project_id_here"
      }
    }
  }
}
```

### 其他AI助手

对于支持MCP的其他AI助手，可以使用提供的配置文件 `mcp_config.json`。

## 🔍 工具详情

### analyze-new-features

**描述**: 分析两个版本之间的新增功能和特性

**参数**:
- `old_version` (string): 旧版本号（如：6.6.0-ZSJJ-5）
- `new_version` (string): 新版本号（如：7.1.0-hf37）

**返回**: 
- 新增功能统计信息
- 新增功能列表
- 完全新增任务列表
- 部分新增任务列表

### detect-missing-tasks

**描述**: 检测两个版本之间缺失的任务和功能

**参数**:
- `old_version` (string): 旧版本号（如：6.6.0-ZSJJ-5）
- `new_version` (string): 新版本号（如：7.1.0-hf37）

**返回**:
- 缺失任务统计信息
- 缺失任务列表
- 完全缺失任务列表
- 部分缺失任务列表

## 📝 使用示例

### 在AI助手中调用

```
请帮我分析版本 6.6.0-ZSJJ-5 到 7.1.0-hf37 之间的新增功能
```

AI助手将自动调用 `analyze-new-features` 工具并返回结果。

```
请检测版本 6.6.0-ZSJJ-5 到 7.1.0-hf37 之间有哪些功能缺失了
```

AI助手将自动调用 `detect-missing-tasks` 工具并返回结果。

## 🛠️ 开发说明

### 文件结构
```
src/
├── mcp_server.py          # 标准IO MCP服务器
├── mcp_sse_server.py      # SSE MCP服务器
└── services/
    └── version_service.py # 版本比较服务

mcp_config.json           # MCP配置文件
test_mcp_client.py       # 客户端测试脚本
```

### 扩展功能

要添加新的MCP工具：

1. 在 `@server.list_tools()` 中添加工具定义
2. 在 `@server.call_tool()` 中添加工具处理逻辑
3. 添加相应的格式化函数

## 🔗 相关链接

- [Model Context Protocol 官方文档](https://modelcontextprotocol.io)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Claude Desktop MCP 配置指南](https://claude.ai/docs)

## 🤝 贡献

欢迎提交Issue和Pull Request来改进MCP功能！ 