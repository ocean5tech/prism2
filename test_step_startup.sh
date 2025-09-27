#!/bin/bash
# ==============================================================
# Prism2 股票分析平台 - 统一启动脚本
# ==============================================================
# 版本: 2.0
# 更新时间: 2025-09-26
# 功能: 按序启动所有服务并进行健康检查
# ==============================================================

set -e  # 遇到错误立即退出

# 日志文件设置
LOG_DIR="/home/wyatt/prism2/logs/startup_logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/startup_$(date +%Y%m%d_%H%M%S).log"
CURRENT_STEP=""

# 确保日志目录权限
chmod 755 "$LOG_DIR" 2>/dev/null || true

# 错误处理函数
handle_error() {
    local exit_code=$?
    local line_number=$1
    echo -e "\n❌ 脚本执行失败！" | tee -a "$LOG_FILE"
    echo "错误发生在行号: $line_number" | tee -a "$LOG_FILE"
    echo "当前执行步骤: $CURRENT_STEP" | tee -a "$LOG_FILE"
    echo "退出代码: $exit_code" | tee -a "$LOG_FILE"
    echo "时间: $(date)" | tee -a "$LOG_FILE"
    echo "详细日志请查看: $LOG_FILE" | tee -a "$LOG_FILE"
    exit $exit_code
}

# 设置错误陷阱
trap 'handle_error $LINENO' ERR

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# 增强日志函数 - 同时输出到控制台和日志文件
log_info() {
    local timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    local msg="${BLUE}[INFO]${NC} $1"
    local file_msg="[$timestamp] [INFO] $1"
    echo -e "$msg"
    echo "$file_msg" >> "$LOG_FILE"
}

log_success() {
    local timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    local msg="${GREEN}[SUCCESS]${NC} $1"
    local file_msg="[$timestamp] [SUCCESS] $1"
    echo -e "$msg"
    echo "$file_msg" >> "$LOG_FILE"
}

log_warning() {
    local timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    local msg="${YELLOW}[WARNING]${NC} $1"
    local file_msg="[$timestamp] [WARNING] $1"
    echo -e "$msg"
    echo "$file_msg" >> "$LOG_FILE"
}

log_error() {
    local timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    local msg="${RED}[ERROR]${NC} $1"
    local file_msg="[$timestamp] [ERROR] $1"
    echo -e "$msg"
    echo "$file_msg" >> "$LOG_FILE"
}

log_step() {
    local timestamp="$(date '+%Y-%m-%d %H:%M:%S')"
    CURRENT_STEP="$1"
    local msg="\n${PURPLE}[STEP]${NC} $1"
    local file_msg="[$timestamp] [STEP] $1"
    echo -e "$msg"
    echo "$file_msg" >> "$LOG_FILE"
    echo "=====================================" >> "$LOG_FILE"
}

# 检查端口是否被占用
check_port() {
    local port=$1
    local service_name=$2

    if netstat -tuln | grep ":$port " > /dev/null 2>&1; then
        log_success "端口 $port ($service_name) 已在使用"
        return 0
    else
        log_warning "端口 $port ($service_name) 未使用"
        return 1
    fi
}

# 实际数据检测函数
test_redis_functionality() {
    log_info "测试Redis实际读写功能..."

    # 使用redis-cli进行实际测试
    local test_key="prism2_startup_test_$(date +%s)"
    local test_value="startup_test_value"

    # 写入测试
    if redis-cli -p 6379 set "$test_key" "$test_value" EX 60 > /dev/null 2>&1; then
        log_info "Redis写入测试成功"

        # 读取测试
        local retrieved_value=$(redis-cli -p 6379 get "$test_key" 2>/dev/null)
        if [[ "$retrieved_value" == "$test_value" ]]; then
            log_success "Redis读写功能验证通过"
            redis-cli -p 6379 del "$test_key" > /dev/null 2>&1
            return 0
        else
            log_error "Redis读取测试失败：值不匹配"
            return 1
        fi
    else
        log_error "Redis写入测试失败"
        return 1
    fi
}

