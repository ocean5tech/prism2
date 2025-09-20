#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批处理系统数据库初始化脚本
"""
import psycopg2
import os
import sys
from pathlib import Path

def create_batch_tables():
    """创建批处理系统数据表"""

    # 数据库连接配置
    db_config = {
        'host': 'localhost',
        'port': 5432,
        'database': 'prism2',
        'user': 'prism2',
        'password': 'prism2_secure_password'
    }

    # 读取SQL脚本
    sql_file = Path(__file__).parent / "create_batch_tables.sql"

    try:
        with open(sql_file, 'r', encoding='utf-8') as f:
            sql_script = f.read()

        # 连接数据库
        print("正在连接数据库...")
        conn = psycopg2.connect(**db_config)
        conn.autocommit = True
        cursor = conn.cursor()

        # 执行SQL脚本
        print("正在执行数据表创建脚本...")
        cursor.execute(sql_script)

        # 验证表创建
        print("正在验证表创建结果...")
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            AND table_name IN ('user_watchlists', 'rag_data_versions', 'batch_jobs', 'batch_performance_metrics')
            ORDER BY table_name
        """)

        tables = cursor.fetchall()
        print(f"成功创建 {len(tables)} 个批处理表:")
        for table in tables:
            print(f"  ✅ {table[0]}")

        # 检查初始数据
        cursor.execute("SELECT COUNT(*) FROM user_watchlists WHERE user_id = 'test_user_001'")
        test_count = cursor.fetchone()[0]
        print(f"插入测试数据: {test_count} 条自选股记录")

        cursor.close()
        conn.close()

        print("\n🎉 批处理系统数据库初始化完成!")
        return True

    except Exception as e:
        print(f"❌ 数据库初始化失败: {e}")
        return False

def verify_database_connection():
    """验证数据库连接"""
    try:
        conn = psycopg2.connect(
            host='localhost',
            port=5432,
            database='prism2',
            user='prism2',
            password='prism2_secure_password'
        )
        cursor = conn.cursor()
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        print(f"✅ 数据库连接成功: {version}")
        cursor.close()
        conn.close()
        return True
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Prism2 批处理系统数据库初始化")
    print("=" * 50)

    # 验证数据库连接
    if not verify_database_connection():
        print("\n请确保PostgreSQL服务正在运行且配置正确")
        sys.exit(1)

    # 创建表
    if create_batch_tables():
        print("\n数据库初始化成功! 现在可以启动批处理服务。")
    else:
        print("\n数据库初始化失败! 请检查错误信息。")
        sys.exit(1)