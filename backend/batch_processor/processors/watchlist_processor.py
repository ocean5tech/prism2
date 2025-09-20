#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自选股批处理处理器
复用现有的ThreeTierDataService进行数据预热
"""
import asyncio
import logging
import time
from typing import List, Dict, Any
from datetime import datetime
import sys
import os

# 添加父目录到路径，以便导入现有的ThreeTierDataService
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from enhanced_dashboard_api import ThreeTierDataService
except ImportError:
    logger = logging.getLogger(__name__)
    logger.warning("无法导入ThreeTierDataService，将使用模拟实现")
    ThreeTierDataService = None

from ..config.batch_config import config
from ..services.watchlist_service import WatchlistService
from ..models.batch_job import JobType, JobStatus, BatchJobCreate

logger = logging.getLogger(__name__)

class WatchlistProcessor:
    """自选股批处理处理器"""

    def __init__(self):
        self.watchlist_service = WatchlistService()
        self.data_service = None
        self.batch_settings = config.batch_settings

        # 初始化三层数据服务
        self._init_data_service()

        logger.info("自选股批处理处理器初始化完成")

    def _init_data_service(self):
        """初始化数据服务"""
        try:
            if ThreeTierDataService:
                self.data_service = ThreeTierDataService()
                logger.info("成功初始化ThreeTierDataService")
            else:
                logger.warning("ThreeTierDataService不可用，使用模拟模式")
        except Exception as e:
            logger.error(f"初始化ThreeTierDataService失败: {e}")
            self.data_service = None

    async def process_watchlist_batch(self, priority_level: int = None, force_refresh: bool = False) -> Dict[str, Any]:
        """处理指定优先级的自选股批处理"""
        start_time = time.time()
        result = {
            "priority_level": priority_level,
            "start_time": datetime.now(),
            "total_watchlists": 0,
            "total_stocks": 0,
            "processed_stocks": 0,
            "success_count": 0,
            "failed_count": 0,
            "skipped_count": 0,
            "processing_time": 0,
            "failed_items": [],
            "cache_hits": 0,
            "cache_misses": 0
        }

        try:
            # 获取指定优先级的自选股列表
            watchlists = await self.watchlist_service.get_priority_watchlists(priority_level)
            result["total_watchlists"] = len(watchlists)

            if not watchlists:
                logger.info(f"没有找到优先级 {priority_level} 的自选股列表")
                return result

            # 收集所有需要处理的股票
            stocks_to_process = {}  # {stock_code: set(data_types)}

            for watchlist in watchlists:
                for stock_code in watchlist.stock_codes:
                    if stock_code not in stocks_to_process:
                        stocks_to_process[stock_code] = set()
                    stocks_to_process[stock_code].update(watchlist.data_types)

            result["total_stocks"] = len(stocks_to_process)
            logger.info(f"开始处理优先级 {priority_level} 的批处理: {len(watchlists)} 个列表, {len(stocks_to_process)} 只股票")

            # 批量处理股票数据
            batch_size = self.batch_settings.get('max_stocks_per_batch', 20)
            stock_list = list(stocks_to_process.items())

            for i in range(0, len(stock_list), batch_size):
                batch = stock_list[i:i + batch_size]
                batch_result = await self._process_stock_batch(batch, force_refresh)

                # 累加结果
                result["processed_stocks"] += batch_result["processed"]
                result["success_count"] += batch_result["success"]
                result["failed_count"] += batch_result["failed"]
                result["skipped_count"] += batch_result["skipped"]
                result["failed_items"].extend(batch_result["failed_items"])
                result["cache_hits"] += batch_result["cache_hits"]
                result["cache_misses"] += batch_result["cache_misses"]

                # 批次间延迟，避免过度负载
                if i + batch_size < len(stock_list):
                    await asyncio.sleep(1)

            # 更新自选股使用统计
            await self._update_watchlist_stats(watchlists, result)

        except Exception as e:
            logger.error(f"处理自选股批处理失败: {e}")
            result["failed_count"] += 1
            result["failed_items"].append({"error": str(e), "type": "batch_processing"})

        finally:
            result["processing_time"] = time.time() - start_time
            result["end_time"] = datetime.now()

        logger.info(f"自选股批处理完成: 成功 {result['success_count']}, 失败 {result['failed_count']}, 耗时 {result['processing_time']:.2f}秒")
        return result

    async def _process_stock_batch(self, stock_batch: List[tuple], force_refresh: bool = False) -> Dict[str, Any]:
        """处理股票批次"""
        batch_result = {
            "processed": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "failed_items": [],
            "cache_hits": 0,
            "cache_misses": 0
        }

        for stock_code, data_types in stock_batch:
            for data_type in data_types:
                try:
                    batch_result["processed"] += 1

                    # 调用现有的三层数据服务
                    if self.data_service:
                        response = await self._call_existing_api(stock_code, data_type, force_refresh)

                        if response and response.get("success"):
                            batch_result["success"] += 1

                            # 统计缓存命中情况
                            cache_info = response.get("cache_info", {})
                            if any("缓存命中" in str(info) for info in cache_info.values()):
                                batch_result["cache_hits"] += 1
                            else:
                                batch_result["cache_misses"] += 1
                        else:
                            batch_result["failed"] += 1
                            batch_result["failed_items"].append({
                                "stock_code": stock_code,
                                "data_type": data_type,
                                "error": "API调用失败"
                            })
                    else:
                        # 模拟处理模式
                        batch_result["skipped"] += 1
                        logger.debug(f"模拟处理: {stock_code} - {data_type}")

                except Exception as e:
                    batch_result["failed"] += 1
                    batch_result["failed_items"].append({
                        "stock_code": stock_code,
                        "data_type": data_type,
                        "error": str(e)
                    })
                    logger.error(f"处理股票数据失败 {stock_code}-{data_type}: {e}")

                # 限制处理频率，避免过度负载AKShare
                await asyncio.sleep(0.1)

        return batch_result

    async def _call_existing_api(self, stock_code: str, data_type: str, force_refresh: bool = False) -> Dict[str, Any]:
        """调用现有的Dashboard API获取数据"""
        try:
            if not self.data_service:
                return None

            # 构建请求数据
            request_data = {
                "stock_code": stock_code,
                "data_types": [data_type],
                "kline_period": "daily",
                "kline_days": 60,
                "news_days": 7
            }

            # 如果强制刷新，清除缓存
            if force_refresh:
                cache_key = self.data_service.get_cache_key(data_type, stock_code)
                try:
                    self.data_service.redis_client.delete(cache_key)
                except:
                    pass

            # 获取数据（使用现有的三层架构）
            result = await self._get_data_via_three_tier(stock_code, data_type)

            return {
                "success": True,
                "stock_code": stock_code,
                "data_type": data_type,
                "data": result,
                "cache_info": {"source": "batch_processing"},
                "timestamp": datetime.now()
            }

        except Exception as e:
            logger.error(f"调用现有API失败 {stock_code}-{data_type}: {e}")
            return {
                "success": False,
                "error": str(e),
                "stock_code": stock_code,
                "data_type": data_type
            }

    async def _get_data_via_three_tier(self, stock_code: str, data_type: str) -> Any:
        """通过三层架构获取数据"""
        try:
            # 使用ThreeTierDataService的统一get_data方法
            if hasattr(self.data_service, 'get_data'):
                result = self.data_service.get_data(data_type, stock_code)
                return result
            else:
                logger.warning(f"ThreeTierDataService没有get_data方法")
                return None

        except Exception as e:
            logger.error(f"三层架构数据获取失败: {e}")
            raise

    async def _update_watchlist_stats(self, watchlists: List, result: Dict[str, Any]):
        """更新自选股使用统计"""
        try:
            for watchlist in watchlists:
                # 计算该列表相关的统计
                stock_count = len(watchlist.stock_codes)
                data_type_count = len(watchlist.data_types)
                expected_operations = stock_count * data_type_count

                # 计算缓存命中率
                total_operations = result["cache_hits"] + result["cache_misses"]
                cache_hit_rate = result["cache_hits"] / total_operations if total_operations > 0 else 0

                # 计算平均响应时间（基于总时间和操作数）
                avg_response_time = result["processing_time"] / max(result["processed_stocks"], 1)

                await self.watchlist_service.update_watchlist_stats(
                    watchlist_id=watchlist.id,
                    access_count=expected_operations,
                    avg_response_time=avg_response_time,
                    cache_hit_rate=cache_hit_rate
                )

        except Exception as e:
            logger.error(f"更新自选股统计失败: {e}")

    async def process_single_watchlist(self, watchlist_id: int, force_refresh: bool = False) -> Dict[str, Any]:
        """处理单个自选股列表"""
        try:
            watchlist = await self.watchlist_service.get_watchlist_by_id(watchlist_id)
            if not watchlist:
                raise ValueError(f"自选股列表不存在 (ID: {watchlist_id})")

            if not watchlist.is_active:
                raise ValueError(f"自选股列表已停用 (ID: {watchlist_id})")

            logger.info(f"开始处理单个自选股列表: {watchlist.watchlist_name} (ID: {watchlist_id})")

            # 构造批处理数据
            stocks_to_process = [(stock_code, set(watchlist.data_types)) for stock_code in watchlist.stock_codes]

            # 处理数据
            batch_result = await self._process_stock_batch(stocks_to_process, force_refresh)

            # 更新统计
            await self._update_watchlist_stats([watchlist], {
                "cache_hits": batch_result["cache_hits"],
                "cache_misses": batch_result["cache_misses"],
                "processing_time": 0,  # 会在_update_watchlist_stats中重新计算
                "processed_stocks": batch_result["processed"]
            })

            return {
                "watchlist_id": watchlist_id,
                "watchlist_name": watchlist.watchlist_name,
                "result": batch_result,
                "timestamp": datetime.now()
            }

        except Exception as e:
            logger.error(f"处理单个自选股列表失败 (ID: {watchlist_id}): {e}")
            raise

    async def get_batch_summary(self, hours: int = 24) -> Dict[str, Any]:
        """获取批处理摘要统计"""
        try:
            # 这里可以添加从batch_jobs表查询统计的逻辑
            # 目前返回基本信息
            watchlists = await self.watchlist_service.get_priority_watchlists()

            total_stocks = sum(len(wl.stock_codes) for wl in watchlists)
            total_operations = sum(len(wl.stock_codes) * len(wl.data_types) for wl in watchlists)

            return {
                "total_watchlists": len(watchlists),
                "total_stocks": total_stocks,
                "total_operations": total_operations,
                "priority_distribution": self._get_priority_distribution(watchlists),
                "data_type_distribution": self._get_data_type_distribution(watchlists),
                "timestamp": datetime.now()
            }

        except Exception as e:
            logger.error(f"获取批处理摘要失败: {e}")
            raise

    def _get_priority_distribution(self, watchlists: List) -> Dict[int, int]:
        """获取优先级分布"""
        distribution = {}
        for wl in watchlists:
            priority = wl.priority_level
            distribution[priority] = distribution.get(priority, 0) + 1
        return distribution

    def _get_data_type_distribution(self, watchlists: List) -> Dict[str, int]:
        """获取数据类型分布"""
        distribution = {}
        for wl in watchlists:
            for data_type in wl.data_types:
                distribution[data_type] = distribution.get(data_type, 0) + 1
        return distribution

    async def get_priority_watchlists(self, min_priority: int = None) -> List:
        """获取指定最低优先级的自选股列表 - 兼容测试接口"""
        try:
            return await self.watchlist_service.get_priority_watchlists(min_priority)
        except Exception as e:
            logger.error(f"获取优先级自选股列表失败: {e}")
            return []

    async def process_stock_batch(self, stocks: List[str]) -> Dict[str, Any]:
        """处理股票批次 - 兼容测试接口"""
        try:
            # 构造标准格式：[(stock_code, data_types)]
            stock_batch = [(stock, {'financial', 'announcements'}) for stock in stocks]
            return await self._process_stock_batch(stock_batch, force_refresh=False)
        except Exception as e:
            logger.error(f"处理股票批次失败: {e}")
            return {
                "processed": 0,
                "success": 0,
                "failed": len(stocks),
                "skipped": 0,
                "failed_items": [{"error": str(e), "stocks": stocks}],
                "cache_hits": 0,
                "cache_misses": 0
            }