#!/bin/bash

echo "=== Neo4j 密码重置脚本 ==="

echo "1. 停止 Neo4j 服务..."
sudo neo4j stop

echo "2. 清除现有认证数据..."
sudo rm -rf /var/lib/neo4j/data/dbms/auth*

echo "3. 设置新密码..."
sudo neo4j-admin set-initial-password yang1209041527

echo "4. 启动 Neo4j 服务..."
sudo neo4j start

echo "5. 等待服务启动..."
sleep 10

echo "6. 检查服务状态..."
sudo neo4j status

echo ""
echo "=== 密码重置完成 ==="
echo "现在可以使用以下信息登录："
echo "URL: http://172.22.98.74:7474"
echo "用户名: neo4j"
echo "密码: yang1209041527"
echo ""
echo "如果还是无法登录，请尝试默认密码 'neo4j'"