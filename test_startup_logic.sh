#!/bin/bash
# ==============================================================
# Prism2 启动逻辑测试脚本
# ==============================================================
# 功能: 测试启动脚本的基础设施启动逻辑（不实际启动服务）
# ==============================================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m'

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

# 测试基础设施启动逻辑
test_infrastructure_logic() {
    log_step "测试基础设施启动逻辑"

    # 检查podman是否可用
    if command -v podman &> /dev/null; then
        log_success "✅ Podman 命令可用"
    else
        log_error "❌ Podman 命令不可用"
        return 1
    fi

    # 显示当前容器状态
    log_info "当前容器状态:"
    podman ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | while read line; do
        echo "    $line"
    done

    # 检查各个容器
    containers=("prism2-redis" "prism2-postgres" "prism2-chromadb" "prism2-ollama" "prism2-openwebui")

    for container in "${containers[@]}"; do
        log_info "检查容器: $container"

        if podman ps -a | grep -q "$container"; then
            if podman ps | grep -q "$container"; then
                log_success "  ✅ $container 正在运行"
            else
                log_warning "  ⚠️  $container 存在但未运行"
                log_info "  📝 启动命令: podman start $container"
            fi
        else
            log_warning "  ❌ $container 不存在"
        fi
    done

    echo ""
}

# 测试端口检查逻辑
test_port_logic() {
    log_step "测试端口检查逻辑"

    ports=(
        "6379:Redis"
        "5432:PostgreSQL"
        "8003:ChromaDB"
        "8081:Enhanced Dashboard API"
        "8005:MCPO Agent"
        "8006:实时数据MCP"
        "8007:结构化数据MCP"
        "8008:RAG增强MCP"
        "8009:任务协调MCP"
        "9000:Claude API集成"
        "11434:Ollama"
        "3001:OpenWebUI"
    )

    for port_info in "${ports[@]}"; do
        port=${port_info%:*}
        name=${port_info#*:}

        if check_port $port "$name" > /dev/null 2>&1; then
            echo -e "  ${port}: ${name} ✅"
        else
            echo -e "  ${port}: ${name} ❌"
        fi
    done

    echo ""
}

# 测试文件和目录检查
test_file_structure() {
    log_step "测试文件结构检查"

    # 检查关键文件和目录
    files_dirs=(
        "/home/wyatt/prism2:项目根目录"
        "/home/wyatt/prism2/backend:后台服务目录"
        "/home/wyatt/prism2/backend/enhanced_dashboard_api.py:数据API文件"
        "/home/wyatt/prism2/test_venv:测试虚拟环境"
        "/home/wyatt/prism2/mcp_servers:MCP服务器目录"
        "/home/wyatt/prism2/mcp_servers/mcp4_venv:4MCP虚拟环境"
        "/home/wyatt/prism2/mcp_servers/claude_integration_api:Claude集成目录"
        "/home/wyatt/prism2/logs:日志目录"
    )

    for item in "${files_dirs[@]}"; do
        path=${item%:*}
        desc=${item#*:}

        if [ -e "$path" ]; then
            if [ -d "$path" ]; then
                log_success "  ✅ 目录存在: $desc ($path)"
            else
                log_success "  ✅ 文件存在: $desc ($path)"
            fi
        else
            log_warning "  ❌ 不存在: $desc ($path)"
        fi
    done

    echo ""
}

# 模拟启动逻辑测试
simulate_startup_logic() {
    log_step "模拟启动逻辑测试"

    log_info "如果现在运行真正的启动脚本，会发生什么:"

    # 基础设施层模拟
    echo -e "\n${CYAN}【基础设施层】${NC}"
    containers=("prism2-redis" "prism2-postgres" "prism2-chromadb")

    for container in "${containers[@]}"; do
        if podman ps | grep -q "$container"; then
            echo "  ✅ $container: 已运行，跳过启动"
        elif podman ps -a | grep -q "$container"; then
            echo "  🔄 $container: 将执行 'podman start $container'"
        else
            echo "  ❌ $container: 容器不存在，需要先创建"
        fi
    done

    # 后台服务层模拟
    echo -e "\n${CYAN}【后台服务层】${NC}"
    if check_port 8081 "Enhanced Dashboard API" > /dev/null 2>&1; then
        echo "  ✅ Enhanced Dashboard API: 已运行，跳过启动"
    else
        if [ -f "/home/wyatt/prism2/backend/enhanced_dashboard_api.py" ]; then
            echo "  🔄 Enhanced Dashboard API: 将启动Python服务"
        else
            echo "  ❌ Enhanced Dashboard API: 文件不存在"
        fi
    fi

    # 4MCP服务层模拟
    echo -e "\n${CYAN}【4MCP服务层】${NC}"
    mcp_ports=("8006:实时数据MCP" "8007:结构化数据MCP" "8008:RAG增强MCP" "8009:任务协调MCP")

    for port_info in "${mcp_ports[@]}"; do
        port=${port_info%:*}
        name=${port_info#*:}

        if check_port $port "$name" > /dev/null 2>&1; then
            echo "  ✅ $name: 已运行，跳过启动"
        else
            echo "  🔄 $name: 将启动MCP服务器"
        fi
    done

    # Claude集成层模拟
    echo -e "\n${CYAN}【Claude集成层】${NC}"
    if check_port 9000 "Claude API集成" > /dev/null 2>&1; then
        echo "  ✅ Claude API集成: 已运行，跳过启动"
    else
        if [ -f "/home/wyatt/prism2/mcp_servers/claude_integration_api/server.py" ]; then
            echo "  🔄 Claude API集成: 将启动Python服务"
        else
            echo "  ❌ Claude API集成: 文件不存在"
        fi
    fi

    echo ""
}

# 主函数
main() {
    echo -e "${WHITE}============================================${NC}"
    echo -e "${WHITE}  Prism2 启动逻辑测试脚本               ${NC}"
    echo -e "${WHITE}============================================${NC}"
    echo -e "测试时间: $(date)"
    echo ""

    test_infrastructure_logic
    test_port_logic
    test_file_structure
    simulate_startup_logic

    echo -e "${WHITE}============================================${NC}"
    log_success "启动逻辑测试完成"
    echo ""
    echo -e "${YELLOW}💡 提示：${NC}"
    echo "• 如果看到很多 ✅，说明系统当前状态良好"
    echo "• 如果看到 ❌，说明需要先解决这些问题"
    echo "• 🔄 表示启动脚本会尝试启动该服务"
    echo ""
    echo -e "${BLUE}下一步操作：${NC}"
    echo "• 运行完整启动脚本: ./start_prism2_system.sh"
    echo "• 只检查状态: ./start_prism2_system.sh status"
    echo -e "${WHITE}============================================${NC}"
}

# 运行测试
main