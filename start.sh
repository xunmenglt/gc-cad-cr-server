#!/bin/bash

# 广诚CAD内容识别系统 Docker 启动脚本

echo "正在启动广诚CAD内容识别系统..."

# 创建必要的数据目录
echo "创建数据目录..."
mkdir -p data/huggingface
mkdir -p data/sqlite_database
mkdir -p data/file_system
mkdir -p data/tmp
mkdir -p data/logs

# 设置目录权限
chmod -R 755 data/

echo "数据目录创建完成"

# 构建并启动Docker服务
echo "构建并启动Docker容器..."
docker-compose up --build -d

# 检查服务状态
echo "检查服务状态..."
sleep 5
docker-compose ps

echo ""
echo "启动完成！"
echo ""
echo "服务访问地址:"
echo "   前端界面: http://localhost:3000"
echo "   后端API:  http://localhost:8000"
echo "   API文档:  http://localhost:8000/docs"
echo ""
echo "查看日志:"
echo "   docker-compose logs frontend"
echo "   docker-compose logs backend"
echo ""
echo "停止服务:"
echo "   docker-compose down" 