#!/bin/bash

echo "正在连接到 PostgreSQL 并安装 pgvector..."

# 连接到 PostgreSQL 并执行 SQL 命令
PGPASSWORD=searchforrag psql -h 117.72.54.192 -p 5432 -U searchforrag -d searchforrag -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 验证安装
echo "验证 pgvector 扩展..."
PGPASSWORD=searchforrag psql -h 117.72.54.192 -p 5432 -U searchforrag -d searchforrag -c "SELECT * FROM pg_extension WHERE extname = 'vector';"

echo "完成！"