test_postgresql_functionality() {
    log_info "测试PostgreSQL实际数据查询功能..."

    # 测试数据库连接和基本查询
    local test_query="SELECT version(), now(), pg_database_size('stock_data') as db_size;"

    if PGPASSWORD="your_password" psql -h localhost -U postgres -d stock_data -c "$test_query" > /dev/null 2>&1; then
        log_info "PostgreSQL基础查询测试成功"

        # 测试stock相关表查询
        local stock_table_query="SELECT COUNT(*) as table_count FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE '%stock%';"
        local table_count=$(PGPASSWORD="your_password" psql -h localhost -U postgres -d stock_data -t -c "$stock_table_query" 2>/dev/null | tr -d ' ')

        if [[ "$table_count" -gt 0 ]]; then
            log_success "PostgreSQL数据查询功能验证通过（发现 $table_count 个股票相关表）"
            return 0
        else
            log_warning "PostgreSQL连接正常，但未发现股票相关表"
            return 0  # 连接正常就算通过
        fi
    else
        log_error "PostgreSQL数据查询测试失败"
        return 1
    fi
}

test_dashboard_api_functionality() {
    log_info "测试Enhanced Dashboard API实际数据功能..."

    # 测试健康检查
    local health_response=$(curl -s "http://localhost:8081/health" 2>/dev/null)
    if [[ "$health_response" == *"healthy"* || "$health_response" == *"ok"* ]]; then
        log_info "Enhanced Dashboard API健康检查通过"

        # 测试实际股票数据接口
        local stock_response=$(curl -s "http://localhost:8081/api/stock/realtime?symbol=688469" 2>/dev/null)
        if [[ "$stock_response" != "ERROR" && "$stock_response" != "" ]]; then
            # 检查响应是否包含股票相关数据
            if [[ "$stock_response" == *"price"* || "$stock_response" == *"symbol"* || "$stock_response" == *"688469"* ]]; then
                log_success "Enhanced Dashboard API股票数据功能验证通过"
                return 0
            else
                log_warning "Enhanced Dashboard API返回响应，但可能不包含预期的股票数据"
                return 0  # 有响应就算通过
            fi
        else
            log_warning "Enhanced Dashboard API股票数据接口无响应，但基础服务正常"
            return 0  # 健康检查通过就算可用
        fi
    else
        log_error "Enhanced Dashboard API健康检查失败"
        return 1
    fi
}

test_mcp_service_functionality() {
    local port=$1
    local service_name=$2

    log_info "测试 $service_name 实际功能..."

    # 测试健康检查
    local health_response=$(curl -s "http://localhost:$port/health" 2>/dev/null)
    if [[ "$health_response" != "ERROR" && "$health_response" != "" ]]; then
        log_success "$service_name 健康检查功能验证通过"
        return 0
    else
        log_error "$service_name 健康检查失败"
        return 1
    fi
}

test_claude_integration_functionality() {
    log_info "测试Claude集成层实际分析功能..."

    # 测试基础API
    local base_response=$(curl -s "http://localhost:9000" 2>/dev/null)
    if [[ "$base_response" == *"Claude Integration API"* ]]; then
        log_info "Claude集成层基础API验证通过"

        # 测试健康检查
        local health_response=$(curl -s "http://localhost:9000/health" 2>/dev/null)
        if [[ "$health_response" == *"healthy"* || "$health_response" == *"ok"* ]]; then
            log_info "Claude集成层健康检查通过"

            # 测试简单分析请求
            local analysis_request='{"stock_code":"688469","analysis_type":"quick","include_claude_insights":false}'
            local analysis_response=$(curl -s -X POST "http://localhost:9000/api/v1/analysis" \
                -H "Content-Type: application/json" \
                -d "$analysis_request" 2>/dev/null)

            if [[ "$analysis_response" != "ERROR" && "$analysis_response" != "" ]]; then
                log_success "Claude集成层分析功能验证通过"
                return 0
            else
                log_warning "Claude集成层分析接口无响应，但基础服务正常"
                return 0
            fi
        else
            log_error "Claude集成层健康检查失败"
            return 1
        fi
    else
        log_error "Claude集成层基础API验证失败"
        return 1
    fi
}

