#!/bin/bash

# RAG Service 测试案例执行脚本
# 基于 RAG_Service_Test_Cases.md

echo "🧪 RAG Service 完整测试执行"
echo "=============================="

# 设置测试结果文件
TEST_RESULT_FILE="test_results_$(date +%Y%m%d_%H%M%S).log"
echo "📋 测试结果将保存到: $TEST_RESULT_FILE"

# 测试结果统计
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 记录测试结果函数
log_test_result() {
    local test_id="$1"
    local test_name="$2"
    local result="$3"
    local details="$4"

    TOTAL_TESTS=$((TOTAL_TESTS + 1))

    echo "[$test_id] $test_name: $result" | tee -a $TEST_RESULT_FILE
    if [[ "$details" != "" ]]; then
        echo "    详情: $details" | tee -a $TEST_RESULT_FILE
    fi

    if [[ "$result" == "PASS" ]]; then
        PASSED_TESTS=$((PASSED_TESTS + 1))
        echo "    ✅ 测试通过" | tee -a $TEST_RESULT_FILE
    else
        FAILED_TESTS=$((FAILED_TESTS + 1))
        echo "    ❌ 测试失败" | tee -a $TEST_RESULT_FILE
    fi
    echo "" | tee -a $TEST_RESULT_FILE
}

echo "🚀 开始测试执行..." | tee $TEST_RESULT_FILE
echo "测试时间: $(date)" | tee -a $TEST_RESULT_FILE
echo "" | tee -a $TEST_RESULT_FILE

# ============================================
# TC-A1: 服务启动测试
# ============================================
echo "📋 执行测试组 A: 系统维护功能"

# A1.1: 服务启动测试
echo "🔍 测试 A1.1: 服务启动功能"
if curl -s http://localhost:8001/api/health >/dev/null 2>&1; then
    log_test_result "A1.1" "服务启动功能" "PASS" "服务正在运行，健康检查通过"
else
    log_test_result "A1.1" "服务启动功能" "FAIL" "服务未运行或健康检查失败"
fi

# A1.2: 依赖服务连接测试
echo "🔍 测试 A1.2: 依赖服务连接"
health_response=$(curl -s http://localhost:8001/api/health)
if echo "$health_response" | grep -q '"status":"healthy"'; then
    log_test_result "A1.2" "依赖服务连接" "PASS" "所有依赖服务连接正常"
else
    log_test_result "A1.2" "依赖服务连接" "FAIL" "依赖服务连接异常: $health_response"
fi

# A4.1: API健康检查
echo "🔍 测试 A4.1: API健康检查"
http_code=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/api/health)
if [[ "$http_code" == "200" ]]; then
    log_test_result "A4.1" "API健康检查" "PASS" "HTTP状态码: $http_code"
else
    log_test_result "A4.1" "API健康检查" "FAIL" "HTTP状态码: $http_code (期望: 200)"
fi

# ============================================
# TC-B1: RSS监控功能测试
# ============================================
echo "📋 执行测试组 B: 核心业务功能"

# B1.1: RSS数据收集测试
echo "🔍 测试 B1.1: RSS数据收集"
if ls rss_data/isolated_rss_*.json >/dev/null 2>&1; then
    latest_file=$(ls -t rss_data/isolated_rss_*.json | head -1)
    article_count=$(cat "$latest_file" | jq -r '.metadata.total_articles // 0' 2>/dev/null)
    if [[ "$article_count" -gt 0 ]]; then
        log_test_result "B1.1" "RSS数据收集" "PASS" "收集到 $article_count 篇文章"
    else
        log_test_result "B1.1" "RSS数据收集" "FAIL" "数据文件存在但无有效文章"
    fi
else
    log_test_result "B1.1" "RSS数据收集" "FAIL" "未找到RSS数据文件"
fi

# B1.3: 数据格式标准化测试
echo "🔍 测试 B1.3: 数据格式标准化"
if ls rss_data/isolated_rss_*.json >/dev/null 2>&1; then
    latest_file=$(ls -t rss_data/isolated_rss_*.json | head -1)
    if cat "$latest_file" | jq '.metadata, .articles[0].id, .articles[0].title' >/dev/null 2>&1; then
        log_test_result "B1.3" "数据格式标准化" "PASS" "JSON格式符合schema"
    else
        log_test_result "B1.3" "数据格式标准化" "FAIL" "JSON格式不符合schema"
    fi
else
    log_test_result "B1.3" "数据格式标准化" "FAIL" "无数据文件可验证"
fi

# ============================================
# TC-B2: 文档向量化测试
# ============================================

# B2.1: 基础向量化测试（使用真实RSS数据）
echo "🔍 测试 B2.1: 文档向量化（真实数据）"
if ls rss_data/isolated_rss_*.json >/dev/null 2>&1; then
    latest_rss=$(ls -t rss_data/isolated_rss_*.json | head -1)
    real_article=$(cat "$latest_rss" | jq -r '.articles[0]')
    article_id=$(echo "$real_article" | jq -r '.id')
    article_content=$(echo "$real_article" | jq -r '.content')
    article_title=$(echo "$real_article" | jq -r '.title')
    article_source=$(echo "$real_article" | jq -r '.source')

    embed_response=$(curl -s -X POST http://localhost:8001/api/rag/embed \
        -H "Content-Type: application/json" \
        -d "{
            \"documents\": [
                {
                    \"id\": \"$article_id\",
                    \"content\": \"$article_content\",
                    \"metadata\": {
                        \"source\": \"$article_source\",
                        \"title\": \"$article_title\"
                    }
                }
            ]
        }" 2>/dev/null)
