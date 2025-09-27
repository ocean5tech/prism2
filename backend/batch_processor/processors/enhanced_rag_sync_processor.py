#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强的RAG同步处理器 - 集成完整日志记录
"""
import asyncio
import logging
import time
import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime

# 导入日志系统
from app.utils.logger import rag_logger, batch_logger, PrismLogger

from ..services.version_manager import VersionManager
from ..services.data_vectorizer import DataVectorizer

logger = logging.getLogger(__name__)


class EnhancedRAGSyncProcessor:
    """增强的RAG同步处理器 - 集成日志记录"""

    def __init__(self):
        """初始化RAG同步处理器"""
        self.version_manager = VersionManager()
        self.data_vectorizer = DataVectorizer()

        # 创建专用日志记录器
        self.rag_logger = PrismLogger("rag", "sync_processor")

        # 尝试导入RAG服务
        try:
            from services.rag_service import rag_service
            self.rag_service = rag_service
            logger.info("RAG服务导入成功")
        except ImportError:
            logger.warning("RAG服务导入失败，将使用模拟模式")
            self.rag_service = None

        logger.info("增强RAG同步处理器初始化完成")

    async def sync_single_stock_data(self, stock_code: str, data_type: str) -> Dict[str, Any]:
        """
        同步单个股票数据到RAG系统

        Args:
            stock_code: 股票代码
            data_type: 数据类型

        Returns:
            同步结果
        """
        start_time = time.time()

        try:
            logger.info(f"开始RAG同步: {stock_code}-{data_type}")

            # 1. 创建或获取数据版本
            version_result = await self._create_data_version(stock_code, data_type)
            if not version_result['success']:
                raise Exception(f"创建数据版本失败: {version_result['error']}")

            version_id = version_result['version_id']
            input_chunks = 0
            output_vectors = 0

            # 2. 数据向量化
            if version_result['needs_vectorization']:
                vectorization_result = await self._vectorize_data(stock_code, data_type, version_id)

                input_chunks = vectorization_result['input_chunks']
                output_vectors = vectorization_result['output_vectors']

                if not vectorization_result['success']:
                    # 标记版本为失败
                    await self.version_manager.update_vector_status(version_id, "failed")

                    execution_time = time.time() - start_time

                    # 记录失败的RAG操作
                    self.rag_logger.log_rag_operation(
                        operation_type="sync_single_stock",
                        stock_code=stock_code,
                        data_type=data_type,
                        input_chunks=input_chunks,
                        output_vectors=0,
                        collection_name=f"{stock_code}_{data_type}",
                        version_id=version_id,
                        execution_time=execution_time,
                        status="failed",
                        error_message=vectorization_result['error']
                    )

                    return {
                        'success': False,
                        'version_id': version_id,
                        'error': vectorization_result['error']
                    }

                # 3. 更新向量状态
                await self.version_manager.update_vector_status(version_id, "vectorized")

            # 4. 激活版本
            await self.version_manager.activate_version(version_id)

            execution_time = time.time() - start_time

            # 记录成功的RAG操作
            collection_name = f"prism2_{stock_code}_{data_type}"
            self.rag_logger.log_rag_operation(
                operation_type="sync_single_stock",
                stock_code=stock_code,
                data_type=data_type,
                input_chunks=input_chunks,
                output_vectors=output_vectors,
                collection_name=collection_name,
                version_id=version_id,
                execution_time=execution_time,
                status="success"
            )

            logger.info(f"RAG同步成功: {stock_code}-{data_type}, version={version_id}")

            return {
                'success': True,
                'version_id': version_id,
                'chunks_processed': input_chunks,
                'vectors_created': output_vectors
            }

        except Exception as e:
            execution_time = time.time() - start_time

            # 记录错误的RAG操作
            self.rag_logger.log_rag_operation(
                operation_type="sync_single_stock",
                stock_code=stock_code,
                data_type=data_type,
                input_chunks=0,
                output_vectors=0,
                collection_name=f"{stock_code}_{data_type}",
                version_id=str(uuid.uuid4()),
                execution_time=execution_time,
                status="failed",
                error_message=str(e)
            )

            logger.error(f"RAG同步失败: {stock_code}-{data_type}, error: {e}")
            return {
                'success': False,
                'version_id': None,
                'error': str(e)
            }

    async def sync_batch_stocks(self, stock_data_list: List[Dict[str, str]]) -> Dict[str, Any]:
        """
        批量同步股票数据到RAG系统

        Args:
            stock_data_list: 股票数据列表，格式: [{"stock_code": "000001", "data_type": "financial"}, ...]

        Returns:
            批量同步结果
        """
        start_time = time.time()

        try:
            total_stocks = len(set(item['stock_code'] for item in stock_data_list))
            total_data_types = len(set(item['data_type'] for item in stock_data_list))

            logger.info(f"开始批量RAG同步: {total_stocks}只股票, {total_data_types}种数据类型")

            success_count = 0
            failed_count = 0
            skipped_count = 0
            total_chunks = 0
            total_vectors = 0
            error_details = []

            # 处理每个数据项
            for item in stock_data_list:
                stock_code = item['stock_code']
                data_type = item['data_type']

                try:
                    result = await self.sync_single_stock_data(stock_code, data_type)

                    if result['success']:
                        success_count += 1
                        total_chunks += result.get('chunks_processed', 0)
                        total_vectors += result.get('vectors_created', 0)
                    else:
                        failed_count += 1
                        error_details.append(f"{stock_code}-{data_type}: {result.get('error', 'Unknown error')}")

                    # 添加延迟避免系统压力
                    await asyncio.sleep(0.1)

                except Exception as e:
                    failed_count += 1
                    error_details.append(f"{stock_code}-{data_type}: {str(e)}")
                    logger.error(f"批量同步项失败: {stock_code}-{data_type}, error: {e}")

            execution_time = time.time() - start_time
            success_rate = success_count / len(stock_data_list) if stock_data_list else 0

            # 记录批量RAG处理日志
            batch_logger.log_batch_execution(
                process_name="rag_batch_sync",
                data_source="stock_data_batch",
                input_count=len(stock_data_list),
                output_count=success_count,
                rag_stored_count=total_vectors,
                execution_time=execution_time,
                success_rate=success_rate,
                error_details=error_details
            )

            logger.info(f"批量RAG同步完成: 成功{success_count}, 失败{failed_count}, 跳过{skipped_count}, 耗时{execution_time:.2f}秒")

            return {
                'success_count': success_count,
                'failed_count': failed_count,
                'skipped_count': skipped_count,
                'total_chunks_processed': total_chunks,
                'total_vectors_created': total_vectors,
                'execution_time': execution_time,
                'success_rate': success_rate,
                'error_details': error_details
            }

        except Exception as e:
            execution_time = time.time() - start_time

            # 记录批量处理错误
            batch_logger.log_batch_execution(
                process_name="rag_batch_sync",
                data_source="stock_data_batch",
                input_count=len(stock_data_list) if stock_data_list else 0,
                output_count=0,
                rag_stored_count=0,
                execution_time=execution_time,
                success_rate=0,
                error_details=[str(e)]
            )

            logger.error(f"批量RAG同步失败: {e}")
            raise

    async def get_sync_status(self) -> Dict[str, Any]:
        """
        获取RAG同步状态统计

        Returns:
            同步状态信息
        """
        try:
            # 获取版本统计
            version_stats = await self.version_manager.get_version_statistics()

            # 计算平均切片数
            active_versions = await self.version_manager.get_versions_by_status("active")
            total_chunks = sum(v.get('chunk_count', 0) for v in active_versions)
            avg_chunks = total_chunks / len(active_versions) if active_versions else 0

            failed_versions = await self.version_manager.get_versions_by_status("failed")
            failed_chunks = sum(v.get('chunk_count', 0) for v in failed_versions)
            failed_avg_chunks = failed_chunks / len(failed_versions) if failed_versions else 0

            status = {
                'active': {
                    'count': version_stats.get('active', 0),
                    'avg_chunks': round(avg_chunks, 1)
                },
                'failed': {
                    'count': version_stats.get('failed', 0),
                    'avg_chunks': round(failed_avg_chunks, 1)
                },
                'total_vectors': total_chunks,
                'timestamp': datetime.now()
            }

            logger.info(f"RAG同步状态: {status}")
            return status

        except Exception as e:
            logger.error(f"获取RAG同步状态失败: {e}")
            raise

    async def _create_data_version(self, stock_code: str, data_type: str) -> Dict[str, Any]:
        """创建数据版本"""
        try:
            # 模拟从数据库获取数据
            mock_data = {
                'financial': {'revenue': 1000000, 'profit': 100000},
                'announcements': [{'title': 'Test Announcement', 'content': 'Test content'}],
                'shareholders': [{'name': 'Test Shareholder', 'ratio': 10.5}],
                'longhubang': [{'rank': 1, 'amount': 1000000}]
            }

            source_data = mock_data.get(data_type, {})

            version_id = await self.version_manager.create_version(
                stock_code=stock_code,
                data_type=data_type,
                source_data=source_data
            )

            return {
                'success': True,
                'version_id': version_id,
                'needs_vectorization': True
            }

        except Exception as e:
            return {
                'success': False,
                'version_id': None,
                'error': str(e)
            }

    async def _vectorize_data(self, stock_code: str, data_type: str, version_id: str) -> Dict[str, Any]:
        """向量化数据"""
        try:
            # 获取版本数据
            version_info = await self.version_manager.get_version_info(version_id)
            if not version_info:
                raise Exception(f"版本 {version_id} 不存在")

            # 转换为文本块
            text_chunks = self.data_vectorizer.convert_to_text_chunks(
                stock_code=stock_code,
                data_type=data_type,
                data=version_info.get('source_data', {})
            )

            if not text_chunks:
                return {
                    'success': False,
                    'input_chunks': 0,
                    'output_vectors': 0,
                    'error': '无法生成文本块'
                }

            # 模拟向量化过程
            if self.rag_service:
                # 实际RAG服务调用
                vectors = await self._store_to_rag_service(stock_code, data_type, text_chunks, version_id)
            else:
                # 模拟向量化
                vectors = len(text_chunks)

            logger.info(f"向量化完成: {stock_code}-{data_type}, {len(text_chunks)}个文本块")

            return {
                'success': True,
                'input_chunks': len(text_chunks),
                'output_vectors': vectors,
                'text_chunks': text_chunks
            }

        except Exception as e:
            return {
                'success': False,
                'input_chunks': 0,
                'output_vectors': 0,
                'error': str(e)
            }

    async def _store_to_rag_service(self, stock_code: str, data_type: str, text_chunks: List[str], version_id: str) -> int:
        """存储到RAG服务"""
        try:
            collection_name = f"prism2_{stock_code}_{data_type}"

            # 调用RAG服务存储向量
            result = await self.rag_service.store_documents(
                collection_name=collection_name,
                documents=text_chunks,
                metadata={
                    'stock_code': stock_code,
                    'data_type': data_type,
                    'version_id': version_id,
                    'created_at': datetime.now().isoformat()
                }
            )

            return len(text_chunks)

        except Exception as e:
            logger.error(f"存储到RAG服务失败: {e}")
            raise


# 创建全局实例
enhanced_rag_sync_processor = EnhancedRAGSyncProcessor()