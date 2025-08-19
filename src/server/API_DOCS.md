# 广诚CAD内容识别服务 API 文档

## 概述

本文档描述了广诚CAD内容识别服务的REST API接口规范，基于FastAPI框架构建，提供了完整的Swagger文档支持。

## 接口地址

- **服务地址**: `http://localhost:8000`
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`
- **OpenAPI Schema**: `http://localhost:8000/openapi.json`

## 主要功能模块

### 1. 文件管理 (`/files`)

| 接口 | 方法 | 描述 |
|------|------|------|
| `/files/` | GET | 获取文件列表 |
| `/files/create-folder` | POST | 创建文件夹 |
| `/files/upload` | POST | 上传文件 |
| `/files/{file_id}` | DELETE | 删除文件或文件夹 |

### 2. 任务管理 (`/task`)

| 接口 | 方法 | 描述 |
|------|------|------|
| `/task/` | GET | 获取任务列表 |
| `/task/create` | POST | 创建新任务 |
| `/task/{task_id}` | GET | 获取任务详情 |
| `/task/{task_id}` | DELETE | 删除任务 |
| `/task/{task_id}/startup` | POST | 启动任务 |
| `/task/{task_id}/stop` | POST | 停止任务 |
| `/task/{task_id}/update_result` | POST | 更新任务结果 |

### 3. 系统信息

| 接口 | 方法 | 描述 |
|------|------|------|
| `/` | GET | 系统首页信息 |
| `/health` | GET | 健康检查 |

## API 响应格式

所有API接口遵循统一的响应格式：

```json
{
  "code": 200,
  "msg": "success",
  "data": {}
}
```

- `code`: HTTP状态码
- `msg`: 响应消息
- `data`: 响应数据

## 使用示例

### 1. 上传文件并创建识别任务

#### 步骤1: 上传CAD文件
```bash
curl -X POST "http://localhost:8000/files/upload" \
     -H "Content-Type: multipart/form-data" \
     -F "parent_id=root" \
     -F "uploaded_file=@drawing.dwg"
```

#### 步骤2: 创建识别任务
```bash
curl -X POST "http://localhost:8000/task/create" \
     -H "Content-Type: application/json" \
     -d '{
       "task_name": "CAD图纸识别",
       "task_description": "识别CAD图纸中的文字和标注",
       "task_params": {"input_file": "drawing.dwg"},
       "task_level": 0
     }'
```

#### 步骤3: 启动任务
```bash
curl -X POST "http://localhost:8000/task/{task_id}/startup"
```

#### 步骤4: 查看任务进度
```bash
curl -X GET "http://localhost:8000/task/{task_id}"
```

## 错误处理

API使用标准HTTP状态码表示请求结果：

- `200`: 请求成功
- `400`: 请求参数错误
- `404`: 资源不存在
- `500`: 服务器内部错误

错误响应格式：
```json
{
  "detail": "错误描述信息"
}
```

## 数据模型

### 任务模型
```json
{
  "task_id": "task_20231201_001",
  "task_name": "CAD图纸识别任务",
  "task_description": "识别CAD图纸中的文字和标注信息",
  "task_params": {"input_file": "drawing.dwg"},
  "task_level": 0,
  "task_status": "completed",
  "task_progress": 100,
  "task_result": {"extracted_text": "示例文字"},
  "update_time": "2023-12-01 10:30:00",
  "create_time": "2023-12-01 10:00:00"
}
```

### 文件模型
```json
{
  "file_id": "file_20231201_001",
  "file_name": "drawing.dwg",
  "file_type": "dwg",
  "file_size": 1024000,
  "parent_id": "root",
  "file_path": "/uploads/drawing.dwg",
  "is_directory": false,
  "create_time": "2023-12-01 10:00:00",
  "update_time": "2023-12-01 10:00:00"
}
```

## 启动服务

```bash
cd /opt/data/private/liuteng/code/dev/gc-cad-cr-server
python src/server/start.py
```

服务启动后访问 `http://localhost:8000/docs` 查看完整的Swagger文档。

## 技术支持

如有问题请联系技术支持团队：support@guangcheng.com 