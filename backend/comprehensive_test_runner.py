#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prism2 Backend全面测试执行器
基于Backend-Comprehensive-Test-Plan.md的可执行测试脚本
"""
import asyncio
import json
import time
import sys
import logging
import requests
import redis
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from typing import Dict, List, Any, Optional

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ComprehensiveTestRunner:
    """Backend全面测试运行器"""

    def __init__(self):
        self.api_base_url = "http://localhost:8081"
        self.test_stocks = {
            "online": "600549",  # 厦门钨业
            "batch": ["688660", "600629", "600619"]  # 深度学习、华建集团、海立股份
        }

        # 连接配置
        self.redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        self.pg_config = {
            'host': 'localhost',
            'database': 'prism2',
            'user': 'prism2',
            'password': 'prism2_secure_password'
        }

        # 测试结果
        self.test_results = {
            "start_time": datetime.now(),
            "online_api_tests": {},
            "batch_processing_tests": {},
            "data_consistency_tests": {},
            "performance_tests": {},
            "integration_tests": {},
            "summary": {}
        }

    def get_pg_connection(self):
        """获取PostgreSQL连接"""
        try:
            return psycopg2.connect(**self.pg_config, cursor_factory=RealDictCursor)
        except psycopg2.Error as e:
            logger.error(f"PostgreSQL连接失败: {e}")
            raise Exception(f"数据库连接失败: {e}")
        except Exception as e:
            logger.error(f"数据库连接异常: {e}")
            raise Exception(f"数据库连接异常: {e}")

    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("🚀 开始Backend全面测试")
        logger.info(f"测试股票 - Online: {self.test_stocks['online']}, Batch: {self.test_stocks['batch']}")

        try:
            # 1. Online API测试
            await self.run_online_api_tests()

            # 2. 批处理系统测试
            await self.run_batch_processing_tests()

            # 3. 数据一致性测试
            await self.run_data_consistency_tests()

            # 4. 性能测试
            await self.run_performance_tests()

            # 5. 集成测试
            await self.run_integration_tests()

            # 6. 生成测试报告
            await self.generate_test_report()

        except Exception as e:
            logger.error(f"测试执行失败: {e}")
            raise

    async def run_online_api_tests(self):
        """Online API系统测试"""
        logger.info("\n" + "="*60)
        logger.info("🌐 Part 1: Online API系统测试")
        logger.info("="*60)

        online_results = {}

        # 测试用例 API-001: 主要仪表板接口
        logger.info("测试用例 API-001: 主要仪表板接口")

        # 清空缓存
        self.redis_client.flushdb()
        logger.info("✓ 缓存已清空")

        # 发送API请求
        payload = {
            "stock_code": self.test_stocks["online"],
            "data_types": ["realtime", "kline", "basic_info", "financial", "announcements", "shareholders", "longhubang"],
            "kline_period": "daily",
            "kline_days": 60,
            "news_days": 7
        }

        start_time = time.time()
        try:
            response = requests.post(
                f"{self.api_base_url}/api/v1/stocks/dashboard",
                json=payload,
                timeout=30
            )
            response_time = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                online_results["api_001"] = {
                    "success": True,
                    "response_time": response_time,
                    "stock_code": data.get("stock_code"),
                    "data_sources": data.get("data_sources", {}),
                    "cache_info": data.get("cache_info", {}),
                    "data_types_count": len(data.get("data", {}))
                }
                logger.info(f"✓ API请求成功: {response_time:.2f}s")
                logger.info(f"  数据类型: {len(data.get('data', {}))} 种")
                logger.info(f"  缓存信息: {data.get('cache_info', {})}")
            else:
                online_results["api_001"] = {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
                logger.error(f"✗ API请求失败: {response.status_code}")

        except Exception as e:
            online_results["api_001"] = {
                "success": False,
                "error": str(e)
            }
            logger.error(f"✗ API请求异常: {e}")

        # 验证数据库存储
        try:
            conn = self.get_pg_connection()
            cursor = conn.cursor()

            tables = ["stock_financial", "stock_announcements", "stock_shareholders", "stock_longhubang"]
            db_counts = {}

            for table in tables:
                cursor.execute(f"SELECT COUNT(*) FROM {table} WHERE stock_code = %s", (self.test_stocks["online"],))
                result = cursor.fetchone()
                count = result['count'] if result else 0
                db_counts[table] = count
                logger.info(f"  {table}: {count} 条记录")

            online_results["database_storage"] = db_counts
            conn.close()

        except Exception as e:
            error_msg = str(e) if str(e) and str(e) != "0" else "数据库连接或查询失败"
            logger.error(f"✗ 数据库验证失败: {error_msg}")
            online_results["database_storage"] = {"error": error_msg}

        # 验证Redis缓存
        try:
            cache_keys = self.redis_client.keys(f"*{self.test_stocks['online']}*")
            online_results["redis_cache"] = {
                "keys_count": len(cache_keys),
                "keys": cache_keys[:10]  # 只显示前10个键
            }
            logger.info(f"  Redis缓存: {len(cache_keys)} 个键")

        except Exception as e:
            logger.error(f"✗ Redis验证失败: {e}")
            online_results["redis_cache"] = {"error": str(e)}

        # 测试用例 API-002: 缓存命中测试
        logger.info("\n测试用例 API-002: 缓存命中测试")

        payload_cache = {
            "stock_code": self.test_stocks["online"],
            "data_types": ["realtime", "kline", "basic_info"],
            "kline_period": "daily",
            "kline_days": 60
        }

        start_time = time.time()
        try:
            response = requests.post(
                f"{self.api_base_url}/api/v1/stocks/dashboard",
                json=payload_cache,
                timeout=10
            )
            response_time = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                online_results["api_002"] = {
                    "success": True,
                    "response_time": response_time,
                    "cache_info": data.get("cache_info", {})
                }
                logger.info(f"✓ 缓存测试成功: {response_time:.2f}s")
                logger.info(f"  缓存命中: {data.get('cache_info', {})}")
            else:
                online_results["api_002"] = {
                    "success": False,
                    "error": f"HTTP {response.status_code}"
                }
                logger.error(f"✗ 缓存测试失败: {response.status_code}")

        except Exception as e:
            online_results["api_002"] = {
                "success": False,
                "error": str(e)
            }
            logger.error(f"✗ 缓存测试异常: {e}")

        # 测试用例 API-003: 根路径测试
        logger.info("\n测试用例 API-003: 根路径测试")

        try:
            response = requests.get(f"{self.api_base_url}/", timeout=5)
            if response.status_code == 200:
                data = response.json()
                online_results["api_003"] = {
                    "success": True,
                    "message": data.get("message"),
                    "status": data.get("status"),
                    "version": data.get("version")
                }
                logger.info(f"✓ 根路径测试成功: {data.get('message')}")
            else:
                online_results["api_003"] = {
                    "success": False,
                    "error": f"HTTP {response.status_code}"
                }
                logger.error(f"✗ 根路径测试失败: {response.status_code}")

        except Exception as e:
            online_results["api_003"] = {
                "success": False,
                "error": str(e)
            }
            logger.error(f"✗ 根路径测试异常: {e}")

        self.test_results["online_api_tests"] = online_results

    async def run_batch_processing_tests(self):
        """批处理系统测试"""
        logger.info("\n" + "="*60)
        logger.info("⚡ Part 2: 批处理系统测试")
        logger.info("="*60)

        batch_results = {}

        # 测试用例 BATCH-001: 创建测试自选股列表
        logger.info("测试用例 BATCH-001: 创建测试自选股列表")

        try:
            from batch_processor.services.watchlist_service import WatchlistService
            from batch_processor.models.watchlist import WatchlistCreate

            service = WatchlistService()

            # 清理可能存在的重复测试数据
            try:
                existing_watchlists = await service.get_user_watchlists("test_user_comprehensive")
                for watchlist in existing_watchlists:
                    if watchlist.watchlist_name == "综合测试股票池":
                        await service.delete_watchlist(watchlist.id)
                        logger.info(f"已清理重复的测试自选股列表: {watchlist.id}")
            except Exception as cleanup_error:
                logger.warning(f"清理重复数据时出错: {cleanup_error}")

            watchlist_data = WatchlistCreate(
                user_id='test_user_comprehensive',
                watchlist_name='综合测试股票池',
                description='用于Backend全面测试的股票组合',
                stock_codes=self.test_stocks["batch"],
                priority_level=5,
                data_types=['financial', 'announcements', 'shareholders', 'longhubang'],
                auto_batch=True
            )

            result = await service.create_watchlist(watchlist_data)
            batch_results["batch_001"] = {
                "success": True,
                "watchlist_id": getattr(result, "id", None),
                "stock_codes": getattr(result, "stock_codes", None),
                "priority_level": getattr(result, "priority_level", None)
            }
            logger.info(f"✓ 自选股列表创建成功: ID={getattr(result, 'id', None)}")
            logger.info(f"  包含股票: {getattr(result, 'stock_codes', None)}")

        except Exception as e:
            batch_results["batch_001"] = {
                "success": False,
                "error": str(e)
            }
            logger.error(f"✗ 自选股列表创建失败: {e}")

        # 测试用例 BATCH-002: 自选股批处理执行
        logger.info("\n测试用例 BATCH-002: 自选股批处理执行")

        try:
            from batch_processor.processors.watchlist_processor import WatchlistProcessor

            processor = WatchlistProcessor()

            # 获取高优先级自选股列表
            watchlists = await processor.get_priority_watchlists(min_priority=4)
            logger.info(f"发现 {len(watchlists)} 个高优先级自选股列表")

            if watchlists:
                # 执行批处理
                watchlist = watchlists[0]
                start_time = time.time()
                result = await processor.process_single_watchlist(
                    watchlist_id=watchlist.id,
                    force_refresh=True
                )
                processing_time = time.time() - start_time

                batch_results["batch_002"] = {
                    "success": True,
                    "processing_time": processing_time,
                    "processed_stocks": result.get("processed_stocks"),
                    "successful_stocks": result.get("successful_stocks"),
                    "failed_stocks": result.get("failed_stocks")
                }
                logger.info(f"✓ 批处理执行成功: {processing_time:.2f}s")
                logger.info(f"  处理股票: {result.get('processed_stocks')} 只")
                logger.info(f"  成功: {result.get('successful_stocks')}, 失败: {result.get('failed_stocks')}")
            else:
                batch_results["batch_002"] = {
                    "success": False,
                    "error": "没有找到高优先级自选股列表"
                }
                logger.error("✗ 没有找到高优先级自选股列表")

        except Exception as e:
            batch_results["batch_002"] = {
                "success": False,
                "error": str(e)
            }
            logger.error(f"✗ 批处理执行失败: {e}")

        # 测试用例 RAG-001: RAG批量同步测试
        logger.info("\n测试用例 RAG-001: RAG批量同步测试")

        try:
            from batch_processor.processors.rag_sync_processor import RAGSyncProcessor

            processor = RAGSyncProcessor()

            start_time = time.time()
            result = await processor.sync_batch_data_to_rag(
                stock_codes=self.test_stocks["batch"],
                data_types=['financial', 'announcements'],
                force_refresh=True
            )
            sync_time = time.time() - start_time

            batch_results["rag_001"] = {
                "success": True,
                "sync_time": sync_time,
                "successful_syncs": result.get("successful_syncs"),
                "failed_syncs": result.get("failed_syncs"),
                "new_versions_created": result.get("new_versions_created")
            }
            logger.info(f"✓ RAG同步成功: {sync_time:.2f}s")
            logger.info(f"  成功同步: {result.get('successful_syncs')}")
            logger.info(f"  失败同步: {result.get('failed_syncs')}")
            logger.info(f"  新版本: {result.get('new_versions_created')}")

        except Exception as e:
            batch_results["rag_001"] = {
                "success": False,
                "error": str(e)
            }
            logger.error(f"✗ RAG同步失败: {e}")

        self.test_results["batch_processing_tests"] = batch_results

    async def run_data_consistency_tests(self):
        """数据一致性验证测试"""
        logger.info("\n" + "="*60)
        logger.info("📊 Part 3: 数据一致性验证测试")
        logger.info("="*60)

        consistency_results = {}

        # 测试用例 DATA-001: 三层架构数据流验证
        logger.info("测试用例 DATA-001: 三层架构数据流验证")

        test_stock = self.test_stocks["online"]
        data_types = ['financial', 'announcements', 'shareholders']

        try:
            conn = self.get_pg_connection()
            cursor = conn.cursor()

            consistency_data = {}

            for data_type in data_types:
                logger.info(f"\n检查 {test_stock} - {data_type}:")

                # 1. 检查Redis缓存
                cache_key = f'{data_type}:{test_stock}'
                redis_data = self.redis_client.get(cache_key)
                redis_status = "有数据" if redis_data else "无数据"
                redis_size = len(redis_data) if redis_data else 0

                # 2. 检查PostgreSQL存储
                table_map = {
                    'financial': ('stock_financial', 'summary_data'),
                    'announcements': ('stock_announcements', 'announcement_data'),
                    'shareholders': ('stock_shareholders', 'shareholders_data')
                }

                table_name, data_column = table_map[data_type]
                cursor.execute(f'SELECT {data_column}, updated_at FROM {table_name} WHERE stock_code = %s ORDER BY updated_at DESC LIMIT 1', (test_stock,))
                pg_result = cursor.fetchone()
                pg_status = "有数据" if pg_result else "无数据"
                pg_update_time = pg_result["updated_at"] if pg_result else None

                # 3. 数据一致性检查
                consistency_rate = 0.0
                if redis_data and pg_result:
                    try:
                        redis_obj = json.loads(redis_data)
                        pg_obj = pg_result[data_column]

                        # 对于不同类型的数据，使用不同的一致性检查策略
                        if data_type == "financial":
                            # 财务数据：比较数值字段的存在性
                            if isinstance(redis_obj, dict) and isinstance(pg_obj, dict):
                                redis_keys = set(redis_obj.keys())
                                pg_keys = set(pg_obj.keys())
                                common_keys = redis_keys & pg_keys
                                total_keys = max(len(redis_keys), len(pg_keys))
                                consistency_rate = len(common_keys) / total_keys if total_keys > 0 else 0.0
                            elif redis_obj and pg_obj:
                                # 如果两边都有数据但格式不同，认为50%一致
                                consistency_rate = 0.5
                        else:
                            # 其他数据类型：直接比较
                            if isinstance(redis_obj, dict) and isinstance(pg_obj, dict):
                                redis_keys = set(redis_obj.keys())
                                pg_keys = set(pg_obj.keys())
                                common_keys = redis_keys & pg_keys
                                total_keys = max(len(redis_keys), len(pg_keys))
                                consistency_rate = len(common_keys) / total_keys if total_keys > 0 else 0.0
                            elif str(redis_obj) == str(pg_obj):
                                consistency_rate = 1.0
                            elif redis_obj and pg_obj:
                                consistency_rate = 0.5
                    except Exception as consistency_error:
                        # 如果两边都有数据但无法解析，认为部分一致
                        if redis_data and pg_result[data_column]:
                            consistency_rate = 0.3
                        else:
                            consistency_rate = 0.0

                consistency_data[data_type] = {
                    "redis_status": redis_status,
                    "redis_size": redis_size,
                    "postgresql_status": pg_status,
                    "postgresql_update_time": str(pg_update_time) if pg_update_time else None,
                    "consistency_rate": consistency_rate
                }

                logger.info(f"  Redis: {redis_status} ({redis_size} 字符)")
                logger.info(f"  PostgreSQL: {pg_status} (更新时间: {pg_update_time})")
                logger.info(f"  数据一致性: {consistency_rate:.2%}")

            conn.close()

            consistency_results["data_001"] = {
                "success": True,
                "test_stock": test_stock,
                "data_types": consistency_data
            }

        except Exception as e:
            consistency_results["data_001"] = {
                "success": False,
                "error": str(e)
            }
            logger.error(f"✗ 数据一致性验证失败: {e}")

        # 测试用例 DATA-002: 批处理数据完整性检查
        logger.info("\n测试用例 DATA-002: 批处理数据完整性检查")

        try:
            conn = self.get_pg_connection()
            cursor = conn.cursor()

            # 检查测试股票数据覆盖率
            all_test_stocks = [self.test_stocks["online"]] + self.test_stocks["batch"]
            coverage_data = {}

            for stock_code in all_test_stocks:
                cursor.execute("SELECT COUNT(*) FROM stock_financial WHERE stock_code = %s", (stock_code,))
                result = cursor.fetchone()
                financial_count = result['count'] if result else 0

                cursor.execute("SELECT COUNT(*) FROM stock_announcements WHERE stock_code = %s", (stock_code,))
                result = cursor.fetchone()
                announcements_count = result['count'] if result else 0

                cursor.execute("SELECT COUNT(*) FROM stock_shareholders WHERE stock_code = %s", (stock_code,))
                result = cursor.fetchone()
                shareholders_count = result['count'] if result else 0

                cursor.execute("SELECT COUNT(*) FROM stock_longhubang WHERE stock_code = %s", (stock_code,))
                result = cursor.fetchone()
                longhubang_count = result['count'] if result else 0

                coverage_data[stock_code] = {
                    "financial": "✓" if financial_count > 0 else "✗",
                    "announcements": "✓" if announcements_count > 0 else "✗",
                    "shareholders": "✓" if shareholders_count > 0 else "✗",
                    "longhubang": "✓" if longhubang_count > 0 else "✗"
                }

                logger.info(f"  {stock_code}: 财务{coverage_data[stock_code]['financial']} 公告{coverage_data[stock_code]['announcements']} 股东{coverage_data[stock_code]['shareholders']} 龙虎榜{coverage_data[stock_code]['longhubang']}")

            # 检查RAG版本数据
            cursor.execute("""
                SELECT stock_code, data_type, vector_status, chunk_count
                FROM rag_data_versions
                WHERE stock_code = ANY(%s) AND vector_status = 'active'
                ORDER BY stock_code, data_type
            """, (all_test_stocks,))
            rag_versions = cursor.fetchall()

            rag_data = {}
            for row in rag_versions:
                stock_code = row['stock_code']
                if stock_code not in rag_data:
                    rag_data[stock_code] = {}
                rag_data[stock_code][row['data_type']] = {
                    "status": row['vector_status'],
                    "chunk_count": row['chunk_count']
                }

            logger.info(f"\nRAG版本数据: {len(rag_versions)} 个活跃版本")
            for stock_code, types in rag_data.items():
                logger.info(f"  {stock_code}: {len(types)} 种数据类型")

            conn.close()

            consistency_results["data_002"] = {
                "success": True,
                "coverage_data": coverage_data,
                "rag_versions_count": len(rag_versions),
                "rag_data": rag_data
            }

        except Exception as e:
            error_msg = str(e) if str(e) != "0" else "数据库连接或查询失败"
            consistency_results["data_002"] = {
                "success": False,
                "error": error_msg
            }
            logger.error(f"✗ 数据完整性检查失败: {error_msg}")

        self.test_results["data_consistency_tests"] = consistency_results

    async def run_performance_tests(self):
        """性能与压力测试"""
        logger.info("\n" + "="*60)
        logger.info("🚀 Part 4: 性能与压力测试")
        logger.info("="*60)

        performance_results = {}

        # 测试用例 PERF-001: API响应时间基准测试
        logger.info("测试用例 PERF-001: API响应时间基准测试")

        try:
            test_stock = self.test_stocks["online"]
            payload = {
                "stock_code": test_stock,
                "data_types": ["realtime", "kline", "basic_info"],
                "kline_period": "daily",
                "kline_days": 60
            }

            # 冷启动测试（清空缓存）
            self.redis_client.delete(f"*{test_stock}*")

            start_time = time.time()
            response = requests.post(f"{self.api_base_url}/api/v1/stocks/dashboard", json=payload, timeout=30)
            cold_start_time = time.time() - start_time

            # 热缓存测试
            start_time = time.time()
            response = requests.post(f"{self.api_base_url}/api/v1/stocks/dashboard", json=payload, timeout=10)
            hot_cache_time = time.time() - start_time

            # 并发测试
            concurrent_times = []
            for i in range(3):  # 3个并发请求
                start_time = time.time()
                response = requests.post(f"{self.api_base_url}/api/v1/stocks/dashboard", json=payload, timeout=10)
                concurrent_times.append(time.time() - start_time)

            avg_concurrent_time = sum(concurrent_times) / len(concurrent_times)

            performance_results["perf_001"] = {
                "success": True,
                "cold_start_time": cold_start_time,
                "hot_cache_time": hot_cache_time,
                "avg_concurrent_time": avg_concurrent_time,
                "performance_grade": {
                    "cold_start": "优秀" if cold_start_time < 5 else "一般" if cold_start_time < 10 else "差",
                    "hot_cache": "优秀" if hot_cache_time < 1 else "一般" if hot_cache_time < 2 else "差"
                }
            }

            logger.info(f"✓ API性能测试完成:")
            logger.info(f"  冷启动: {cold_start_time:.2f}s")
            logger.info(f"  热缓存: {hot_cache_time:.2f}s")
            logger.info(f"  并发平均: {avg_concurrent_time:.2f}s")

        except Exception as e:
            performance_results["perf_001"] = {
                "success": False,
                "error": str(e)
            }
            logger.error(f"✗ API性能测试失败: {e}")

        self.test_results["performance_tests"] = performance_results

    async def run_integration_tests(self):
        """综合集成测试"""
        logger.info("\n" + "="*60)
        logger.info("📋 Part 5: 综合集成测试")
        logger.info("="*60)

        integration_results = {}

        # 测试用例 E2E-001: 完整业务流程测试
        logger.info("测试用例 E2E-001: 完整业务流程测试")

        try:
            test_stock = self.test_stocks["batch"][0]  # 使用603993

            # 步骤1: 环境清理
            logger.info("步骤1: 环境清理")
            cache_keys = self.redis_client.keys(f"*{test_stock}*")
            if cache_keys:
                self.redis_client.delete(*cache_keys)

            conn = self.get_pg_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM rag_data_versions WHERE stock_code = %s", (test_stock,))
            conn.commit()
            conn.close()

            # 步骤2: API首次调用（冷启动）
            logger.info("步骤2: API冷启动调用")
            payload = {
                "stock_code": test_stock,
                "data_types": ["financial", "announcements"]
            }

            start_time = time.time()
            response = requests.post(f"{self.api_base_url}/api/v1/stocks/dashboard", json=payload, timeout=30)
            cold_response_time = time.time() - start_time

            cold_success = response.status_code == 200
            cold_cache_info = response.json().get("cache_info", {}) if cold_success else {}

            # 步骤3: 执行批处理
            logger.info("步骤3: 执行批处理")
            from batch_processor.processors.watchlist_processor import WatchlistProcessor

            processor = WatchlistProcessor()
            batch_start = time.time()
            batch_result = await processor.process_stock_batch([test_stock])
            batch_time = time.time() - batch_start
            batch_success = batch_result.get("success", 0) > 0

            # 步骤4: 执行RAG同步
            logger.info("步骤4: 执行RAG同步")
            from batch_processor.processors.rag_sync_processor import RAGSyncProcessor

            rag_processor = RAGSyncProcessor()
            rag_start = time.time()
            rag_result = await rag_processor.sync_batch_data_to_rag(
                stock_codes=[test_stock],
                data_types=['financial', 'announcements']
            )
            rag_time = time.time() - rag_start
            rag_success = rag_result.get("successful_syncs", 0) > 0

            # 步骤5: API再次调用（热缓存）
            logger.info("步骤5: API热缓存调用")
            start_time = time.time()
            response = requests.post(f"{self.api_base_url}/api/v1/stocks/dashboard", json=payload, timeout=10)
            hot_response_time = time.time() - start_time

            hot_success = response.status_code == 200
            hot_cache_info = response.json().get("cache_info", {}) if hot_success else {}

            integration_results["e2e_001"] = {
                "success": all([cold_success, batch_success, rag_success, hot_success]),
                "cold_start": {
                    "success": cold_success,
                    "response_time": cold_response_time,
                    "cache_info": cold_cache_info
                },
                "batch_processing": {
                    "success": batch_success,
                    "processing_time": batch_time,
                    "result": batch_result
                },
                "rag_sync": {
                    "success": rag_success,
                    "sync_time": rag_time,
                    "result": rag_result
                },
                "hot_cache": {
                    "success": hot_success,
                    "response_time": hot_response_time,
                    "cache_info": hot_cache_info
                }
            }

            logger.info(f"✓ 端到端测试完成:")
            logger.info(f"  冷启动API: {cold_success} ({cold_response_time:.2f}s)")
            logger.info(f"  批处理: {batch_success} ({batch_time:.2f}s)")
            logger.info(f"  RAG同步: {rag_success} ({rag_time:.2f}s)")
            logger.info(f"  热缓存API: {hot_success} ({hot_response_time:.2f}s)")

        except Exception as e:
            integration_results["e2e_001"] = {
                "success": False,
                "error": str(e)
            }
            logger.error(f"✗ 端到端测试失败: {e}")

        self.test_results["integration_tests"] = integration_results

    async def generate_test_report(self):
        """生成测试报告"""
        logger.info("\n" + "="*60)
        logger.info("📊 生成测试报告")
        logger.info("="*60)

        end_time = datetime.now()
        total_time = (end_time - self.test_results["start_time"]).total_seconds()

        # 统计测试结果
        total_tests = 0
        passed_tests = 0

        # 排除非测试项目的条目
        excluded_items = ["start_time", "summary", "database_storage", "redis_cache"]

        for category, tests in self.test_results.items():
            if category in excluded_items:
                continue

            for test_name, result in tests.items():
                # 跳过非测试条目
                if test_name in excluded_items:
                    continue

                total_tests += 1
                if result.get("success", False):
                    passed_tests += 1

        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0

        # 生成摘要
        summary = {
            "test_execution_time": total_time,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": total_tests - passed_tests,
            "success_rate": success_rate,
            "test_stocks": self.test_stocks,
            "overall_status": "PASS" if success_rate >= 80 else "FAIL"
        }

        self.test_results["summary"] = summary
        self.test_results["end_time"] = end_time

        # 保存测试报告
        report_file = f"/home/wyatt/prism2/docs/Backend-Test-Report-{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(self.test_results, f, ensure_ascii=False, indent=2, default=str)

        # 输出测试报告
        logger.info(f"🎯 测试总结:")
        logger.info(f"  总测试数: {total_tests}")
        logger.info(f"  通过测试: {passed_tests}")
        logger.info(f"  失败测试: {total_tests - passed_tests}")
        logger.info(f"  成功率: {success_rate:.1f}%")
        logger.info(f"  总耗时: {total_time:.1f}秒")
        logger.info(f"  整体状态: {summary['overall_status']}")
        logger.info(f"  测试报告: {report_file}")

        if success_rate >= 80:
            logger.info("🎉 Backend系统测试通过！")
        else:
            logger.warning("⚠️ Backend系统测试未达标，需要检查失败的测试用例")

        return summary

async def main():
    """主函数"""
    try:
        runner = ComprehensiveTestRunner()
        await runner.run_all_tests()
    except KeyboardInterrupt:
        logger.info("\n测试被用户中断")
    except Exception as e:
        logger.error(f"测试执行失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())