#!/bin/bash

echo "=== 修改 Neo4j 配置以允许外部访问 ==="

# 备份原始配置
echo "1. 备份原始配置..."
sudo cp /etc/neo4j/neo4j.conf /etc/neo4j/neo4j.conf.backup

# 修改监听地址
echo "2. 修改监听地址..."
sudo sed -i 's/#dbms.connector.bolt.listen_address=:7687/dbms.connector.bolt.listen_address=0.0.0.0:7687/' /etc/neo4j/neo4j.conf
sudo sed -i 's/#dbms.connector.http.listen_address=:7474/dbms.connector.http.listen_address=0.0.0.0:7474/' /etc/neo4j/neo4j.conf

# 重启 Neo4j
echo "3. 重启 Neo4j..."
sudo neo4j restart

echo "4. 等待服务启动..."
sleep 5

# 检查状态
echo "5. 检查服务状态..."
sudo neo4j status

echo ""
echo "=== 配置完成 ==="
echo "现在可以通过以下地址访问："
echo "HTTP: http://172.22.98.74:7474"
echo "Bolt: bolt://172.22.98.74:7687"
echo "用户名: neo4j"
echo "密码: yang1209041527"