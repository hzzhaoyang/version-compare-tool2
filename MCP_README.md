# 版本比较工具 MCP (Model Context Protocol) 支持

本项目已集成 [Model Context Protocol (MCP)](https://github.com/modelcontextprotocol/python-sdk) 支持，可以作为MCP工具供AI助手（如Claude、ChatGPT等）调用。

## 🚀 功能特性

### MCP 工具
- **analyze-new-features**: 分析两个版本之间的新增功能和特性
- **detect-missing-tasks**: 检测两个版本之间缺失的任务和功能
- **list-supported-projects**: 列出所有支持的GitLab项目配置（无需参数）

### 统一架构设计
- **集成式服务**: MCP功能已集成到Web API服务器中
- **SSE通信**: 通过HTTP和Server-Sent Events进行通信
- **多项目支持**: 从JSON配置文件动态加载项目配置
- **Web界面**: 提供完整的Web界面进行版本比较操作

## 📦 安装依赖

```bash
pip install -r requirements.txt
```

## ⚙️ 配置环境变量

项目配置从 `config/projects.json` 文件读取，支持多项目配置。创建 `.env` 文件或设置环境变量：

```bash
# GitLab基础配置
export GITLAB_URL="https://gitlab.example.com"

# 项目配置（示例：复杂报表专业版）
export GITLAB_TOKEN_COMPLEX_REPORT_PRO="your_gitlab_token_here"
export GITLAB_PROJECT_ID_COMPLEX_REPORT_PRO="415"

# 其他项目配置（可选）
export GITLAB_TOKEN_BI_SERVER="your_token"
export GITLAB_PROJECT_ID_BI_SERVER="130"

export GITLAB_TOKEN_DATA_MIND="your_token"
export GITLAB_PROJECT_ID_DATA_MIND="385"
# ... 更多项目配置
```

## 🔧 使用方法

### 1. 启动集成服务

启动包含Web界面和MCP功能的统一服务：

```bash
python3 run.py
```

或使用uvicorn直接启动：

```bash
uvicorn src.api.main:app --host 0.0.0.0 --port 9112
```

服务器将在 `http://localhost:9112` 启动，提供以下端点：
- `/`: 前端Web界面
- `/api/mcp/health`: MCP健康检查
- `/api/mcp/sse`: MCP SSE连接端点
- `/api/mcp/messages/`: MCP消息处理端点
- `/docs`: API文档

### 2. 客户端测试

运行测试脚本验证功能：

```bash
python3 test_integrated_mcp.py
```

## 🤖 AI助手集成

### Claude Desktop 配置

在Claude Desktop的配置文件中添加：

```json
{
  "mcpServers": {
    "version-compare-tool": {
      "command": "uvicorn",
      "args": ["src.api.main:app", "--host", "0.0.0.0", "--port", "9112"],
      "env": {
        "GITLAB_URL": "https://gitlab.example.com",
        "GITLAB_TOKEN_COMPLEX_REPORT_PRO": "your_token_here",
        "GITLAB_PROJECT_ID_COMPLEX_REPORT_PRO": "415"
      }
    }
  }
}
```

💡 **提示**: 配置完成后，Claude Desktop将通过SSE连接到 `http://localhost:9112/api/mcp/sse` 端点使用MCP工具。

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

### list-supported-projects

**描述**: 列出所有支持的GitLab项目配置信息

**参数**: 无参数

**返回**:
- 项目配置列表
- 项目ID、名称、URL等信息
- 当前连接状态

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

```
请列出所有支持的GitLab项目
```

AI助手将自动调用 `list-supported-projects` 工具并返回当前配置的所有项目信息。

## 🛠️ 开发说明

### 文件结构
```
src/
├── api/
│   └── main.py           # 集成的Web API + MCP服务器
└── services/
    └── version_service.py # 版本比较服务

config/
└── projects.json         # 项目配置文件

mcp_config.json          # MCP配置文件
test_integrated_mcp.py   # 集成测试脚本
```

### 扩展功能

要添加新的MCP工具：

1. 在 `src/api/main.py` 的 `@mcp_server.list_tools()` 中添加工具定义
2. 在 `@mcp_server.call_tool()` 中添加工具处理逻辑
3. 要添加新项目支持，在 `config/projects.json` 中添加项目配置

### 架构优势

- **统一服务**: Web界面、API和MCP功能在同一服务中
- **配置管理**: 项目配置外部化到JSON文件
- **零兼容代码**: 彻底移除向后兼容逻辑，代码简洁清晰
- **多项目支持**: 动态加载和切换项目配置
3. 添加相应的格式化函数

## 🔗 相关链接

- [Model Context Protocol 官方文档](https://modelcontextprotocol.io)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Claude Desktop MCP 配置指南](https://claude.ai/docs)

## 🤝 贡献

欢迎提交Issue和Pull Request来改进MCP功能！ 