#!/bin/bash
# ==============================================================
# Prism2 股票分析平台 - 专用停止脚本
# ==============================================================
# 版本: 2.0
# 更新时间: 2025-09-26
# 功能: 安全、智能地停止所有Prism2服务
# ==============================================================

set -e  # 遇到错误立即退出

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "\n${PURPLE}[STEP]${NC} $1"
}

# 检查进程是否存在
check_process() {
    local pid=$1
    if ps -p $pid > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# 安全停止进程
safe_kill_process() {
    local pid=$1
    local service_name=$2
    local timeout=${3:-10}

    if check_process $pid; then
        log_info "停止 $service_name (PID: $pid)..."

        # 先尝试SIGTERM
        if kill $pid 2>/dev/null; then
            local count=0
            while [ $count -lt $timeout ] && check_process $pid; do
                sleep 1
                count=$((count + 1))
            done

            if check_process $pid; then
                log_warning "$service_name 没有响应SIGTERM，使用SIGKILL强制停止..."
                kill -9 $pid 2>/dev/null || true
                sleep 2
                if check_process $pid; then
                    log_error "无法停止 $service_name (PID: $pid)"
                    return 1
                else
                    log_success "$service_name 已强制停止"
                fi
            else
                log_success "$service_name 已正常停止"
            fi
        else
            log_error "无法发送停止信号给 $service_name (PID: $pid)"
            return 1
        fi
    else
        log_info "$service_name (PID: $pid) 进程不存在"
    fi

    return 0
}

# 停止Python服务
stop_python_services() {
    log_step "第1步: 停止Python服务"

    cd /home/wyatt/prism2

    # 定义所有Python服务
    local services=(
        "claude_integration:Claude API集成层"
        "enhanced_dashboard:Enhanced Dashboard API"
        "mcpo:MCPO代理"
    )

    # 定义4MCP服务
    local mcp_services=(
        "realtime_data:实时数据MCP"
        "structured_data:结构化数据MCP"
        "rag_enhanced:RAG增强MCP"
        "coordination:任务协调MCP"
    )

    # 停止主要服务
    for service_info in "${services[@]}"; do
        service_key=${service_info%:*}
        service_name=${service_info#*:}

        if [ -f "logs/${service_key}.pid" ]; then
            pid=$(cat "logs/${service_key}.pid")
            safe_kill_process $pid "$service_name"

            # 清理PID文件
            rm -f "logs/${service_key}.pid"
        else
            log_info "$service_name: 没有PID文件"
        fi
    done

    # 停止4MCP服务
    for service_info in "${mcp_services[@]}"; do
        service_key=${service_info%:*}
        service_name=${service_info#*:}

        if [ -f "logs/4mcp/${service_key}.pid" ]; then
            pid=$(cat "logs/4mcp/${service_key}.pid")
            safe_kill_process $pid "$service_name"

            # 清理PID文件
            rm -f "logs/4mcp/${service_key}.pid"
        else
            log_info "$service_name: 没有PID文件"
        fi
    done

    # 额外检查：按名称查找可能遗漏的Python进程
    log_info "检查可能遗漏的Python进程..."
    local python_processes=$(ps aux | grep -E "(enhanced_dashboard|claude_integration|mcpo)" | grep -v grep | awk '{print $2,$11,$12,$13,$14,$15}' || true)

    if [ -n "$python_processes" ]; then
        echo -e "${YELLOW}发现以下可能的相关进程:${NC}"
        echo "$python_processes"
        echo ""
        echo -e "${YELLOW}是否要停止这些进程? (y/N): ${NC}"
        read -t 10 -n 1 response
        echo ""

        if [[ "$response" =~ ^[Yy]$ ]]; then
            echo "$python_processes" | while read line; do
                if [ -n "$line" ]; then
                    pid=$(echo $line | awk '{print $1}')
                    process_name=$(echo $line | awk '{print $2,$3,$4,$5,$6}')
                    safe_kill_process $pid "遗漏进程: $process_name"
                fi
            done
        fi
    else
        log_success "没有发现遗漏的Python进程"
    fi

    log_success "Python服务停止完成"
}

# 停止容器服务
stop_container_services() {
    log_step "第2步: 停止容器服务"

    # 检查podman是否可用
    if ! command -v podman &> /dev/null; then
        log_warning "Podman 不可用，跳过容器停止"
        return
    fi

    # 显示当前容器状态
    log_info "当前容器状态:"
    podman ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | while read line; do
        echo "    $line"
    done
    echo ""

    # 应用容器 (可以安全停止)
    local app_containers=("prism2-openwebui" "prism2-mcp-server" "prism2-nginx")

    echo -e "${YELLOW}是否停止应用容器 (OpenWebUI, MCP容器, Nginx)? (y/N): ${NC}"
    read -t 10 -n 1 response
    echo ""

    if [[ "$response" =~ ^[Yy]$ ]]; then
        for container in "${app_containers[@]}"; do
            if podman ps | grep -q "$container"; then
                log_info "停止容器: $container"
                if podman stop "$container" --timeout 10; then
                    log_success "已停止 $container"
                else
                    log_error "停止 $container 失败"
                fi
            else
                log_info "$container 未运行"
            fi
        done
    else
        log_info "保持应用容器运行"
    fi

    # AI服务容器 (可选停止)
    local ai_containers=("prism2-ollama" "prism2-chromadb")

    echo -e "\n${YELLOW}是否停止AI服务容器 (Ollama, ChromaDB)? 这会影响AI功能 (y/N): ${NC}"
    read -t 10 -n 1 response
    echo ""

    if [[ "$response" =~ ^[Yy]$ ]]; then
        for container in "${ai_containers[@]}"; do
            if podman ps | grep -q "$container"; then
                log_info "停止容器: $container"
                if podman stop "$container" --timeout 15; then
                    log_success "已停止 $container"
                else
                    log_error "停止 $container 失败"
                fi
            else
                log_info "$container 未运行"
            fi
        done
    else
        log_info "保持AI服务容器运行"
    fi

    # 数据库容器 (危险操作，需要明确确认)
    local db_containers=("prism2-postgres" "prism2-redis")

    echo -e "\n${RED}⚠️  危险操作: 是否停止数据库容器 (PostgreSQL, Redis)? ${NC}"
    echo -e "${RED}这会影响所有数据存储和缓存功能！(y/N): ${NC}"
    read -t 15 -n 1 response
    echo ""

    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo -e "${RED}最后确认: 确定要停止数据库容器吗? 输入 'YES' 确认: ${NC}"
        read -t 10 confirmation

        if [[ "$confirmation" == "YES" ]]; then
            for container in "${db_containers[@]}"; do
                if podman ps | grep -q "$container"; then
                    log_warning "停止数据库容器: $container"
                    if podman stop "$container" --timeout 20; then
                        log_success "已停止 $container"
                    else
                        log_error "停止 $container 失败"
                    fi
                else
                    log_info "$container 未运行"
                fi
            done
        else
            log_info "取消停止数据库容器"
        fi
    else
        log_info "保持数据库容器运行"
    fi

    log_success "容器服务停止完成"
}

# 清理临时文件
cleanup_temp_files() {
    log_step "第3步: 清理临时文件"

    cd /home/wyatt/prism2

    # 清理PID文件
    if [ -d "logs" ]; then
        local pid_files=$(find logs -name "*.pid" 2>/dev/null || true)
        if [ -n "$pid_files" ]; then
            log_info "清理PID文件:"
            echo "$pid_files" | while read pid_file; do
                if [ -n "$pid_file" ]; then
                    echo "  删除: $pid_file"
                    rm -f "$pid_file"
                fi
            done
        fi
    fi

    # 清理临时套接字文件
    local socket_files=$(find /tmp -name "*prism2*" -o -name "*mcp*" 2>/dev/null || true)
    if [ -n "$socket_files" ]; then
        log_info "清理临时套接字文件:"
        echo "$socket_files" | while read socket_file; do
            if [ -n "$socket_file" ]; then
                echo "  删除: $socket_file"
                rm -f "$socket_file"
            fi
        done
    fi

    log_success "临时文件清理完成"
}

# 系统状态验证
verify_shutdown() {
    log_step "第4步: 验证停止状态"

    # 检查端口占用
    local ports=("8005" "8006" "8007" "8008" "8009" "8081" "9000")
    local active_ports=""

    for port in "${ports[@]}"; do
        if netstat -tuln | grep ":$port " > /dev/null 2>&1; then
            active_ports="$active_ports $port"
        fi
    done

    if [ -n "$active_ports" ]; then
        log_warning "以下端口仍在使用:$active_ports"
        echo -e "${YELLOW}详细信息:${NC}"
        for port in $active_ports; do
            echo "端口 $port:"
            lsof -i :$port 2>/dev/null | head -5 || netstat -tuln | grep ":$port "
        done
    else
        log_success "所有Python服务端口已释放"
    fi

    # 检查剩余的Python进程
    local remaining_processes=$(ps aux | grep -E "(python.*prism2|mcpo|enhanced_dashboard|claude_integration)" | grep -v grep || true)
    if [ -n "$remaining_processes" ]; then
        log_warning "发现剩余的相关进程:"
        echo "$remaining_processes"
    else
        log_success "没有发现剩余的Python服务进程"
    fi

    # 显示容器状态
    if command -v podman &> /dev/null; then
        log_info "当前容器状态:"
        podman ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | while read line; do
            echo "    $line"
        done
    fi

    log_success "停止状态验证完成"
}

# 显示停止总结
show_shutdown_summary() {
    log_step "Prism2 服务停止完成"

    echo -e "\n${WHITE}========================================${NC}"
    echo -e "${WHITE}   Prism2 服务停止总结                  ${NC}"
    echo -e "${WHITE}========================================${NC}"
    echo -e "${GREEN}✅ Python服务层:${NC} 已停止所有Python后台服务"
    echo -e "${GREEN}✅ 容器服务层:${NC} 根据用户选择停止相应容器"
    echo -e "${GREEN}✅ 临时文件:${NC} 已清理PID文件和临时文件"
    echo -e "${GREEN}✅ 状态验证:${NC} 已验证服务停止状态"

    echo -e "\n${WHITE}下一步操作:${NC}"
    echo -e "• 重新启动系统: ${BLUE}./start_prism2_system.sh${NC}"
    echo -e "• 检查系统状态: ${BLUE}./start_prism2_system.sh status${NC}"
    echo -e "• 测试启动逻辑: ${BLUE}./test_startup_logic.sh${NC}"

    echo -e "\n${YELLOW}注意事项:${NC}"
    echo -e "• 如果数据库容器被停止，下次启动需要更多时间"
    echo -e "• 某些持久化数据可能需要重新初始化"
    echo -e "• 建议在重启后运行完整的系统验证"

    echo -e "\n${WHITE}停止时间: $(date)${NC}"
    echo -e "${WHITE}========================================${NC}"
}

# 主函数
main() {
    echo -e "${WHITE}============================================${NC}"
    echo -e "${WHITE}  Prism2 股票分析平台 - 服务停止脚本    ${NC}"
    echo -e "${WHITE}============================================${NC}"
    echo -e "停止时间: $(date)"
    echo -e "工作目录: $(pwd)"
    echo -e "用户: $(whoami)"

    echo -e "\n${YELLOW}⚠️  注意: 此脚本将停止Prism2相关服务${NC}"
    echo -e "${YELLOW}请确保没有重要操作正在进行${NC}"
    echo ""
    echo -e "${YELLOW}是否继续? (y/N): ${NC}"
    read -t 15 -n 1 response
    echo ""

    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        log_info "用户取消操作"
        exit 0
    fi

    stop_python_services
    stop_container_services
    cleanup_temp_files
    verify_shutdown
    show_shutdown_summary

    log_success "Prism2 系统停止脚本执行完成"
}

# 参数处理
case "${1:-interactive}" in
    interactive)
        main
        ;;
    force)
        log_warning "强制停止模式 - 将停止所有服务而不询问"
        # 在强制模式下设置自动回答
        export response="y"
        stop_python_services

        # 强制停止所有容器
        if command -v podman &> /dev/null; then
            log_info "强制停止所有Prism2容器..."
            local all_containers=("prism2-openwebui" "prism2-mcp-server" "prism2-nginx" "prism2-ollama" "prism2-chromadb")
            for container in "${all_containers[@]}"; do
                if podman ps | grep -q "$container"; then
                    podman stop "$container" --timeout 5 2>/dev/null && log_success "强制停止 $container" || log_warning "停止 $container 失败"
                fi
            done
        fi

        cleanup_temp_files
        log_success "强制停止完成"
        ;;
    soft)
        log_info "温和停止模式 - 只停止Python服务，保留容器"
        stop_python_services
        cleanup_temp_files
        log_success "温和停止完成"
        ;;
    *)
        echo "用法: $0 {interactive|force|soft}"
        echo "  interactive - 交互式停止 (默认)"
        echo "  force       - 强制停止所有服务"
        echo "  soft        - 只停止Python服务，保留容器"
        exit 1
        ;;
esac