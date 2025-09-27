#!/usr/bin/env python3
"""
Prism2 系统快速验证脚本
======================
功能: 快速验证所有服务的功能是否正常，包括数据查询和API响应
版本: 2.0
更新: 2025-09-26
"""

import asyncio
import json
import time
from datetime import datetime
import httpx
import redis
import psycopg2
import sys

# 颜色定义
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    PURPLE = '\033[0;35m'
    CYAN = '\033[0;36m'
    WHITE = '\033[1;37m'
    NC = '\033[0m'

def log_info(msg):
    print(f"{Colors.BLUE}[INFO]{Colors.NC} {msg}")

def log_success(msg):
    print(f"{Colors.GREEN}[SUCCESS]{Colors.NC} {msg}")

def log_warning(msg):
    print(f"{Colors.YELLOW}[WARNING]{Colors.NC} {msg}")

def log_error(msg):
    print(f"{Colors.RED}[ERROR]{Colors.NC} {msg}")

def log_step(msg):
    print(f"\n{Colors.PURPLE}[STEP]{Colors.NC} {msg}")

class Prism2SystemVerifier:
    """Prism2系统验证器"""

    def __init__(self):
        self.test_stock = "688469"  # 测试用股票代码
        self.results = {
            'infrastructure': {},
            'backend': {},
            'mcp_legacy': {},
            'mcp_4services': {},
            'claude_integration': {},
            'functional': {}
        }

    async def verify_infrastructure(self):
        """验证基础设施"""
        log_step("第1步: 验证基础设施")

        # Redis验证
        try:
            r = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
            r.ping()
            # 简单读写测试
            test_key = "prism2_test_key"
            r.set(test_key, "test_value", ex=60)
            if r.get(test_key) == "test_value":
                log_success("Redis - 连接和读写正常")
                self.results['infrastructure']['redis'] = True
            else:
                log_error("Redis - 读写测试失败")
                self.results['infrastructure']['redis'] = False
        except Exception as e:
            log_error(f"Redis - 连接失败: {e}")
            self.results['infrastructure']['redis'] = False

        # PostgreSQL验证
        try:
            conn = psycopg2.connect(
                host="localhost",
                database="stock_data",
                user="postgres",
                password="your_password"  # 需要根据实际配置修改
            )
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public';")
            table_count = cur.fetchone()[0]
            conn.close()

            log_success(f"PostgreSQL - 连接正常，共有 {table_count} 张表")
            self.results['infrastructure']['postgresql'] = True
        except Exception as e:
            log_warning(f"PostgreSQL - 连接测试: {e}")
            self.results['infrastructure']['postgresql'] = False

    async def verify_backend_services(self):
        """验证后台服务"""
        log_step("第2步: 验证后台服务")

        async with httpx.AsyncClient(timeout=10.0) as client:
            # Enhanced Dashboard API
            try:
                # 健康检查
                response = await client.get("http://localhost:8081/health")
                if response.status_code == 200:
                    log_success("Enhanced Dashboard API - 健康检查通过")

                    # 股票数据测试
                    response = await client.get(f"http://localhost:8081/api/stock/realtime?symbol={self.test_stock}")
                    if response.status_code == 200:
                        data = response.json()
                        if 'price' in str(data):
                            log_success(f"Enhanced Dashboard API - 股票数据获取正常 (测试股票: {self.test_stock})")
                            self.results['backend']['enhanced_api'] = True
                        else:
                            log_warning("Enhanced Dashboard API - 股票数据格式异常")
                            self.results['backend']['enhanced_api'] = False
                    else:
                        log_warning(f"Enhanced Dashboard API - 股票数据获取失败: {response.status_code}")
                        self.results['backend']['enhanced_api'] = False
                else:
                    log_error(f"Enhanced Dashboard API - 健康检查失败: {response.status_code}")
                    self.results['backend']['enhanced_api'] = False

            except Exception as e:
                log_error(f"Enhanced Dashboard API - 验证失败: {e}")
                self.results['backend']['enhanced_api'] = False

    async def verify_legacy_mcp(self):
        """验证传统MCP服务"""
        log_step("第3步: 验证传统MCP服务")

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                # MCPO代理验证
                response = await client.get("http://localhost:8005/prism2-stock-analysis/openapi.json")
                if response.status_code == 200:
                    openapi_spec = response.json()
                    if 'paths' in openapi_spec:
                        tool_count = len(openapi_spec['paths'])
                        log_success(f"MCPO Agent - OpenAPI规范正常，发现 {tool_count} 个工具")
                        self.results['mcp_legacy']['mcpo'] = True
                    else:
                        log_warning("MCPO Agent - OpenAPI规范格式异常")
                        self.results['mcp_legacy']['mcpo'] = False
                else:
                    log_error(f"MCPO Agent - OpenAPI获取失败: {response.status_code}")
                    self.results['mcp_legacy']['mcpo'] = False

            except Exception as e:
                log_error(f"MCPO Agent - 验证失败: {e}")
                self.results['mcp_legacy']['mcpo'] = False

    async def verify_4mcp_services(self):
        """验证4MCP服务架构"""
        log_step("第4步: 验证4MCP服务架构")

        mcp_services = {
            '8006': '实时数据MCP',
            '8007': '结构化数据MCP',
            '8008': 'RAG增强MCP',
            '8009': '任务协调MCP'
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            for port, name in mcp_services.items():
                try:
                    # 健康检查
                    response = await client.get(f"http://localhost:{port}/health")
                    if response.status_code == 200:
                        log_success(f"{name} (端口{port}) - 健康检查通过")
                        self.results['mcp_4services'][port] = True
                    else:
                        log_warning(f"{name} (端口{port}) - 健康检查异常: {response.status_code}")
                        self.results['mcp_4services'][port] = False

                except Exception as e:
                    log_error(f"{name} (端口{port}) - 验证失败: {e}")
                    self.results['mcp_4services'][port] = False

    async def verify_claude_integration(self):
        """验证Claude集成层"""
        log_step("第5步: 验证Claude集成层")

        async with httpx.AsyncClient(timeout=15.0) as client:
            try:
                # 基础API验证
                response = await client.get("http://localhost:9000")
                if response.status_code == 200:
                    data = response.json()
                    if 'service' in data and 'Claude Integration API' in data['service']:
                        log_success("Claude API集成 - 基础API正常")

                        # 健康检查
                        response = await client.get("http://localhost:9000/health")
                        if response.status_code == 200:
                            health_data = response.json()
                            log_success(f"Claude API集成 - 健康检查通过，状态: {health_data.get('status')}")

                            # 股票分析测试
                            analysis_request = {
                                "stock_code": self.test_stock,
                                "analysis_type": "quick",
                                "include_claude_insights": True
                            }

                            response = await client.post(
                                "http://localhost:9000/api/v1/analysis",
                                json=analysis_request
                            )

                            if response.status_code == 200:
                                analysis_data = response.json()
                                if 'request_id' in analysis_data:
                                    log_success(f"Claude API集成 - 股票分析功能正常 (请求ID: {analysis_data.get('request_id', 'N/A')[:8]}...)")
                                    self.results['claude_integration']['api'] = True
                                else:
                                    log_warning("Claude API集成 - 股票分析响应格式异常")
                                    self.results['claude_integration']['api'] = False
                            else:
                                log_warning(f"Claude API集成 - 股票分析失败: {response.status_code}")
                                self.results['claude_integration']['api'] = False
                        else:
                            log_error(f"Claude API集成 - 健康检查失败: {response.status_code}")
                            self.results['claude_integration']['api'] = False
                    else:
                        log_error("Claude API集成 - 基础API响应异常")
                        self.results['claude_integration']['api'] = False
                else:
                    log_error(f"Claude API集成 - 基础API访问失败: {response.status_code}")
                    self.results['claude_integration']['api'] = False

            except Exception as e:
                log_error(f"Claude API集成 - 验证失败: {e}")
                self.results['claude_integration']['api'] = False

    async def verify_functional_integration(self):
        """验证功能集成"""
        log_step("第6步: 验证功能集成")

        async with httpx.AsyncClient(timeout=20.0) as client:
            try:
                # 聊天接口测试
                chat_request = {
                    "message": f"请分析股票{self.test_stock}的基本情况",
                    "include_mcp_data": True
                }

                response = await client.post(
                    "http://localhost:9000/api/v1/chat",
                    json=chat_request
                )

                if response.status_code == 200:
                    chat_data = response.json()
                    if 'assistant_response' in chat_data:
                        response_length = len(chat_data['assistant_response'])
                        log_success(f"功能集成 - 聊天接口正常 (回复长度: {response_length}字符)")
                        self.results['functional']['chat'] = True
                    else:
                        log_warning("功能集成 - 聊天接口响应格式异常")
                        self.results['functional']['chat'] = False
                else:
                    log_error(f"功能集成 - 聊天接口失败: {response.status_code}")
                    self.results['functional']['chat'] = False

                # 服务状态查询
                response = await client.get("http://localhost:9000/api/v1/services")
                if response.status_code == 200:
                    services_data = response.json()
                    total_services = services_data.get('summary', {}).get('total_services', 0)
                    log_success(f"功能集成 - 服务状态查询正常 (总服务数: {total_services})")
                    self.results['functional']['services'] = True
                else:
                    log_warning(f"功能集成 - 服务状态查询异常: {response.status_code}")
                    self.results['functional']['services'] = False

            except Exception as e:
                log_error(f"功能集成 - 验证失败: {e}")
                self.results['functional']['chat'] = False
                self.results['functional']['services'] = False

    def generate_report(self):
        """生成验证报告"""
        log_step("系统验证报告")

        print(f"\n{Colors.WHITE}{'='*60}{Colors.NC}")
        print(f"{Colors.WHITE}   Prism2 股票分析平台 - 系统验证报告   {Colors.NC}")
        print(f"{Colors.WHITE}{'='*60}{Colors.NC}")
        print(f"验证时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"测试股票: {self.test_stock}")

        # 统计结果
        total_tests = 0
        passed_tests = 0

        for category, tests in self.results.items():
            category_passed = 0
            category_total = len(tests)

            print(f"\n{Colors.CYAN}【{category.upper()}】{Colors.NC}")

            for test_name, result in tests.items():
                status = f"{Colors.GREEN}✅ 通过{Colors.NC}" if result else f"{Colors.RED}❌ 失败{Colors.NC}"
                print(f"  • {test_name}: {status}")

                if result:
                    category_passed += 1
                    passed_tests += 1
                total_tests += 1

            if category_total > 0:
                success_rate = (category_passed / category_total) * 100
                print(f"  └─ 成功率: {success_rate:.1f}% ({category_passed}/{category_total})")

        # 总体评估
        overall_success_rate = (passed_tests / total_tests) * 100 if total_tests > 0 else 0

        print(f"\n{Colors.WHITE}【总体评估】{Colors.NC}")
        print(f"总测试项: {total_tests}")
        print(f"通过数量: {passed_tests}")
        print(f"总成功率: {overall_success_rate:.1f}%")

        if overall_success_rate >= 90:
            print(f"{Colors.GREEN}🎉 系统状态: 优秀 - 所有核心功能正常{Colors.NC}")
        elif overall_success_rate >= 70:
            print(f"{Colors.YELLOW}⚠️  系统状态: 良好 - 大部分功能正常，建议检查失败项{Colors.NC}")
        else:
            print(f"{Colors.RED}❌ 系统状态: 需要修复 - 多个关键功能异常{Colors.NC}")

        print(f"{Colors.WHITE}{'='*60}{Colors.NC}")

        # 返回状态码
        return 0 if overall_success_rate >= 70 else 1

    async def run_full_verification(self):
        """运行完整验证流程"""
        start_time = time.time()

        print(f"{Colors.WHITE}{'='*60}{Colors.NC}")
        print(f"{Colors.WHITE}   Prism2 系统验证开始   {Colors.NC}")
        print(f"{Colors.WHITE}{'='*60}{Colors.NC}")

        # 按顺序执行验证
        await self.verify_infrastructure()
        await self.verify_backend_services()
        await self.verify_legacy_mcp()
        await self.verify_4mcp_services()
        await self.verify_claude_integration()
        await self.verify_functional_integration()

        # 生成报告
        exit_code = self.generate_report()

        elapsed_time = time.time() - start_time
        print(f"\n{Colors.BLUE}验证耗时: {elapsed_time:.2f} 秒{Colors.NC}")

        return exit_code

async def main():
    """主函数"""
    verifier = Prism2SystemVerifier()
    exit_code = await verifier.run_full_verification()
    sys.exit(exit_code)

if __name__ == "__main__":
    asyncio.run(main())