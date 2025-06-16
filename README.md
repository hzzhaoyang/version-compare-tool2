# 版本比较工具 v2.0

基于GitLab API的高性能版本比较和task分析工具，专门用于检测版本间的task缺失和新增功能。

## 🚀 v2.0 重大更新

### 🎯 核心改进
- **性能提升13倍**：从262.30s优化到~20s
- **完整数据获取**：获取全部commits（17,331 + 18,093 = 35,424个）
- **详细日志系统**：每页获取进度、统计信息、性能指标
- **去掉缓存依赖**：简化逻辑，避免缓存问题
- **优化文件命名**：去掉Optimized前缀，更简洁

### 📊 性能对比
| 指标 | v1.0 | v2.0 | 提升 |
|------|------|------|------|
| 总耗时 | 262.30s | ~20s | **13倍** |
| 获取commits | 100个 | 35,424个 | **354倍** |
| 数据准确性 | 部分 | 完整 | **100%** |
| 并发处理 | 无 | 8个worker | **8倍** |

### 🔧 技术架构
- **并发分页获取**：8个worker并发处理
- **智能页数探测**：二分查找快速定位总页数
- **本地内存分析**：避免重复API调用
- **详细性能监控**：实时统计和日志

## 📋 功能特性

### 🔍 缺失Task检测
- 检测旧版本中存在但新版本中缺失的GALAXY tasks
- 支持任意GitLab tag版本比较
- 提供详细的task列表和统计信息

### 🆕 新增功能分析
- 分析新版本中新增的features和tasks
- 识别版本间的功能差异
- 支持批量分析和报告生成

### 📊 性能监控
- 实时显示获取进度和速度
- 详细的统计信息和性能指标
- 支持并发处理状态监控

## 🛠️ 安装配置

### 环境要求
- Python 3.8+
- GitLab API访问权限
- 必要的Python依赖包

### 安装步骤
```bash
# 克隆项目
git clone <repository-url>
cd version-compare-tool2

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，设置GitLab相关配置
```

### 环境变量配置
```bash
GITLAB_URL=https://gitlab.mayidata.com/
GITLAB_TOKEN=your_gitlab_token
GITLAB_PROJECT_ID=130
```

## 🚀 使用方法

### 1. 命令行使用
```bash
# 测试核心功能
python3 test_v2_core.py

# 启动API服务
python3 -m src.api.main
```

### 2. API接口使用

#### 缺失Tasks检测
```bash
curl -X POST "http://localhost:8000/api/v2/missing-tasks" \
  -H "Content-Type: application/json" \
  -d '{
    "old_version": "6.6.0-ZSJJ-5",
    "new_version": "7.1.0-hf37"
  }'
```

#### 新增Features分析
```bash
curl -X POST "http://localhost:8000/api/v2/new-features" \
  -H "Content-Type: application/json" \
  -d '{
    "old_version": "6.6.0-ZSJJ-5", 
    "new_version": "7.1.0-hf37"
  }'
```

### 3. Python代码集成
```python
from src.gitlab.gitlab_manager_v2 import GitLabManager
from src.core.task_detector_v2 import TaskLossDetector

# 初始化
gitlab_manager = GitLabManager(gitlab_url, token, project_id)
detector = TaskLossDetector(gitlab_manager)

# 检测缺失tasks
result = detector.detect_missing_tasks("6.6.0-ZSJJ-5", "7.1.0-hf37")
print(f"缺失tasks: {len(result['missing_tasks'])}")

# 分析新增features
features = detector.analyze_new_features("6.6.0-ZSJJ-5", "7.1.0-hf37")
print(f"新增features: {len(features['new_features'])}")
```

## 📊 实际测试结果

### 测试环境
- 项目：guandata-core (项目ID: 130)
- 版本对比：6.6.0-ZSJJ-5 vs 7.1.0-hf37
- 测试时间：2025-06-16

### 测试结果
```
🎯 版本task分析完成:
    📊 总耗时: 19.23s (原版262.30s)
    ⚡ 性能提升: 13.6x 倍速
    📊 旧版本 6.6.0-ZSJJ-5: 3371 个tasks
    📊 新版本 7.1.0-hf37: 3966 个tasks
    🔍 缺失tasks: 12 个
    🆕 新增features: 607 个
    ✅ 共同tasks: 3359 个
```

### 详细统计
- **获取commits**：35,424个（17,331 + 18,093）
- **处理速度**：~900 commits/s
- **并发效率**：8个worker并发处理
- **数据准确性**：100%完整数据

## 🏗️ 项目结构

```
version-compare-tool2/
├── src/
│   ├── api/
│   │   └── main.py                 # FastAPI应用入口
│   ├── core/
│   │   └── task_detector_v2.py     # Task检测器v2
│   ├── gitlab/
│   │   └── gitlab_manager_v2.py    # GitLab管理器v2
│   └── services/
│       └── version_service.py      # 版本比较服务
├── docs/                           # 文档目录
├── .env.example                    # 环境变量模板
├── requirements.txt                # Python依赖
└── README.md                       # 项目文档
```

## 🔧 核心技术

### 并发分页获取
- 使用ThreadPoolExecutor实现8个worker并发
- 智能二分查找探测总页数
- 实时进度监控和错误处理

### 高效数据处理
- 本地内存分析，避免重复API调用
- 正则表达式快速提取GALAXY tasks
- 集合运算计算差异，性能优异

### 详细日志系统
- 分阶段进度显示
- 实时性能统计
- 详细错误信息和调试支持

## 🚨 注意事项

1. **API限制**：请注意GitLab API的速率限制
2. **网络稳定性**：大量数据获取需要稳定的网络连接
3. **内存使用**：处理大量commits时注意内存使用情况
4. **Token权限**：确保GitLab token有足够的项目访问权限

## 📈 性能优化建议

1. **并发数调整**：根据网络和服务器性能调整worker数量
2. **分页大小**：可根据实际情况调整每页获取的commits数量
3. **缓存策略**：对于频繁查询的数据可考虑添加缓存
4. **错误重试**：网络不稳定时可增加重试机制

## 🤝 贡献指南

欢迎提交Issue和Pull Request来改进这个工具！

## �� 许可证

MIT License 