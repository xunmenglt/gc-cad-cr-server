# Docker 部署说明

## 项目结构
- `client/` - 前端服务 (Vue 3 + TypeScript + Vite)
- `src/` - 后端服务 (Python FastAPI)
- `server/` - 额外的服务模块

## 快速启动

### 1. 创建必要的数据目录
```bash
mkdir -p data/huggingface
mkdir -p data/sqlite_database
mkdir -p data/file_system
mkdir -p data/tmp
mkdir -p data/logs
```

### 2. 构建并启动服务
```bash
# 构建并启动所有服务
docker-compose up --build

# 后台运行
docker-compose up -d --build
```

### 3. 访问服务
- 前端界面: http://localhost:3000
- 后端API: http://localhost:8000
- 后端其他服务端口: 9890, 9899

## 数据持久化

以下目录会被映射到宿主机，确保数据持久化：

| 容器内路径 | 宿主机路径 | 说明 |
|-----------|-----------|------|
| `/opt/data/private/liuteng/huggingface` | `./data/huggingface` | HuggingFace模型缓存 |
| `/app/src/data/sqlite_database` | `./data/sqlite_database` | SQLite数据库文件 |
| `/app/src/data/file_system` | `./data/file_system` | 文件系统存储 |
| `/app/src/data/tmp` | `./data/tmp` | 临时数据目录 |
| `/app/src/logs` | `./data/logs` | 日志文件 |

## 配置说明

### 后端配置
- 主要配置文件: `src/conf/config.py` 和 `src/conf/config.yaml`
- 如需修改配置，可以直接编辑这些文件，重启容器即可生效

### 前端配置
- 前端使用相对路径访问API（如 `/files`、`/task`）
- nginx 负责将API请求代理到后端服务，无需额外配置

## 常用命令

```bash
# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs

# 查看特定服务日志
docker-compose logs frontend
docker-compose logs backend

# 停止服务
docker-compose down

# 重新构建并启动
docker-compose up --build

# 进入容器
docker-compose exec backend bash
docker-compose exec frontend sh
```

## 注意事项

1. **首次启动**: 第一次启动时需要下载大量依赖和模型，请耐心等待
2. **存储空间**: 确保有足够的磁盘空间存储模型和数据
3. **网络访问**: 某些服务需要访问外部API，确保网络通畅
4. **端口冲突**: 如果端口被占用，请修改 docker-compose.yml 中的端口映射

## 故障排除

### 后端启动失败
1. 检查Python依赖是否正确安装
2. 查看后端日志: `docker-compose logs backend`
3. 确保数据目录权限正确

### 前端无法访问后端
1. 检查网络配置
2. 确认后端服务已正常启动
3. 检查nginx代理配置

### 模型下载问题
1. 检查网络连接
2. 确认HuggingFace镜像地址配置正确
3. 手动下载模型到 `data/huggingface` 目录 