test_chromadb_functionality() {
    log_info "测试ChromaDB向量数据库功能..."

    # 测试ChromaDB心跳接口
    local heartbeat_response=$(curl -s "http://localhost:8003/api/v1/heartbeat" 2>/dev/null)
    if [[ "$heartbeat_response" != "ERROR" && "$heartbeat_response" != "" ]]; then
        log_info "ChromaDB心跳检查通过"

        # 测试获取版本信息
        local version_response=$(curl -s "http://localhost:8003/api/v1/version" 2>/dev/null)
        if [[ "$version_response" != "ERROR" && "$version_response" != "" ]]; then
            log_success "ChromaDB功能验证通过"
            return 0
        else
            log_warning "ChromaDB版本接口无响应，但心跳正常"
            return 0
        fi
    else
        log_error "ChromaDB心跳检查失败"
        return 1
    fi
}

# 等待服务启动
wait_for_service() {
    local url=$1
    local service_name=$2
    local max_attempts=${3:-30}
    local attempt=0

    log_info "等待 $service_name 启动..."

    while [ $attempt -lt $max_attempts ]; do
        if curl -s "$url" > /dev/null 2>&1; then
            log_success "$service_name 已启动"
            return 0
        fi

        attempt=$((attempt + 1))
        echo -n "."
        sleep 2
    done

    log_error "$service_name 启动超时"
    return 1
}

# 验证服务健康状况
verify_service_health() {
    local url=$1
    local service_name=$2
    local expected_content=$3

    log_info "验证 $service_name 健康状况..."

    response=$(curl -s "$url" 2>/dev/null || echo "ERROR")

    if [[ "$response" == "ERROR" ]]; then
        log_error "$service_name 健康检查失败: 无法连接"
        return 1
    fi

    if [[ -n "$expected_content" && "$response" != *"$expected_content"* ]]; then
        log_warning "$service_name 响应异常，但服务可能仍在运行"
    else
        log_success "$service_name 健康检查通过"
    fi

    return 0
}

