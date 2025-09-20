#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据版本管理器
实现"前一版本非活性，新版信息活性"的核心功能
"""
import logging
import hashlib
import json
import uuid
from typing import Optional, Dict, List, Any
from datetime import datetime
import psycopg2
from psycopg2.extras import RealDictCursor

from ..config.batch_config import config

logger = logging.getLogger(__name__)

class VersionManager:
    """数据版本管理服务"""

    def __init__(self):
        self.db_config = config.database_config
        logger.info("版本管理器初始化完成")

    def _get_connection(self):
        """获取数据库连接"""
        if 'url' in self.db_config:
            return psycopg2.connect(self.db_config['url'])
        else:
            return psycopg2.connect(**self.db_config)

    def calculate_data_hash(self, data: Dict) -> str:
        """计算数据哈希值用于版本控制"""
        try:
            # 将数据转换为排序后的JSON字符串，确保一致性
            json_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
            # 使用SHA256计算哈希
            return hashlib.sha256(json_str.encode('utf-8')).hexdigest()
        except Exception as e:
            logger.error(f"计算数据哈希失败: {e}")
            raise

    async def create_new_version(self, stock_code: str, data_type: str, source_data: Dict) -> str:
        """
        创建新数据版本

        Args:
            stock_code: 股票代码
            data_type: 数据类型 (financial, announcements, shareholders, longhubang)
            source_data: 源数据

        Returns:
            version_id: 新版本UUID
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # 生成新版本ID和数据哈希
            version_id = str(uuid.uuid4())
            data_hash = self.calculate_data_hash(source_data)

            # 检查是否已存在相同哈希的版本
            cursor.execute("""
                SELECT version_id FROM rag_data_versions
                WHERE stock_code = %s AND data_type = %s AND data_hash = %s
                ORDER BY created_at DESC LIMIT 1
            """, (stock_code, data_type, data_hash))

            existing_version = cursor.fetchone()
            if existing_version:
                logger.info(f"数据未变化，跳过创建新版本: {stock_code}-{data_type}")
                cursor.close()
                conn.close()
                return existing_version['version_id']

            # 插入新版本记录
            insert_sql = """
                INSERT INTO rag_data_versions
                (stock_code, data_type, version_id, data_hash, vector_status,
                 source_data, embedding_model, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING version_id
            """

            cursor.execute(insert_sql, (
                stock_code,
                data_type,
                version_id,
                data_hash,
                'pending',  # 初始状态为pending
                json.dumps(source_data, ensure_ascii=False),
                'bge-large-zh-v1.5',  # 默认embedding模型
                datetime.now()
            ))

            result = cursor.fetchone()
            conn.commit()
            cursor.close()
            conn.close()

            logger.info(f"创建新版本成功: {stock_code}-{data_type}, version_id={version_id}")
            return result['version_id']

        except Exception as e:
            logger.error(f"创建新版本失败: {stock_code}-{data_type}, {e}")
            raise

    async def activate_version(self, version_id: str) -> bool:
        """
        激活指定版本
        原子性操作：先停用旧版本，再激活新版本
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # 开始事务
            cursor.execute("BEGIN")

            # 获取版本信息
            cursor.execute("""
                SELECT stock_code, data_type FROM rag_data_versions
                WHERE version_id = %s
            """, (version_id,))

            version_info = cursor.fetchone()
            if not version_info:
                raise ValueError(f"版本不存在: {version_id}")

            stock_code = version_info['stock_code']
            data_type = version_info['data_type']

            # 停用同股票同数据类型的所有旧版本
            deprecated_count = await self._deprecate_old_versions_in_transaction(
                cursor, stock_code, data_type, version_id
            )

            # 激活新版本
            cursor.execute("""
                UPDATE rag_data_versions
                SET activated_at = %s, vector_status = 'active'
                WHERE version_id = %s
            """, (datetime.now(), version_id))

            affected_rows = cursor.rowcount
            if affected_rows == 0:
                raise ValueError(f"版本激活失败: {version_id}")

            # 提交事务
            cursor.execute("COMMIT")
            cursor.close()
            conn.close()

            logger.info(f"版本激活成功: {version_id}, 停用旧版本: {deprecated_count} 个")
            return True

        except Exception as e:
            logger.error(f"版本激活失败: {version_id}, {e}")
            # 回滚事务
            try:
                cursor.execute("ROLLBACK")
                cursor.close()
                conn.close()
            except:
                pass
            raise

    async def _deprecate_old_versions_in_transaction(self, cursor, stock_code: str, data_type: str, exclude_version: str) -> int:
        """在事务中停用旧版本"""
        cursor.execute("""
            UPDATE rag_data_versions
            SET deprecated_at = %s, vector_status = 'deprecated'
            WHERE stock_code = %s AND data_type = %s
              AND version_id != %s AND deprecated_at IS NULL
        """, (datetime.now(), stock_code, data_type, exclude_version))

        return cursor.rowcount

    async def deprecate_old_versions(self, stock_code: str, data_type: str, exclude_version: str) -> int:
        """
        停用旧版本
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE rag_data_versions
                SET deprecated_at = %s, vector_status = 'deprecated'
                WHERE stock_code = %s AND data_type = %s
                  AND version_id != %s AND deprecated_at IS NULL
            """, (datetime.now(), stock_code, data_type, exclude_version))

            affected_rows = cursor.rowcount
            conn.commit()
            cursor.close()
            conn.close()

            logger.info(f"停用旧版本成功: {stock_code}-{data_type}, 影响行数: {affected_rows}")
            return affected_rows

        except Exception as e:
            logger.error(f"停用旧版本失败: {stock_code}-{data_type}, {e}")
            raise

    async def get_active_version(self, stock_code: str, data_type: str) -> Optional[Dict]:
        """获取当前活跃版本"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("""
                SELECT * FROM rag_data_versions
                WHERE stock_code = %s AND data_type = %s
                  AND deprecated_at IS NULL
                  AND vector_status = 'active'
                ORDER BY activated_at DESC
                LIMIT 1
            """, (stock_code, data_type))

            result = cursor.fetchone()
            cursor.close()
            conn.close()

            if result:
                return dict(result)
            return None

        except Exception as e:
            logger.error(f"获取活跃版本失败: {stock_code}-{data_type}, {e}")
            raise

    async def get_version_by_id(self, version_id: str) -> Optional[Dict]:
        """根据ID获取版本信息"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("""
                SELECT * FROM rag_data_versions
                WHERE version_id = %s
            """, (version_id,))

            result = cursor.fetchone()
            cursor.close()
            conn.close()

            if result:
                return dict(result)
            return None

        except Exception as e:
            logger.error(f"获取版本信息失败: {version_id}, {e}")
            raise

    async def update_vector_status(self, version_id: str, status: str, chunk_count: int = 0, vector_metadata: Dict = None) -> bool:
        """更新版本的向量状态"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            update_fields = ["vector_status = %s"]
            params = [status]

            if chunk_count > 0:
                update_fields.append("chunk_count = %s")
                params.append(chunk_count)

            if vector_metadata:
                update_fields.append("vector_metadata = %s")
                params.append(json.dumps(vector_metadata, ensure_ascii=False))

            params.append(version_id)

            sql = f"""
                UPDATE rag_data_versions
                SET {', '.join(update_fields)}
                WHERE version_id = %s
            """

            cursor.execute(sql, params)
            affected_rows = cursor.rowcount
            conn.commit()
            cursor.close()
            conn.close()

            logger.info(f"更新向量状态成功: {version_id}, 状态: {status}")
            return affected_rows > 0

        except Exception as e:
            logger.error(f"更新向量状态失败: {version_id}, {e}")
            raise

    async def get_pending_versions(self, limit: int = 100) -> List[Dict]:
        """获取待处理的版本列表"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("""
                SELECT * FROM rag_data_versions
                WHERE vector_status = 'pending'
                ORDER BY created_at ASC
                LIMIT %s
            """, (limit,))

            results = cursor.fetchall()
            cursor.close()
            conn.close()

            return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"获取待处理版本失败: {e}")
            raise

    async def cleanup_deprecated_versions(self, days_old: int = 30) -> int:
        """清理过期的已停用版本"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # 删除超过指定天数的已停用版本
            cursor.execute("""
                DELETE FROM rag_data_versions
                WHERE vector_status = 'deprecated'
                  AND deprecated_at < CURRENT_TIMESTAMP - INTERVAL '%s days'
            """, (days_old,))

            deleted_count = cursor.rowcount
            conn.commit()
            cursor.close()
            conn.close()

            logger.info(f"清理过期版本成功: 删除 {deleted_count} 条记录")
            return deleted_count

        except Exception as e:
            logger.error(f"清理过期版本失败: {e}")
            raise

    async def get_version_history(self, stock_code: str, data_type: str, limit: int = 10) -> List[Dict]:
        """获取版本历史"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("""
                SELECT version_id, data_hash, vector_status, chunk_count,
                       created_at, activated_at, deprecated_at
                FROM rag_data_versions
                WHERE stock_code = %s AND data_type = %s
                ORDER BY created_at DESC
                LIMIT %s
            """, (stock_code, data_type, limit))

            results = cursor.fetchall()
            cursor.close()
            conn.close()

            return [dict(row) for row in results]

        except Exception as e:
            logger.error(f"获取版本历史失败: {stock_code}-{data_type}, {e}")
            raise

    async def get_version_stats(self) -> Dict[str, Any]:
        """获取版本统计信息"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # 按状态统计
            cursor.execute("""
                SELECT vector_status, COUNT(*) as count
                FROM rag_data_versions
                GROUP BY vector_status
            """)
            status_stats = {row['vector_status']: row['count'] for row in cursor.fetchall()}

            # 按数据类型统计
            cursor.execute("""
                SELECT data_type, COUNT(*) as count
                FROM rag_data_versions
                WHERE deprecated_at IS NULL
                GROUP BY data_type
            """)
            type_stats = {row['data_type']: row['count'] for row in cursor.fetchall()}

            # 按股票统计
            cursor.execute("""
                SELECT stock_code, COUNT(*) as count
                FROM rag_data_versions
                WHERE deprecated_at IS NULL
                GROUP BY stock_code
                ORDER BY count DESC
                LIMIT 10
            """)
            stock_stats = {row['stock_code']: row['count'] for row in cursor.fetchall()}

            cursor.close()
            conn.close()

            return {
                "status_distribution": status_stats,
                "data_type_distribution": type_stats,
                "top_stocks": stock_stats,
                "generated_at": datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"获取版本统计失败: {e}")
            raise