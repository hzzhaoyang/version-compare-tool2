# 🚀 版本比较工具 Docker 部署指南

## 📋 部署前准备

### 1. 环境要求
- Docker 20.10+
- Docker Compose 2.0+
- 2GB+ 可用内存
- 500MB+ 可用磁盘空间

### 2. 配置环境变量
```bash
# 复制环境变量模板
cp env.example .env

# 编辑配置文件
vim .env
```

**必需配置项：**
```bash
# GitLab 配置
GITLAB_URL=https://your-gitlab-domain.com
GITLAB_TOKEN_BI_SERVER=your_gitlab_token_here
GITLAB_PROJECT_ID_BI_SERVER=your_project_id_here

# 服务配置
PORT=9112
DEBUG=false
```

## 🔧 部署方式

### 方式1：使用部署脚本（推荐）
```bash
# 给脚本执行权限
chmod +x deploy.sh

# 运行部署脚本
./deploy.sh
```

### 方式2：手动部署

#### 开发模式（前台运行）
```bash
docker-compose up --build
```

#### 生产模式（后台运行）
```bash
docker-compose up -d --build
```

## 📊 部署验证

### 1. 检查服务状态
```bash
# 检查容器状态
docker-compose ps

# 查看日志
docker-compose logs -f version-compare-api

# 健康检查
curl http://localhost:9112/health
```

### 2. 访问服务
- **Web界面**: http://localhost:9112
- **API文档**: http://localhost:9112/docs
- **健康检查**: http://localhost:9112/health
- **API信息**: http://localhost:9112/api

## 🔍 常用命令

```bash
# 查看实时日志
docker-compose logs -f version-compare-api

# 重启服务
docker-compose restart version-compare-api

# 停止服务
docker-compose down

# 完全清理（包括镜像）
docker-compose down --rmi all -v

# 进入容器调试
docker-compose exec version-compare-api bash
```

## 🛠️ 故障排除

### 1. 容器启动失败
```bash
# 查看详细日志
docker-compose logs version-compare-api

# 检查配置文件
cat .env
```

### 2. 健康检查失败
```bash
# 检查端口是否被占用
netstat -tlnp | grep 9112

# 检查GitLab连接
curl -H "PRIVATE-TOKEN: your_token" https://your-gitlab-domain.com/api/v4/user
```

### 3. 内存不足
```bash
# 查看资源使用情况
docker stats

# 优化配置（减少worker数量）
# 在docker-compose.yml中修改启动参数
```

## 🔒 安全建议

1. **环境变量安全**
   - 不要将 `.env` 文件提交到版本控制
   - 使用强密码和安全的API密钥
   - 定期轮换访问令牌

2. **网络安全**
   - 在生产环境中使用反向代理（如nginx）
   - 配置HTTPS证书
   - 限制访问IP范围

3. **数据安全**
   - 定期备份日志文件
   - 监控服务运行状态
   - 设置日志轮转

## 📈 性能优化

1. **资源配置**
   ```yaml
   # 在docker-compose.yml中添加资源限制
   deploy:
     resources:
       limits:
         memory: 1G
         cpus: '0.5'
   ```

2. **日志管理**
   ```yaml
   # 配置日志轮转
   logging:
     driver: "json-file"
     options:
       max-size: "10m"
       max-file: "3"
   ```

## 🚀 扩展部署

### 多实例部署
```yaml
version: '3.8'
services:
  version-compare-api:
    # ... 其他配置
    deploy:
      replicas: 3
```

### 负载均衡
如需要负载均衡，可以在前端添加nginx或使用Docker Swarm模式。

---

## 📞 支持

如果遇到问题，请：
1. 查看日志文件
2. 检查环境配置
3. 参考常见问题解答
4. 联系技术支持 