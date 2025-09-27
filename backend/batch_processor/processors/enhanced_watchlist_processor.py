#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强的自选股批处理处理器 - 集成完整日志记录
"""
import asyncio
import logging
import time
from typing import List, Dict, Any
from datetime import datetime
import sys
import os

# 添加父目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from enhanced_dashboard_api import ThreeTierDataService
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("无法导入ThreeTierDataService，将使用模拟实现")
    ThreeTierDataService = None

# 导入日志系统
from app.utils.logger import batch_logger, rag_logger, PrismLogger

from ..config.batch_config import config
from ..services.watchlist_service import WatchlistService
from ..models.batch_job import JobType, JobStatus, BatchJobCreate

logger = logging.getLogger(__name__)


class EnhancedWatchlistProcessor:
    """增强的自选股批处理处理器 - 集成日志记录"""

    def __init__(self):
        """初始化处理器"""
        self.watchlist_service = WatchlistService()

        # 初始化数据服务
        if ThreeTierDataService:
            self.data_service = ThreeTierDataService()
            logger.info("成功初始化ThreeTierDataService")
        else:
            self.data_service = None
            logger.warning("ThreeTierDataService不可用，将使用模拟模式")

        # 创建专用日志记录器
        self.batch_logger = PrismLogger("batch", "watchlist")

        logger.info("增强自选股批处理处理器初始化完成")

    async def process_single_watchlist(self, watchlist_id: int) -> Dict[str, Any]:
        """
        处理单个自选股列表

        Args:
            watchlist_id: 自选股列表ID

        Returns:
            处理结果统计
        """
        start_time = time.time()

        try:
            # 获取自选股列表
            watchlist = await self.watchlist_service.get_watchlist_by_id(watchlist_id)
            if not watchlist:
                raise ValueError(f"自选股列表 {watchlist_id} 不存在")

            logger.info(f"开始处理单个自选股列表: {watchlist.watchlist_name} (ID: {watchlist_id})")

            processed = 0
            success = 0
            failed = 0
            skipped = 0
            failed_items = []
            cache_hits = 0
            cache_misses = 0

            # 处理每只股票的每种数据类型
            for stock_code in watchlist.stock_codes:
                for data_type in watchlist.data_types:
                    try:
                        # 调用数据服务
                        if self.data_service:
                            result = await self._call_data_service(stock_code, data_type)

                            if result.get('cache_hit'):
                                cache_hits += 1
                            else:
                                cache_misses += 1

                            if result.get('success'):
                                success += 1
                            else:
                                failed += 1
                                failed_items.append(f"{stock_code}-{data_type}")
                        else:
                            # 模拟处理
                            await asyncio.sleep(0.1)
                            success += 1
                            cache_misses += 1

                        processed += 1

                    except Exception as e:
                        logger.error(f"处理 {stock_code}-{data_type} 失败: {e}")
                        failed += 1
                        failed_items.append(f"{stock_code}-{data_type}: {str(e)}")
                        processed += 1

            execution_time = time.time() - start_time

            # 计算成功率
            success_rate = success / processed if processed > 0 else 0

            # 记录批处理日志
            self.batch_logger.log_batch_execution(
                process_name=f"single_watchlist_{watchlist_id}",
                data_source="watchlist_stocks",
                input_count=len(watchlist.stock_codes) * len(watchlist.data_types),
                output_count=success,
                rag_stored_count=0,  # 这个处理器不直接写RAG
                execution_time=execution_time,
                success_rate=success_rate,
                cache_hits=cache_hits,
                cache_misses=cache_misses,
                error_details=failed_items
            )

            result = {
                'processed': processed,
                'success': success,
                'failed': failed,
                'skipped': skipped,
                'failed_items': failed_items,
                'cache_hits': cache_hits,
                'cache_misses': cache_misses
            }

            logger.info(f"单个列表处理完成: {result}")
            return result

        except Exception as e:
            execution_time = time.time() - start_time

            # 记录错误日志
            self.batch_logger.log_batch_execution(
                process_name=f"single_watchlist_{watchlist_id}",
                data_source="watchlist_stocks",
                input_count=0,
                output_count=0,
                rag_stored_count=0,
                execution_time=execution_time,
                success_rate=0,
                error_details=[str(e)]
            )

            logger.error(f"处理自选股列表 {watchlist_id} 失败: {e}")
            raise

    async def process_priority_watchlists(self, priority_level: int) -> Dict[str, Any]:
        """
        按优先级批量处理自选股列表

        Args:
            priority_level: 优先级级别

        Returns:
            批量处理结果
        """
        start_time = time.time()

        try:
            # 获取指定优先级的自选股列表
            watchlists = await self.watchlist_service.get_priority_watchlists(priority_level)

            if not watchlists:
                logger.info(f"优先级 {priority_level} 没有自选股列表")
                return {"success": 0, "failed": 0}

            # 获取涉及的所有股票
            all_stocks = set()
            for watchlist in watchlists:
                all_stocks.update(watchlist.stock_codes)

            logger.info(f"开始处理优先级 {priority_level} 的批处理: {len(watchlists)} 个列表, {len(all_stocks)} 只股票")

            total_success = 0
            total_failed = 0
            all_errors = []

            # 处理每个自选股列表
            for watchlist in watchlists:
                try:
                    result = await self.process_single_watchlist(watchlist.id)
                    total_success += result['success']
                    total_failed += result['failed']
                    if result['failed_items']:
                        all_errors.extend(result['failed_items'])

                except Exception as e:
                    logger.error(f"处理自选股列表 {watchlist.id} 失败: {e}")
                    total_failed += 1
                    all_errors.append(f"Watchlist {watchlist.id}: {str(e)}")

            execution_time = time.time() - start_time
            success_rate = total_success / (total_success + total_failed) if (total_success + total_failed) > 0 else 0

            # 记录优先级批处理日志
            self.batch_logger.log_batch_execution(
                process_name=f"priority_batch_{priority_level}",
                data_source="priority_watchlists",
                input_count=len(watchlists),
                output_count=total_success,
                rag_stored_count=0,
                execution_time=execution_time,
                success_rate=success_rate,
                error_details=all_errors
            )

            logger.info(f"自选股批处理完成: 成功 {total_success}, 失败 {total_failed}, 耗时 {execution_time:.2f}秒")

            return {
                "success": total_success,
                "failed": total_failed,
                "execution_time": execution_time,
                "watchlists_processed": len(watchlists),
                "stocks_involved": len(all_stocks)
            }

        except Exception as e:
            execution_time = time.time() - start_time

            # 记录错误日志
            self.batch_logger.log_batch_execution(
                process_name=f"priority_batch_{priority_level}",
                data_source="priority_watchlists",
                input_count=0,
                output_count=0,
                rag_stored_count=0,
                execution_time=execution_time,
                success_rate=0,
                error_details=[str(e)]
            )

            logger.error(f"优先级 {priority_level} 批处理失败: {e}")
            raise

    async def get_batch_summary(self) -> Dict[str, Any]:
        """
        获取批处理执行摘要

        Returns:
            批处理摘要信息
        """
        try:
            watchlists = await self.watchlist_service.get_priority_watchlists()

            total_watchlists = len(watchlists)
            total_stocks = len(set(
                stock_code
                for watchlist in watchlists
                for stock_code in watchlist.stock_codes
            ))

            # 统计数据类型分布
            data_type_count = {}
            priority_distribution = {}

            total_operations = 0

            for watchlist in watchlists:
                # 优先级分布
                priority = watchlist.priority_level
                if priority not in priority_distribution:
                    priority_distribution[priority] = 0
                priority_distribution[priority] += 1

                # 数据类型分布
                for data_type in watchlist.data_types:
                    if data_type not in data_type_count:
                        data_type_count[data_type] = 0
                    data_type_count[data_type] += 1

                # 计算总操作数
                total_operations += len(watchlist.stock_codes) * len(watchlist.data_types)

            summary = {
                'total_watchlists': total_watchlists,
                'total_stocks': total_stocks,
                'total_operations': total_operations,
                'priority_distribution': priority_distribution,
                'data_type_distribution': data_type_count,
                'timestamp': datetime.now()
            }

            logger.info(f"批处理摘要: {summary}")
            return summary

        except Exception as e:
            logger.error(f"获取批处理摘要失败: {e}")
            raise

    async def _call_data_service(self, stock_code: str, data_type: str) -> Dict[str, Any]:
        """
        调用数据服务获取数据

        Args:
            stock_code: 股票代码
            data_type: 数据类型

        Returns:
            数据服务调用结果
        """
        try:
            if not self.data_service:
                # 模拟调用
                await asyncio.sleep(0.1)
                return {
                    'success': True,
                    'cache_hit': False,
                    'data_count': 1
                }

            # 调用实际的数据服务
            method_map = {
                'financial': 'get_financial_data',
                'announcements': 'get_announcements_data',
                'shareholders': 'get_shareholders_data',
                'longhubang': 'get_longhubang_data'
            }

            method_name = method_map.get(data_type)
            if not method_name:
                raise ValueError(f"不支持的数据类型: {data_type}")

            method = getattr(self.data_service, method_name)
            result = await method(stock_code)

            return {
                'success': result is not None,
                'cache_hit': getattr(result, 'cache_hit', False),
                'data_count': 1 if result else 0
            }

        except Exception as e:
            logger.error(f"调用数据服务失败 {stock_code}-{data_type}: {e}")
            return {
                'success': False,
                'cache_hit': False,
                'data_count': 0,
                'error': str(e)
            }


# 创建全局实例
enhanced_watchlist_processor = EnhancedWatchlistProcessor()