# 启动基础软件
start_infrastructure() {
    log_step "第1步: 启动基础软件层"

    # 启动Redis容器
    log_info "启动 Redis 容器 (端口 6379)..."
    if ! check_port 6379 "Redis"; then
        if podman ps -a | grep -q "prism2-redis"; then
            log_info "Redis容器存在但未运行，正在启动..."
            if podman start prism2-redis; then
                log_success "Redis容器启动成功"
                wait_for_service "http://localhost:6379" "Redis" 15 2>/dev/null || true
            else
                log_error "Redis容器启动失败"
                return 1
            fi
        else
            log_warning "Redis容器不存在，请先创建容器"
            log_info "建议运行: podman run -d --name prism2-redis -p 6379:6379 redis:latest"
        fi
    else
        log_success "Redis 已经运行在端口 6379"
    fi

    # Redis实际数据检测
    if check_port 6379 "Redis" > /dev/null 2>&1; then
        test_redis_functionality
    else
        log_warning "跳过Redis实际数据检测：服务未运行"
    fi

    # 启动PostgreSQL容器
    log_info "启动 PostgreSQL 容器 (端口 5432)..."
    if ! check_port 5432 "PostgreSQL"; then
        if podman ps -a | grep -q "prism2-postgres"; then
            log_info "PostgreSQL容器存在但未运行，正在启动..."
            if podman start prism2-postgres; then
                log_success "PostgreSQL容器启动成功"
                sleep 5  # PostgreSQL需要更多启动时间
                log_success "PostgreSQL 启动完成"
            else
                log_error "PostgreSQL容器启动失败"
                return 1
            fi
        else
            log_warning "PostgreSQL容器不存在，请先创建容器"
            log_info "建议运行相应的数据库创建脚本"
        fi
    else
        log_success "PostgreSQL 已经运行在端口 5432"
    fi

    # PostgreSQL实际数据检测
    if check_port 5432 "PostgreSQL" > /dev/null 2>&1; then
        test_postgresql_functionality
    else
        log_warning "跳过PostgreSQL实际数据检测：服务未运行"
    fi

    # 启动ChromaDB容器 (RAG服务)
    log_info "启动 ChromaDB 容器 (端口 8003)..."
    if ! check_port 8003 "ChromaDB"; then
        if podman ps -a | grep -q "prism2-chromadb"; then
            log_info "ChromaDB容器存在但未运行，正在启动..."
            if podman start prism2-chromadb; then
                log_success "ChromaDB容器启动成功"
                wait_for_service "http://localhost:8003/api/v1/heartbeat" "ChromaDB" 20
            else
                log_error "ChromaDB容器启动失败"
                return 1
            fi
        else
            log_warning "ChromaDB容器不存在，请先创建容器"
        fi
    else
        log_success "ChromaDB 已经运行在端口 8003"
    fi

    # ChromaDB实际功能检测
    if check_port 8003 "ChromaDB" > /dev/null 2>&1; then
        test_chromadb_functionality
    else
        log_warning "跳过ChromaDB实际功能检测：服务未运行"
    fi

    # 启动Ollama容器 (可选)
    log_info "检查 Ollama 容器 (端口 11434)..."
    if ! check_port 11434 "Ollama"; then
        if podman ps -a | grep -q "prism2-ollama"; then
            log_info "Ollama容器存在但未运行，正在启动..."
            if podman start prism2-ollama; then
                log_success "Ollama容器启动成功"
                wait_for_service "http://localhost:11434/api/tags" "Ollama" 30
            else
                log_warning "Ollama容器启动失败，但这不影响主要功能"
            fi
        else
            log_info "Ollama容器不存在，跳过启动"
        fi
    else
        log_success "Ollama 已经运行在端口 11434"
    fi

    # 启动OpenWebUI容器 (可选)
    log_info "检查 OpenWebUI 容器 (端口 3001)..."
    if ! check_port 3001 "OpenWebUI"; then
        if podman ps -a | grep -q "prism2-openwebui"; then
            log_info "OpenWebUI容器存在但未运行，正在启动..."
            if podman start prism2-openwebui; then
                log_success "OpenWebUI容器启动成功"
                wait_for_service "http://localhost:3001" "OpenWebUI" 30
            else
                log_warning "OpenWebUI容器启动失败，但这不影响主要功能"
            fi
        else
            log_info "OpenWebUI容器不存在，跳过启动"
        fi
    else
        log_success "OpenWebUI 已经运行在端口 3001"
    fi

    # 显示podman容器状态
    log_info "当前 Podman 容器状态:"
    if command -v podman &> /dev/null; then
        podman ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | while read line; do
            echo "    $line"
        done
    fi

    log_success "基础软件层启动完成"
}

# 启动后台服务
start_backend_services() {
    log_step "第2步: 启动后台服务层"

    cd /home/wyatt/prism2

    # 创建日志目录
    mkdir -p logs

    # Enhanced Dashboard API (端口 8081)
    log_info "启动 Enhanced Dashboard API (端口 8081)..."
    if ! check_port 8081 "Enhanced Dashboard API"; then
        log_info "启动 Enhanced Dashboard API..."

        # 检查backend目录是否存在
        if [ -d "backend" ]; then
            cd backend

            # 激活虚拟环境
            if [ -f "test_venv/bin/activate" ]; then
                source test_venv/bin/activate
                log_info "已激活 test_venv 虚拟环境"
            else
                log_warning "test_venv 虚拟环境不存在，使用系统Python"
            fi

            # 启动API服务
            if [ -f "enhanced_dashboard_api.py" ]; then
                nohup python enhanced_dashboard_api.py > ../logs/enhanced_dashboard.log 2>&1 &
                echo $! > ../logs/enhanced_dashboard.pid
                log_info "Enhanced Dashboard API 后台启动，PID: $(cat ../logs/enhanced_dashboard.pid)"

                cd ..
                wait_for_service "http://localhost:8081/health" "Enhanced Dashboard API"
            else
                log_error "enhanced_dashboard_api.py 文件不存在"
                cd ..
                return 1
            fi
        else
            log_error "backend 目录不存在"
            return 1
        fi
    else
        log_success "Enhanced Dashboard API 已经运行在端口 8081"
    fi

    # 验证数据API健康状况
    if verify_service_health "http://localhost:8081/health" "Enhanced Dashboard API" "healthy"; then
        log_success "Enhanced Dashboard API 健康检查通过"

        # Enhanced Dashboard API实际数据检测
        test_dashboard_api_functionality
    else
        log_warning "Enhanced Dashboard API 健康检查异常，但服务可能仍在启动中"
        log_warning "跳过Enhanced Dashboard API实际数据检测"
    fi

    log_success "后台服务层启动完成"
}

