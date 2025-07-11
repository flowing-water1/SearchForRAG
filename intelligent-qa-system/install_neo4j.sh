#!/bin/bash

echo "=== Neo4j 安装和启动脚本 ==="

# 1. 检查 Docker 是否安装
if ! command -v docker &> /dev/null; then
    echo "❌ Docker 未安装，正在安装..."
    
    # 安装 Docker
    curl -fsSL https://get.docker.com -o get-docker.sh
    sh get-docker.sh
    
    # 启动 Docker 服务
    systemctl start docker
    systemctl enable docker
    
    echo "✅ Docker 安装完成"
else
    echo "✅ Docker 已安装"
fi

# 2. 创建 Neo4j 数据目录
echo "创建 Neo4j 数据目录..."
mkdir -p $HOME/neo4j/data
mkdir -p $HOME/neo4j/logs
mkdir -p $HOME/neo4j/import
mkdir -p $HOME/neo4j/plugins

# 3. 启动 Neo4j 容器
echo "启动 Neo4j 容器..."
docker run \
    --name neo4j \
    -p 7474:7474 -p 7687:7687 \
    -d \
    -v $HOME/neo4j/data:/data \
    -v $HOME/neo4j/logs:/logs \
    -v $HOME/neo4j/import:/var/lib/neo4j/import \
    -v $HOME/neo4j/plugins:/plugins \
    --env NEO4J_AUTH=neo4j/password \
    neo4j:latest

# 4. 等待 Neo4j 启动
echo "等待 Neo4j 启动..."
sleep 30

# 5. 检查 Neo4j 状态
echo "检查 Neo4j 状态..."
docker ps | grep neo4j

echo ""
echo "=== Neo4j 启动完成 ==="
echo "Web 界面: http://localhost:7474"
echo "用户名: neo4j"
echo "密码: password"
echo ""
echo "如果需要停止 Neo4j:"
echo "docker stop neo4j"
echo ""
echo "如果需要重启 Neo4j:"
echo "docker start neo4j"