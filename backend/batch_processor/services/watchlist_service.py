#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自选股管理服务
"""
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, time
import psycopg2
from psycopg2.extras import RealDictCursor
import json

from ..config.batch_config import config
from ..models.watchlist import (
    WatchlistCreate, WatchlistUpdate, WatchlistResponse,
    WatchlistStats, WatchlistBatchTrigger
)

logger = logging.getLogger(__name__)

class WatchlistService:
    """自选股管理服务"""

    def __init__(self):
        self.db_config = config.database_config
        logger.info("自选股服务初始化完成")

    def _get_connection(self):
        """获取数据库连接"""
        if 'url' in self.db_config:
            return psycopg2.connect(self.db_config['url'])
        else:
            return psycopg2.connect(**self.db_config)

    async def create_watchlist(self, watchlist_data: WatchlistCreate) -> WatchlistResponse:
        """创建自选股列表"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # 检查同用户同名列表是否存在
            cursor.execute(
                "SELECT id FROM user_watchlists WHERE user_id = %s AND watchlist_name = %s AND is_active = true",
                (watchlist_data.user_id, watchlist_data.watchlist_name)
            )

            if cursor.fetchone():
                raise ValueError(f"用户 {watchlist_data.user_id} 已存在名为 '{watchlist_data.watchlist_name}' 的自选股列表")

            # 插入新的自选股列表
            insert_sql = """
                INSERT INTO user_watchlists
                (user_id, watchlist_name, description, stock_codes, priority_level,
                 auto_batch, data_types, schedule_time, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """

            cursor.execute(insert_sql, (
                watchlist_data.user_id,
                watchlist_data.watchlist_name,
                watchlist_data.description,
                watchlist_data.stock_codes,
                watchlist_data.priority_level,
                watchlist_data.auto_batch,
                watchlist_data.data_types,
                watchlist_data.schedule_time,
                True
            ))

            result = cursor.fetchone()
            conn.commit()
            cursor.close()
            conn.close()

            logger.info(f"创建自选股列表成功: {watchlist_data.watchlist_name} (用户: {watchlist_data.user_id})")
            return WatchlistResponse(**dict(result))

        except Exception as e:
            logger.error(f"创建自选股列表失败: {e}")
            raise

    async def get_user_watchlists(self, user_id: str, include_inactive: bool = False) -> List[WatchlistResponse]:
        """获取用户的所有自选股列表"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            where_clause = "WHERE user_id = %s"
            params = [user_id]

            if not include_inactive:
                where_clause += " AND is_active = true"

            sql = f"""
                SELECT * FROM user_watchlists
                {where_clause}
                ORDER BY priority_level DESC, created_at DESC
            """

            cursor.execute(sql, params)
            results = cursor.fetchall()

            cursor.close()
            conn.close()

            watchlists = [WatchlistResponse(**dict(row)) for row in results]
            logger.info(f"获取用户 {user_id} 的自选股列表: {len(watchlists)} 个")

            return watchlists

        except Exception as e:
            logger.error(f"获取用户自选股列表失败: {e}")
            raise

    async def get_watchlist_by_id(self, watchlist_id: int) -> Optional[WatchlistResponse]:
        """根据ID获取自选股列表"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            cursor.execute("SELECT * FROM user_watchlists WHERE id = %s", (watchlist_id,))
            result = cursor.fetchone()

            cursor.close()
            conn.close()

            if result:
                return WatchlistResponse(**dict(result))
            return None

        except Exception as e:
            logger.error(f"获取自选股列表失败 (ID: {watchlist_id}): {e}")
            raise

    async def update_watchlist(self, watchlist_id: int, update_data: WatchlistUpdate) -> Optional[WatchlistResponse]:
        """更新自选股列表"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # 构建更新字段
            update_fields = []
            params = []

            for field, value in update_data.dict(exclude_unset=True).items():
                if value is not None:
                    update_fields.append(f"{field} = %s")
                    params.append(value)

            if not update_fields:
                raise ValueError("没有提供更新字段")

            # 添加updated_at字段
            update_fields.append("updated_at = CURRENT_TIMESTAMP")
            params.append(watchlist_id)

            sql = f"""
                UPDATE user_watchlists
                SET {', '.join(update_fields)}
                WHERE id = %s
                RETURNING *
            """

            cursor.execute(sql, params)
            result = cursor.fetchone()

            if not result:
                raise ValueError(f"自选股列表不存在 (ID: {watchlist_id})")

            conn.commit()
            cursor.close()
            conn.close()

            logger.info(f"更新自选股列表成功 (ID: {watchlist_id})")
            return WatchlistResponse(**dict(result))

        except Exception as e:
            logger.error(f"更新自选股列表失败 (ID: {watchlist_id}): {e}")
            raise

    async def delete_watchlist(self, watchlist_id: int) -> bool:
        """删除自选股列表 (软删除)"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                "UPDATE user_watchlists SET is_active = false, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (watchlist_id,)
            )

            affected_rows = cursor.rowcount
            conn.commit()
            cursor.close()
            conn.close()

            if affected_rows > 0:
                logger.info(f"删除自选股列表成功 (ID: {watchlist_id})")
                return True
            else:
                logger.warning(f"自选股列表不存在 (ID: {watchlist_id})")
                return False

        except Exception as e:
            logger.error(f"删除自选股列表失败 (ID: {watchlist_id}): {e}")
            raise

    async def get_priority_watchlists(self, priority_level: int = None) -> List[WatchlistResponse]:
        """获取优先级批处理的自选股列表"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            where_clause = "WHERE is_active = true AND auto_batch = true"
            params = []

            if priority_level is not None:
                where_clause += " AND priority_level = %s"
                params.append(priority_level)

            sql = f"""
                SELECT * FROM user_watchlists
                {where_clause}
                ORDER BY priority_level DESC, schedule_time ASC
            """

            cursor.execute(sql, params)
            results = cursor.fetchall()

            cursor.close()
            conn.close()

            watchlists = [WatchlistResponse(**dict(row)) for row in results]
            logger.info(f"获取优先级批处理自选股列表: {len(watchlists)} 个 (优先级: {priority_level or '全部'})")

            return watchlists

        except Exception as e:
            logger.error(f"获取优先级自选股列表失败: {e}")
            raise

    async def get_scheduled_watchlists(self, current_time: time) -> List[WatchlistResponse]:
        """获取当前时间应该执行的自选股列表"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # 获取当前时间前后5分钟内的任务
            sql = """
                SELECT * FROM user_watchlists
                WHERE is_active = true
                  AND auto_batch = true
                  AND schedule_time BETWEEN %s - INTERVAL '5 minutes' AND %s + INTERVAL '5 minutes'
                ORDER BY priority_level DESC
            """

            cursor.execute(sql, (current_time, current_time))
            results = cursor.fetchall()

            cursor.close()
            conn.close()

            watchlists = [WatchlistResponse(**dict(row)) for row in results]
            logger.info(f"获取调度时间 {current_time} 的自选股列表: {len(watchlists)} 个")

            return watchlists

        except Exception as e:
            logger.error(f"获取调度自选股列表失败: {e}")
            raise

    async def update_watchlist_stats(self, watchlist_id: int, access_count: int = 1,
                                   avg_response_time: float = None, cache_hit_rate: float = None) -> bool:
        """更新自选股使用统计"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # 检查今日统计是否存在
            cursor.execute("""
                SELECT id FROM watchlist_usage_stats
                WHERE watchlist_id = %s AND date_recorded = CURRENT_DATE
            """, (watchlist_id,))

            existing = cursor.fetchone()

            if existing:
                # 更新现有统计
                update_sql = """
                    UPDATE watchlist_usage_stats
                    SET access_count = access_count + %s,
                        last_accessed = CURRENT_TIMESTAMP
                """
                params = [access_count]

                if avg_response_time is not None:
                    update_sql += ", avg_response_time = %s"
                    params.append(avg_response_time)

                if cache_hit_rate is not None:
                    update_sql += ", cache_hit_rate = %s"
                    params.append(cache_hit_rate)

                update_sql += " WHERE id = %s"
                params.append(existing[0])

                cursor.execute(update_sql, params)
            else:
                # 创建新统计记录
                # 先获取用户ID
                cursor.execute("SELECT user_id FROM user_watchlists WHERE id = %s", (watchlist_id,))
                user_result = cursor.fetchone()

                if not user_result:
                    raise ValueError(f"自选股列表不存在 (ID: {watchlist_id})")

                user_id = user_result[0]

                insert_sql = """
                    INSERT INTO watchlist_usage_stats
                    (watchlist_id, user_id, access_count, last_accessed, avg_response_time, cache_hit_rate)
                    VALUES (%s, %s, %s, CURRENT_TIMESTAMP, %s, %s)
                """

                cursor.execute(insert_sql, (watchlist_id, user_id, access_count, avg_response_time, cache_hit_rate))

            conn.commit()
            cursor.close()
            conn.close()

            logger.debug(f"更新自选股统计成功 (ID: {watchlist_id})")
            return True

        except Exception as e:
            logger.error(f"更新自选股统计失败 (ID: {watchlist_id}): {e}")
            raise

    async def get_watchlist_stats(self, watchlist_id: int, days: int = 30) -> List[WatchlistStats]:
        """获取自选股使用统计"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            sql = """
                SELECT * FROM watchlist_usage_stats
                WHERE watchlist_id = %s
                  AND date_recorded >= CURRENT_DATE - INTERVAL '%s days'
                ORDER BY date_recorded DESC
            """

            cursor.execute(sql, (watchlist_id, days))
            results = cursor.fetchall()

            cursor.close()
            conn.close()

            stats = [WatchlistStats(**dict(row)) for row in results]
            logger.info(f"获取自选股统计成功 (ID: {watchlist_id}, {days}天): {len(stats)} 条记录")

            return stats

        except Exception as e:
            logger.error(f"获取自选股统计失败 (ID: {watchlist_id}): {e}")
            raise

    async def get_all_stocks_for_batch(self) -> Dict[int, List[str]]:
        """获取所有需要批处理的股票，按优先级分组"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            sql = """
                SELECT priority_level, stock_codes, data_types
                FROM user_watchlists
                WHERE is_active = true AND auto_batch = true
                ORDER BY priority_level DESC
            """

            cursor.execute(sql)
            results = cursor.fetchall()

            cursor.close()
            conn.close()

            # 按优先级组织股票列表
            priority_stocks = {}
            for row in results:
                priority = row['priority_level']
                if priority not in priority_stocks:
                    priority_stocks[priority] = set()

                # 添加股票代码到对应优先级
                priority_stocks[priority].update(row['stock_codes'])

            # 转换为列表格式
            result = {priority: list(stocks) for priority, stocks in priority_stocks.items()}

            total_stocks = sum(len(stocks) for stocks in result.values())
            logger.info(f"获取批处理股票列表: {total_stocks} 只股票，{len(result)} 个优先级")

            return result

        except Exception as e:
            logger.error(f"获取批处理股票列表失败: {e}")
            raise