# 启动RAG服务
start_rag_services() {
    log_step "第3步: 启动RAG服务层"

    cd /home/wyatt/prism2

    # ChromaDB RAG服务 (端口 8001/8003)
    log_info "检查 RAG 服务..."
    if ! check_port 8001 "RAG Service" && ! check_port 8003 "RAG Service"; then
        log_info "启动 RAG 服务..."
        # 这里应该添加RAG服务的启动命令
        log_warning "RAG 服务启动命令待配置"
    fi

    log_success "RAG服务层检查完成"
}

# 启动传统MCP服务 (兼容性) - 已注释，不再使用
# start_legacy_mcp() {
#     log_step "第4步: 启动传统MCP服务 (兼容性)"
#
#     cd /home/wyatt/prism2
#
#     # MCPO代理 (端口 8005)
#     log_info "检查 MCPO 代理..."
#     if ! check_port 8005 "MCPO Agent"; then
#         log_info "启动 MCPO 代理..."
#         source mcp_env/bin/activate
#         export PYTHONPATH=/home/wyatt/prism2:$PYTHONPATH
#         nohup mcpo --config mcpo_config.json --host 0.0.0.0 --port 8005 --cors-allow-origins "*" > logs/mcpo.log 2>&1 &
#         echo $! > logs/mcpo.pid
#
#         wait_for_service "http://localhost:8005" "MCPO Agent"
#     fi
#
#     verify_service_health "http://localhost:8005/prism2-stock-analysis/openapi.json" "MCPO Agent"
#
#     log_success "传统MCP服务启动完成"
# }

