# Prism2 日志系统综合测试报告

## 📋 测试概要

- **测试开始时间**: 2025-09-23T09:55:06.585576
- **测试结束时间**: None
- **总测试数量**: 23
- **通过测试**: 20
- **失败测试**: 3
- **成功率**: 86.4%

## 📊 性能指标

- **总执行时间**: 0.27 秒
- **测试吞吐量**: 82.01 tests/sec
- **日志文件生成**: 20 个

## 📁 生成的日志文件

- /home/wyatt/prism2/logs/api_backend_20250923_095450.log
- /home/wyatt/prism2/logs/api_backend_20250923_095506.log
- /home/wyatt/prism2/logs/api_backend_20250923_095355.log
- /home/wyatt/prism2/logs/api_backend_20250923_093105.log
- /home/wyatt/prism2/logs/api_backend_20250923_093105.json
- /home/wyatt/prism2/logs/akshare_service_20250923_093105.log
- /home/wyatt/prism2/logs/akshare_service_20250923_095450.log
- /home/wyatt/prism2/logs/akshare_service_20250923_095355.log
- /home/wyatt/prism2/logs/akshare_service_20250923_095506.log
- /home/wyatt/prism2/logs/akshare_service_20250923_093105.json
- /home/wyatt/prism2/logs/batch_processor_20250923_095450.log
- /home/wyatt/prism2/logs/batch_processor_20250923_093105.log
- /home/wyatt/prism2/logs/batch_processor_20250923_095506.log
- /home/wyatt/prism2/logs/batch_processor_20250923_095355.log
- /home/wyatt/prism2/logs/batch_processor_20250923_093105.json
- /home/wyatt/prism2/logs/rag_service_20250923_095506.log
- /home/wyatt/prism2/logs/rag_service_20250923_093105.log
- /home/wyatt/prism2/logs/rag_service_20250923_095355.log
- /home/wyatt/prism2/logs/rag_service_20250923_095450.log
- /home/wyatt/prism2/logs/rag_service_20250923_093105.json

## 🧪 详细测试结果

### ✅ cleanup_old_logs

- **状态**: 通过
- **详情**: 成功清理旧日志文件
- **时间**: 2025-09-23T09:55:06.586071

### ❌ service_check_postgresql

- **状态**: 失败
- **详情**: PostgreSQL 状态: 
- **时间**: 2025-09-23T09:55:06.614122

### ❌ service_check_redis

- **状态**: 失败
- **详情**: Redis 状态: 
- **时间**: 2025-09-23T09:55:06.620020

### ✅ prepare_test_data

- **状态**: 通过
- **详情**: 测试数据准备成功
- **时间**: 2025-09-23T09:55:06.620036

### ✅ A1_stock_search_api

- **状态**: 通过
- **详情**: API调用测试成功，耗时: 0.39ms
- **时间**: 2025-09-23T09:55:06.620435

### ✅ A2_stock_detail_api

- **状态**: 通过
- **详情**: API调用测试成功，耗时: 0.06ms
- **时间**: 2025-09-23T09:55:06.620498

### ✅ A3_batch_stocks_api

- **状态**: 通过
- **详情**: API调用测试成功，耗时: 0.04ms
- **时间**: 2025-09-23T09:55:06.620547

### ✅ A4_error_handling_api

- **状态**: 通过
- **详情**: API调用测试成功，耗时: 0.08ms
- **时间**: 2025-09-23T09:55:06.620631

### ✅ B1_stock_list_retrieval

- **状态**: 通过
- **详情**: AKShare调用成功，数据量: 250，耗时: 1510.00ms
- **时间**: 2025-09-23T09:55:06.620743

### ❌ B2_individual_stock_data

- **状态**: 失败
- **详情**: AKShare测试失败: can't multiply sequence by non-int of type 'float'
- **时间**: 2025-09-23T09:55:06.620750

### ✅ B3_financial_data

- **状态**: 通过
- **详情**: AKShare调用成功，数据量: 30，耗时: 1510.00ms
- **时间**: 2025-09-23T09:55:06.620833

### ✅ C1_watchlist_priority_processing

- **状态**: 通过
- **详情**: 批处理成功，成功率: 80.0%，耗时: 2000.00ms
- **时间**: 2025-09-23T09:55:06.620952

### ✅ C2_akshare_data_sync

- **状态**: 通过
- **详情**: 批处理成功，成功率: 90.0%，耗时: 2000.00ms
- **时间**: 2025-09-23T09:55:06.621007

### ✅ D1_document_vectorization

- **状态**: 通过
- **详情**: RAG操作成功，向量数: 5，耗时: 1000.00ms
- **时间**: 2025-09-23T09:55:06.623087

### ✅ D2_semantic_search_query

- **状态**: 通过
- **详情**: RAG操作成功，向量数: 3，耗时: 1000.00ms
- **时间**: 2025-09-23T09:55:06.623149

### ✅ D3_embedding_processing

- **状态**: 通过
- **详情**: RAG操作成功，向量数: 8，耗时: 1000.00ms
- **时间**: 2025-09-23T09:55:06.623210

### ✅ e2e_flow_test

- **状态**: 通过
- **详情**: 端到端流程测试成功，总耗时: 0.31ms
- **时间**: 2025-09-23T09:55:06.623528

### ✅ concurrent_logging_test

- **状态**: 通过
- **详情**: 并发测试成功，20个请求，耗时: 190.92ms，吞吐量: 104.75 req/s
- **时间**: 2025-09-23T09:55:06.814466

### ✅ rss_monitoring_check

- **状态**: 通过
- **详情**: RSS监控检查完成，文件检查: 3/4
- **时间**: 2025-09-23T09:55:06.830867

### ✅ watchlist_batch_check

- **状态**: 通过
- **详情**: 自选股批处理检查完成，文件检查: 5/6
- **时间**: 2025-09-23T09:55:06.843646

### ✅ log_files_verification

- **状态**: 通过
- **详情**: 日志文件完整性: 250.0% (20/8)
- **时间**: 2025-09-23T09:55:06.844662

### ✅ log_content_verification

- **状态**: 通过
- **详情**: 日志内容有效性: 100.0% (12/12)
- **时间**: 2025-09-23T09:55:06.853791

### ✅ performance_analysis

- **状态**: 通过
- **详情**: 性能分析完成，成功率: 86.4%，执行时间: 0.27s
- **时间**: 2025-09-23T09:55:06.853851


## 🤖 自动化批处理状态

### rss_monitoring

- ✅ isolated_rss_monitor.py: True
- ✅ start_isolated_rss.sh: True
- ✅ stop_isolated_rss.sh: True
- ❌ rss_process_running: False

### watchlist_processing

- ✅ watchlist_processor.py: True
- ✅ watchlist_service.py: True
- ✅ watchlist.py: True
- ✅ batch_config.yaml: True
- ✅ scheduler.py: True
- ❌ batch_process_running: False


---

**报告生成时间**: 2025-09-23T09:55:06.854559