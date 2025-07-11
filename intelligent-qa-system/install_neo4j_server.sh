#!/bin/bash

echo "=== 在 Linux 服务器上安装 Neo4j ==="

# 1. 更新包列表
apt-get update

# 2. 安装 Java（Neo4j 需要）
apt-get install -y openjdk-11-jdk

# 3. 添加 Neo4j 仓库
wget -O - https://debian.neo4j.com/neotechnology.gpg.key | apt-key add -
echo 'deb https://debian.neo4j.com stable 4.4' > /etc/apt/sources.list.d/neo4j.list

# 4. 更新包列表并安装 Neo4j
apt-get update
apt-get install -y neo4j=1:4.4.0

# 5. 启动 Neo4j
systemctl start neo4j
systemctl enable neo4j

# 6. 设置初始密码
neo4j-admin set-initial-password password

echo "✅ Neo4j 安装完成"
echo "Web 界面: http://your-server-ip:7474"
echo "用户名: neo4j"
echo "密码: password"