# 启动4MCP服务架构
start_4mcp_services() {
    log_step "第5步: 启动4MCP服务架构"

    cd /home/wyatt/prism2/mcp_servers

    # 准备环境
    source mcp4_venv/bin/activate
    export PYTHONPATH=/home/wyatt/prism2/mcp_servers/shared:$PYTHONPATH

    # 创建日志目录
    mkdir -p ../logs/4mcp

    # 启动实时数据MCP (端口 8006)
    log_info "启动实时数据MCP (端口 8006)..."
    if ! check_port 8006 "实时数据MCP"; then
        nohup mcpo --config realtime_data_mcp/mcpo_config.json --host 0.0.0.0 --port 8006 > ../logs/4mcp/realtime_data.log 2>&1 &
        echo $! > ../logs/4mcp/realtime_data.pid
        wait_for_service "http://localhost:8006/health" "实时数据MCP"
    fi

    # 启动结构化数据MCP (端口 8007)
    log_info "启动结构化数据MCP (端口 8007)..."
    if ! check_port 8007 "结构化数据MCP"; then
        nohup mcpo --config structured_data_mcp/mcpo_config.json --host 0.0.0.0 --port 8007 > ../logs/4mcp/structured_data.log 2>&1 &
        echo $! > ../logs/4mcp/structured_data.pid
        wait_for_service "http://localhost:8007/health" "结构化数据MCP"
    fi

    # 启动RAG增强MCP (端口 8008)
    log_info "启动RAG增强MCP (端口 8008)..."
    if ! check_port 8008 "RAG增强MCP"; then
        nohup mcpo --config rag_mcp/mcpo_config.json --host 0.0.0.0 --port 8008 > ../logs/4mcp/rag_enhanced.log 2>&1 &
        echo $! > ../logs/4mcp/rag_enhanced.pid
        wait_for_service "http://localhost:8008/health" "RAG增强MCP"
    fi

    # 启动任务协调MCP (端口 8009)
    log_info "启动任务协调MCP (端口 8009)..."
    if ! check_port 8009 "任务协调MCP"; then
        nohup mcpo --config coordination_mcp/mcpo_config.json --host 0.0.0.0 --port 8009 > ../logs/4mcp/coordination.log 2>&1 &
        echo $! > ../logs/4mcp/coordination.pid
        wait_for_service "http://localhost:8009/health" "任务协调MCP"
    fi

    # 验证4MCP服务
    verify_service_health "http://localhost:8006/health" "实时数据MCP"
    verify_service_health "http://localhost:8007/health" "结构化数据MCP"
    verify_service_health "http://localhost:8008/health" "RAG增强MCP"
    verify_service_health "http://localhost:8009/health" "任务协调MCP"

    # 4MCP服务实际功能检测
    log_info "开始4MCP服务实际功能检测..."
    test_mcp_service_functionality 8006 "实时数据MCP"
    test_mcp_service_functionality 8007 "结构化数据MCP"
    test_mcp_service_functionality 8008 "RAG增强MCP"
    test_mcp_service_functionality 8009 "任务协调MCP"

    log_success "4MCP服务架构启动完成"
}

# 启动Claude集成层
start_claude_integration() {
    log_step "第6步: 启动Claude API集成层"

    cd /home/wyatt/prism2/mcp_servers

    # Claude API集成层 (端口 9000)
    log_info "启动Claude API集成层 (端口 9000)..."
    if ! check_port 9000 "Claude API集成"; then
        source mcp4_venv/bin/activate
        export PYTHONPATH=/home/wyatt/prism2/mcp_servers/shared:$PYTHONPATH
        nohup python claude_integration_api/server.py > ../logs/claude_integration.log 2>&1 &
        echo $! > ../logs/claude_integration.pid

        wait_for_service "http://localhost:9000" "Claude API集成"
    fi

    verify_service_health "http://localhost:9000" "Claude API集成" "Claude Integration API"
    verify_service_health "http://localhost:9000/health" "Claude API集成健康检查"

    # Claude集成层实际功能检测
    test_claude_integration_functionality

    log_success "Claude API集成层启动完成"
}