else
    embed_response='{"error": "No RSS data available"}'
fi

if echo "$embed_response" | jq -r '.success' | grep -q "true"; then
    processed_count=$(echo "$embed_response" | jq -r '.processed_count // 0')
    log_test_result "B2.1" "文档向量化" "PASS" "成功处理 $processed_count 个文档"
else
    log_test_result "B2.1" "文档向量化" "FAIL" "向量化请求失败: $embed_response"
fi

# ============================================
# TC-B3: 语义搜索测试
# ============================================

# B3.1: 基础搜索测试（使用真实关键词）
echo "🔍 测试 B3.1: 语义搜索（真实关键词）"
if ls rss_data/isolated_rss_*.json >/dev/null 2>&1; then
    latest_rss=$(ls -t rss_data/isolated_rss_*.json | head -1)
    real_keywords=$(cat "$latest_rss" | jq -r '.articles[0].title' | head -c 50)

    search_response=$(curl -s -X POST http://localhost:8001/api/rag/search \
        -H "Content-Type: application/json" \
        -d "{
            \"query\": \"$real_keywords\",
            \"limit\": 3,
            \"similarity_threshold\": 0.5
        }" 2>/dev/null)
else
    search_response='{"error": "No RSS data available"}'
fi

if echo "$search_response" | jq -r '.results' | grep -q '\[\]' >/dev/null 2>&1; then
    log_test_result "B3.1" "语义搜索" "FAIL" "返回空结果"
elif echo "$search_response" | jq -r '.results[0].document_id' >/dev/null 2>&1; then
    result_count=$(echo "$search_response" | jq -r '.results | length')
    log_test_result "B3.1" "语义搜索" "PASS" "返回 $result_count 个搜索结果"
else
    log_test_result "B3.1" "语义搜索" "FAIL" "搜索响应格式错误: $search_response"
fi

# ============================================
# TC-C1: Bootstrap初始化测试
# ============================================
echo "📋 执行测试组 C: 数据管理功能"

# C1.1: Bootstrap任务创建测试（使用真实数据源）
echo "🔍 测试 C1.1: Bootstrap任务创建（真实数据源）"
if ls rss_data/isolated_rss_*.json >/dev/null 2>&1; then
    latest_rss=$(ls -t rss_data/isolated_rss_*.json | head -1)
    real_sources=$(cat "$latest_rss" | jq -r '.articles[].source' | sort -u | head -3 | jq -R . | jq -s .)
    earliest_date=$(cat "$latest_rss" | jq -r '.articles[].published' | sort | head -1 | cut -d'T' -f1)
    latest_date=$(cat "$latest_rss" | jq -r '.articles[].published' | sort -r | head -1 | cut -d'T' -f1)

    bootstrap_response=$(curl -s -X POST http://localhost:8001/api/rag/bootstrap \
        -H "Content-Type: application/json" \
        -d "{
            \"data_sources\": $real_sources,
            \"time_range\": {\"start\": \"$earliest_date\", \"end\": \"$latest_date\"},
            \"batch_size\": 10,
            \"max_concurrent\": 1
        }" 2>/dev/null)
else
    bootstrap_response='{"error": "No RSS data available"}'
fi

if echo "$bootstrap_response" | jq -r '.task_id' | grep -E '^[a-f0-9\-]+$' >/dev/null 2>&1; then
    task_id=$(echo "$bootstrap_response" | jq -r '.task_id')
    log_test_result "C1.1" "Bootstrap任务创建" "PASS" "任务ID: $task_id"

    # C1.2: 任务进度查询测试
    echo "🔍 测试 C1.2: 任务进度查询"
    progress_response=$(curl -s -X GET "http://localhost:8001/api/rag/bootstrap/$task_id" 2>/dev/null)
    if echo "$progress_response" | jq -r '.task_id' | grep -q "$task_id"; then
        status=$(echo "$progress_response" | jq -r '.status')
        log_test_result "C1.2" "任务进度查询" "PASS" "任务状态: $status"
    else
        log_test_result "C1.2" "任务进度查询" "FAIL" "无法查询任务进度"
    fi
else
    log_test_result "C1.1" "Bootstrap任务创建" "FAIL" "任务创建失败: $bootstrap_response"
    log_test_result "C1.2" "任务进度查询" "SKIP" "依赖任务创建失败"
fi

# ============================================
# 测试结果汇总
# ============================================
echo "" | tee -a $TEST_RESULT_FILE
echo "🎯 测试执行完成" | tee -a $TEST_RESULT_FILE
echo "====================" | tee -a $TEST_RESULT_FILE
echo "总计测试: $TOTAL_TESTS" | tee -a $TEST_RESULT_FILE
echo "通过测试: $PASSED_TESTS" | tee -a $TEST_RESULT_FILE
echo "失败测试: $FAILED_TESTS" | tee -a $TEST_RESULT_FILE

if [[ $FAILED_TESTS -eq 0 ]]; then
    echo "✅ 所有测试通过!" | tee -a $TEST_RESULT_FILE
    exit 0
else
    echo "❌ 有 $FAILED_TESTS 个测试失败" | tee -a $TEST_RESULT_FILE
    echo "📋 详细结果请查看: $TEST_RESULT_FILE"
    exit 1
fi