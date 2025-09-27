# -*- coding: utf-8 -*-
"""
Prism2 统一日志系统
支持API调用、AKShare调用、批处理、RAG操作的详细日志记录
"""

import os
import json
import logging
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from pathlib import Path
from functools import wraps
import time

# 日志基础配置
LOG_BASE_DIR = "/home/wyatt/prism2/logs"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

class PrismLogger:
    """Prism2 统一日志记录器"""

    def __init__(self, log_type: str, component: str = ""):
        """
        初始化日志记录器

        Args:
            log_type: 日志类型 (api, akshare, batch, rag, system)
            component: 组件名称，用于细分日志
        """
        self.log_type = log_type
        self.component = component
        self.log_dir = Path(LOG_BASE_DIR)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 创建基础logger
        logger_name = f"prism2.{log_type}"
        if component:
            logger_name += f".{component}"

        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)

        # 避免重复添加handler
        if not self.logger.handlers:
            self._setup_handlers()

    def _setup_handlers(self):
        """设置日志处理器"""
        # 文件handler - 详细日志
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if self.component:
            log_filename = f"{self.log_type}_{self.component}_{timestamp}.log"
        else:
            log_filename = f"{self.log_type}_{timestamp}.log"

        file_handler = logging.FileHandler(
            self.log_dir / log_filename,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)

        # JSON格式handler - 结构化数据
        json_filename = log_filename.replace('.log', '.json')
        self.json_file = self.log_dir / json_filename

        # 设置格式
        formatter = logging.Formatter(LOG_FORMAT)
        file_handler.setFormatter(formatter)

        self.logger.addHandler(file_handler)

    def _write_json_log(self, log_data: Dict[str, Any]):
        """写入JSON格式日志"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "log_type": self.log_type,
            "component": self.component,
            **log_data
        }

        try:
            # 追加到JSON文件
            with open(self.json_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(log_entry, ensure_ascii=False, default=str) + '\n')
        except Exception as e:
            self.logger.error(f"Failed to write JSON log: {e}")

    def log_api_call(self,
                     endpoint: str,
                     method: str,
                     request_data: Dict[str, Any],
                     response_data: Dict[str, Any],
                     status_code: int,
                     execution_time: float,
                     client_ip: str = None,
                     user_id: str = None):
        """记录API调用日志"""

        log_data = {
            "category": "api_call",
            "endpoint": endpoint,
            "method": method,
            "request": {
                "parameters": request_data,
                "client_ip": client_ip,
                "user_id": user_id
            },
            "response": {
                "data": response_data,
                "status_code": status_code
            },
            "performance": {
                "execution_time_ms": round(execution_time * 1000, 2)
            }
        }

        # 记录文本日志
        self.logger.info(
            f"API Call: {method} {endpoint} | "
            f"Status: {status_code} | "
            f"Time: {execution_time*1000:.2f}ms | "
            f"Params: {len(request_data)} | "
            f"Response: {len(str(response_data))} chars"
        )

        # 记录JSON日志
        self._write_json_log(log_data)

    def log_akshare_call(self,
                        function_name: str,
                        input_params: Dict[str, Any],
                        output_keys: List[str],
                        data_count: int,
                        status_code: int,
                        execution_time: float,
                        error_message: str = None):
        """记录AKShare调用日志"""

        log_data = {
            "category": "akshare_call",
            "function": function_name,
            "input": {
                "parameters": input_params,
                "param_count": len(input_params)
            },
            "output": {
                "keys": output_keys,
                "data_count": data_count,
                "status_code": status_code
            },
            "performance": {
                "execution_time_ms": round(execution_time * 1000, 2)
            },
            "error": error_message
        }

        # 记录文本日志
        if status_code == 200:
            self.logger.info(
                f"AKShare Call: {function_name} | "
                f"Params: {input_params} | "
                f"Data: {data_count} rows | "
                f"Keys: {output_keys} | "
                f"Time: {execution_time*1000:.2f}ms"
            )
        else:
            self.logger.error(
                f"AKShare Error: {function_name} | "
                f"Status: {status_code} | "
                f"Error: {error_message} | "
                f"Time: {execution_time*1000:.2f}ms"
            )

        # 记录JSON日志
        self._write_json_log(log_data)

    def log_batch_execution(self,
                           process_name: str,
                           data_source: str,
                           input_count: int,
                           output_count: int,
                           rag_stored_count: int,
                           execution_time: float,
                           success_rate: float,
                           cache_hits: int = 0,
                           cache_misses: int = 0,
                           error_details: List[str] = None):
        """记录批处理执行日志"""

        log_data = {
            "category": "batch_execution",
            "process": process_name,
            "data_flow": {
                "source": data_source,
                "input_count": input_count,
                "processed_count": output_count,
                "rag_stored_count": rag_stored_count,
                "success_rate": round(success_rate, 2)
            },
            "performance": {
                "execution_time_ms": round(execution_time * 1000, 2),
                "throughput_per_sec": round(output_count / execution_time, 2) if execution_time > 0 else 0
            },
            "cache": {
                "hits": cache_hits,
                "misses": cache_misses,
                "hit_rate": round(cache_hits / (cache_hits + cache_misses), 2) if (cache_hits + cache_misses) > 0 else 0
            },
            "errors": error_details or []
        }

        # 记录文本日志
        self.logger.info(
            f"Batch Process: {process_name} | "
            f"Source: {data_source} | "
            f"In: {input_count} -> Out: {output_count} -> RAG: {rag_stored_count} | "
            f"Success: {success_rate:.1%} | "
            f"Time: {execution_time*1000:.2f}ms | "
            f"Cache: {cache_hits}H/{cache_misses}M"
        )

        # 记录JSON日志
        self._write_json_log(log_data)

    def log_rag_operation(self,
                         operation_type: str,
                         stock_code: str,
                         data_type: str,
                         input_chunks: int,
                         output_vectors: int,
                         collection_name: str,
                         version_id: str,
                         execution_time: float,
                         embedding_model: str = "bge-large-zh-v1.5",
                         status: str = "success",
                         error_message: str = None):
        """记录RAG操作日志"""

        log_data = {
            "category": "rag_operation",
            "operation": operation_type,
            "stock_info": {
                "code": stock_code,
                "data_type": data_type
            },
            "processing": {
                "input_chunks": input_chunks,
                "output_vectors": output_vectors,
                "embedding_model": embedding_model,
                "collection": collection_name,
                "version_id": version_id
            },
            "performance": {
                "execution_time_ms": round(execution_time * 1000, 2),
                "vectors_per_sec": round(output_vectors / execution_time, 2) if execution_time > 0 else 0
            },
            "status": status,
            "error": error_message
        }

        # 记录文本日志
        if status == "success":
            self.logger.info(
                f"RAG {operation_type}: {stock_code}-{data_type} | "
                f"Chunks: {input_chunks} -> Vectors: {output_vectors} | "
                f"Collection: {collection_name} | "
                f"Version: {version_id[:8]}... | "
                f"Time: {execution_time*1000:.2f}ms"
            )
        else:
            self.logger.error(
                f"RAG {operation_type} Failed: {stock_code}-{data_type} | "
                f"Error: {error_message} | "
                f"Time: {execution_time*1000:.2f}ms"
            )

        # 记录JSON日志
        self._write_json_log(log_data)


# 装饰器函数
def log_api_calls(logger_instance: PrismLogger):
    """API调用装饰器"""
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                # 获取请求信息
                request_data = kwargs.copy()
                endpoint = func.__name__

                # 执行函数
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time

                # 记录成功调用
                logger_instance.log_api_call(
                    endpoint=endpoint,
                    method="GET/POST",
                    request_data=request_data,
                    response_data=result if isinstance(result, dict) else {"data": str(result)},
                    status_code=200,
                    execution_time=execution_time
                )

                return result

            except Exception as e:
                execution_time = time.time() - start_time

                # 记录失败调用
                logger_instance.log_api_call(
                    endpoint=endpoint,
                    method="GET/POST",
                    request_data=request_data,
                    response_data={"error": str(e), "traceback": traceback.format_exc()},
                    status_code=500,
                    execution_time=execution_time
                )
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()

            try:
                # 获取请求信息
                request_data = kwargs.copy()
                endpoint = func.__name__

                # 执行函数
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time

                # 记录成功调用
                logger_instance.log_api_call(
                    endpoint=endpoint,
                    method="FUNC",
                    request_data=request_data,
                    response_data=result if isinstance(result, dict) else {"data": str(result)},
                    status_code=200,
                    execution_time=execution_time
                )

                return result

            except Exception as e:
                execution_time = time.time() - start_time

                # 记录失败调用
                logger_instance.log_api_call(
                    endpoint=endpoint,
                    method="FUNC",
                    request_data=request_data,
                    response_data={"error": str(e), "traceback": traceback.format_exc()},
                    status_code=500,
                    execution_time=execution_time
                )
                raise

        return async_wrapper if hasattr(func, '__code__') and func.__code__.co_flags & 0x80 else sync_wrapper
    return decorator


def log_akshare_calls(logger_instance: PrismLogger):
    """AKShare调用装饰器"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            function_name = func.__name__

            try:
                # 执行AKShare函数
                result = func(*args, **kwargs)
                execution_time = time.time() - start_time

                # 分析返回数据
                if hasattr(result, 'columns'):
                    # DataFrame
                    output_keys = list(result.columns)
                    data_count = len(result)
                elif isinstance(result, dict):
                    output_keys = list(result.keys())
                    data_count = 1
                elif isinstance(result, list):
                    output_keys = ["list_data"]
                    data_count = len(result)
                else:
                    output_keys = ["scalar_data"]
                    data_count = 1

                # 记录成功调用
                logger_instance.log_akshare_call(
                    function_name=function_name,
                    input_params=kwargs,
                    output_keys=output_keys,
                    data_count=data_count,
                    status_code=200,
                    execution_time=execution_time
                )

                return result

            except Exception as e:
                execution_time = time.time() - start_time

                # 记录失败调用
                logger_instance.log_akshare_call(
                    function_name=function_name,
                    input_params=kwargs,
                    output_keys=[],
                    data_count=0,
                    status_code=500,
                    execution_time=execution_time,
                    error_message=str(e)
                )
                raise

        return wrapper
    return decorator


# 全局日志实例
api_logger = PrismLogger("api", "backend")
akshare_logger = PrismLogger("akshare", "service")
batch_logger = PrismLogger("batch", "processor")
rag_logger = PrismLogger("rag", "service")
system_logger = PrismLogger("system", "core")