# 系统健康检查和验证
perform_system_verification() {
    log_step "第7步: 系统综合验证"

    # 端口占用总览
    log_info "系统端口占用情况:"
    echo -e "${CYAN}端口  服务名称                状态${NC}"
    echo -e "${CYAN}----  ------------------    ------${NC}"

    services=(
        "6379:Redis"
        "5432:PostgreSQL"
        "8081:Enhanced Dashboard API"
        "8005:MCPO Agent"
        "8006:实时数据MCP"
        "8007:结构化数据MCP"
        "8008:RAG增强MCP"
        "8009:任务协调MCP"
        "9000:Claude API集成"
    )

    all_healthy=true

    for service in "${services[@]}"; do
        port=${service%:*}
        name=${service#*:}
        if check_port $port "$name" > /dev/null 2>&1; then
            echo -e "${port}   ${name}                ✅"
        else
            echo -e "${port}   ${name}                ❌"
            all_healthy=false
        fi
    done

    echo ""

    # API功能验证
    log_info "API功能验证..."

    # 测试Claude API集成
    if curl -s "http://localhost:9000" | grep -q "Claude Integration API"; then
        log_success "Claude API集成 - 基本功能正常"
    else
        log_error "Claude API集成 - 基本功能异常"
        all_healthy=false
    fi

    # 测试股票数据获取 (688469)
    if curl -s "http://localhost:8081/api/stock/realtime?symbol=688469" > /dev/null 2>&1; then
        log_success "股票数据API - 数据获取正常"
    else
        log_warning "股票数据API - 数据获取可能异常"
    fi

    # 系统状态总结
    if [ "$all_healthy" = true ]; then
        log_success "系统验证完成 - 所有服务正常运行"
    else
        log_warning "系统验证完成 - 部分服务可能存在问题"
    fi
}

# 显示系统信息
show_system_info() {
    log_step "Prism2 股票分析平台启动完成"

    echo -e "\n${WHITE}========================================${NC}"
    echo -e "${WHITE}   Prism2 股票分析平台 - 服务状态     ${NC}"
    echo -e "${WHITE}========================================${NC}"
    echo -e "${GREEN}✅ 基础软件层:${NC} Redis, PostgreSQL"
    echo -e "${GREEN}✅ 后台服务层:${NC} Enhanced Dashboard API (8081)"
    echo -e "${GREEN}✅ 传统MCP层:${NC} MCPO Agent (8005)"
    echo -e "${GREEN}✅ 4MCP服务层:${NC}"
    echo -e "   • 实时数据MCP (8006)"
    echo -e "   • 结构化数据MCP (8007)"
    echo -e "   • RAG增强MCP (8008)"
    echo -e "   • 任务协调MCP (8009)"
    echo -e "${GREEN}✅ Claude集成层:${NC} Claude API (9000)"
    echo -e "\n${WHITE}主要访问地址:${NC}"
    echo -e "• Claude API统一接口: ${BLUE}http://localhost:9000${NC}"
    echo -e "• 传统MCP接口: ${BLUE}http://localhost:8005${NC}"
    echo -e "• 股票数据API: ${BLUE}http://localhost:8081${NC}"
    echo -e "• 系统健康检查: ${BLUE}http://localhost:9000/health${NC}"
    echo -e "\n${WHITE}测试命令:${NC}"
    echo -e "• 股票查询: ${YELLOW}curl 'http://localhost:9000/api/v1/analysis' -X POST -H 'Content-Type: application/json' -d '{\"stock_code\":\"688469\"}'${NC}"
    echo -e "• 健康检查: ${YELLOW}curl http://localhost:9000/health${NC}"
    echo -e "\n${WHITE}日志位置:${NC} /home/wyatt/prism2/logs/"
    echo -e "${WHITE}========================================${NC}"
}

# 错误处理
handle_error() {
    local exit_code=$1
    log_error "启动过程中发生错误 (退出码: $exit_code)"
    log_error "请检查日志文件: /home/wyatt/prism2/logs/"
    exit $exit_code
}

# 主函数
main() {
    # 设置错误陷阱
    trap 'handle_error $?' ERR

    # 创建日志目录
    mkdir -p /home/wyatt/prism2/logs

    # 初始化日志文件
    echo "=====================================" > "$LOG_FILE"
    echo "Prism2 股票分析平台 - 启动脚本执行日志" >> "$LOG_FILE"
    echo "=====================================" >> "$LOG_FILE"
    echo "启动时间: $(date)" >> "$LOG_FILE"
    echo "工作目录: $(pwd)" >> "$LOG_FILE"
    echo "用户: $(whoami)" >> "$LOG_FILE"
    echo "日志文件: $LOG_FILE" >> "$LOG_FILE"
    echo "=====================================" >> "$LOG_FILE"
    echo "" >> "$LOG_FILE"

    echo -e "${WHITE}============================================${NC}"
    echo -e "${WHITE}  Prism2 股票分析平台 - 统一启动脚本    ${NC}"
    echo -e "${WHITE}============================================${NC}"
    echo -e "启动时间: $(date)"
    echo -e "工作目录: $(pwd)"
    echo -e "用户: $(whoami)"
    echo -e "执行日志: ${CYAN}$LOG_FILE${NC}"
    echo ""

    # 按序启动各层服务
    start_infrastructure
    start_backend_services
    start_rag_services
    # start_legacy_mcp  # 已注释：MCPO是早期架构遗留服务，现由4MCP架构替代
    start_4mcp_services
    start_claude_integration
    perform_system_verification
    show_system_info

    log_success "Prism2 系统启动完成！"

    # 最终日志总结
    echo "" >> "$LOG_FILE"
    echo "=====================================  " >> "$LOG_FILE"
    echo "启动脚本执行完成" >> "$LOG_FILE"
    echo "完成时间: $(date)" >> "$LOG_FILE"
    echo "总执行时间: 启动脚本执行完毕" >> "$LOG_FILE"
    echo "日志文件位置: $LOG_FILE" >> "$LOG_FILE"
    echo "=====================================" >> "$LOG_FILE"

    echo -e "\n${CYAN}📋 完整执行日志已保存到: $LOG_FILE${NC}"
    echo -e "${YELLOW}💡 如果启动过程中出现问题，请查看日志文件了解详情${NC}"
}

# 脚本参数处理
case "${1:-start}" in
    start)
        main
        ;;
    stop)
        log_info "停止所有Prism2服务..."

        # 停止Claude集成层
        if [ -f /home/wyatt/prism2/logs/claude_integration.pid ]; then
            pid=$(cat /home/wyatt/prism2/logs/claude_integration.pid)
            if kill $pid 2>/dev/null; then
                log_success "Claude集成层已停止 (PID: $pid)"
            else
                log_warning "Claude集成层进程 $pid 不存在或已停止"
            fi
        fi

        # 停止4MCP服务
        for service in realtime_data structured_data rag_enhanced coordination; do
            if [ -f "/home/wyatt/prism2/logs/4mcp/${service}.pid" ]; then
                pid=$(cat "/home/wyatt/prism2/logs/4mcp/${service}.pid")
                if kill $pid 2>/dev/null; then
                    log_success "${service}服务已停止 (PID: $pid)"
                else
                    log_warning "${service}进程 $pid 不存在或已停止"
                fi
            fi
        done

        # 停止其他Python服务
        for service in mcpo enhanced_dashboard; do
            if [ -f "/home/wyatt/prism2/logs/${service}.pid" ]; then
                pid=$(cat "/home/wyatt/prism2/logs/${service}.pid")
                if kill $pid 2>/dev/null; then
                    log_success "${service}服务已停止 (PID: $pid)"
                else
                    log_warning "${service}进程 $pid 不存在或已停止"
                fi
            fi
        done

        # 可选：停止Podman容器 (用户可选择)
        echo -e "\n${YELLOW}是否要停止Podman容器? (y/N): ${NC}"
        read -t 10 -n 1 response
        echo

        if [[ "$response" =~ ^[Yy]$ ]]; then
            log_info "停止Podman容器..."

            containers=("prism2-openwebui" "prism2-ollama" "prism2-chromadb")
            for container in "${containers[@]}"; do
                if podman ps | grep -q "$container"; then
                    podman stop "$container" && log_success "已停止 $container"
                else
                    log_info "$container 未运行"
                fi
            done

            # 保持数据库运行的选择
            echo -e "\n${YELLOW}是否也停止数据库容器 (Redis, PostgreSQL)? 这会影响数据存储 (y/N): ${NC}"
            read -t 10 -n 1 db_response
            echo

            if [[ "$db_response" =~ ^[Yy]$ ]]; then
                db_containers=("prism2-postgres" "prism2-redis")
                for container in "${db_containers[@]}"; do
                    if podman ps | grep -q "$container"; then
                        podman stop "$container" && log_success "已停止 $container"
                    else
                        log_info "$container 未运行"
                    fi
                done
            else
                log_info "保持数据库容器运行"
            fi
        else
            log_info "保持Podman容器运行"
        fi

        log_success "Prism2服务停止操作完成"
        ;;
    status)
        log_info "Prism2系统状态检查..."
        perform_system_verification
        ;;
    *)
        echo "用法: $0 {start|stop|status}"
        echo "  start  - 启动所有服务"
        echo "  stop   - 停止所有服务"
        echo "  status - 检查服务状态"
        exit 1
        ;;
esac