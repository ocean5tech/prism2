#!/usr/bin/env python3
"""
Task Coordination MCP Server (Port 8009)

Orchestrates complex tasks across multiple MCP servers and provides
intelligent workflow management for financial analysis.
"""

import asyncio
import json
import httpx
from typing import Any, Dict, List, Optional, Sequence, Union
from datetime import datetime, timedelta
import uuid

# MCP SDK imports
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel,
    CallToolRequest,
    ListToolsRequest,
    ListResourcesRequest,
    ReadResourceRequest
)

# Shared modules imports
import sys
import os
sys.path.append('/home/wyatt/prism2/mcp_servers/shared')

from config import config
from logger import get_logger, log_mcp_call
from database import data_manager

logger = get_logger("Coordination-MCP")

# Initialize MCP server
server = Server("coordination-mcp")

class TaskOrchestrator:
    """任务编排器 - 协调多个MCP服务完成复杂任务"""

    def __init__(self):
        self.mcp_services = {
            "realtime_data": "http://localhost:8006",
            "structured_data": "http://localhost:8007",
            "rag_enhanced": "http://localhost:8008"
        }
        self.task_history = []
        self.active_workflows = {}

    async def call_mcp_service(self, service_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用指定MCP服务的工具"""
        try:
            if service_name not in self.mcp_services:
                return {"success": False, "error": f"未知的MCP服务: {service_name}"}

            base_url = self.mcp_services[service_name]

            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{base_url}/call_tool",
                    json={
                        "method": "tools/call",
                        "params": {
                            "name": tool_name,
                            "arguments": arguments
                        }
                    }
                )

                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"成功调用 {service_name}.{tool_name}")
                    return {"success": True, "data": result}
                else:
                    logger.warning(f"MCP服务调用失败: {service_name}.{tool_name} - {response.status_code}")
                    return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}

        except httpx.TimeoutException:
            logger.error(f"MCP服务调用超时: {service_name}.{tool_name}")
            return {"success": False, "error": "服务调用超时"}
        except Exception as e:
            logger.error(f"MCP服务调用异常: {service_name}.{tool_name} - {e}")
            return {"success": False, "error": str(e)}

    async def execute_comprehensive_analysis(self, stock_code: str, analysis_type: str = "full") -> Dict[str, Any]:
        """执行综合分析工作流"""
        workflow_id = str(uuid.uuid4())[:8]
        logger.info(f"启动综合分析工作流 {workflow_id} for {stock_code}")

        workflow_results = {
            "workflow_id": workflow_id,
            "stock_code": stock_code,
            "analysis_type": analysis_type,
            "start_time": datetime.now().isoformat(),
            "steps": [],
            "final_summary": None
        }

        try:
            # Step 1: 获取实时数据
            logger.info(f"[{workflow_id}] Step 1: 获取实时数据")
            realtime_result = await self.call_mcp_service(
                "realtime_data",
                "get_realtime_price",
                {"stock_code": stock_code}
            )
            workflow_results["steps"].append({
                "step": 1,
                "name": "实时数据获取",
                "success": realtime_result["success"],
                "data": realtime_result.get("data"),
                "timestamp": datetime.now().isoformat()
            })

            # Step 2: 获取历史数据和财务信息
            logger.info(f"[{workflow_id}] Step 2: 获取结构化数据")
            historical_result = await self.call_mcp_service(
                "structured_data",
                "get_historical_data",
                {"stock_code": stock_code, "period": "daily", "limit": 30}
            )
            workflow_results["steps"].append({
                "step": 2,
                "name": "历史数据获取",
                "success": historical_result["success"],
                "data": historical_result.get("data"),
                "timestamp": datetime.now().isoformat()
            })

            # Step 3: 获取财务报表
            if analysis_type in ["full", "financial"]:
                logger.info(f"[{workflow_id}] Step 3: 获取财务报表")
                financial_result = await self.call_mcp_service(
                    "structured_data",
                    "get_financial_reports",
                    {"stock_code": stock_code, "report_type": "all", "periods": 4}
                )
                workflow_results["steps"].append({
                    "step": 3,
                    "name": "财务报表获取",
                    "success": financial_result["success"],
                    "data": financial_result.get("data"),
                    "timestamp": datetime.now().isoformat()
                })

            # Step 4: RAG增强分析
            logger.info(f"[{workflow_id}] Step 4: RAG背景分析")
            rag_context_result = await self.call_mcp_service(
                "rag_enhanced",
                "search_financial_context",
                {"query": f"{stock_code} 最新动态 投资分析", "stock_code": stock_code, "max_results": 5}
            )
            workflow_results["steps"].append({
                "step": 4,
                "name": "RAG背景分析",
                "success": rag_context_result["success"],
                "data": rag_context_result.get("data"),
                "timestamp": datetime.now().isoformat()
            })

            # Step 5: 新闻情感分析
            logger.info(f"[{workflow_id}] Step 5: 新闻情感分析")
            sentiment_result = await self.call_mcp_service(
                "rag_enhanced",
                "get_news_sentiment",
                {"stock_code": stock_code, "days": 7}
            )
            workflow_results["steps"].append({
                "step": 5,
                "name": "新闻情感分析",
                "success": sentiment_result["success"],
                "data": sentiment_result.get("data"),
                "timestamp": datetime.now().isoformat()
            })

            # Step 6: 生成市场洞察
            if analysis_type == "full":
                logger.info(f"[{workflow_id}] Step 6: 生成市场洞察")
                insight_result = await self.call_mcp_service(
                    "rag_enhanced",
                    "generate_market_insight",
                    {
                        "topic": f"{stock_code} 综合投资分析",
                        "stock_codes": [stock_code],
                        "analysis_depth": "comprehensive"
                    }
                )
                workflow_results["steps"].append({
                    "step": 6,
                    "name": "市场洞察生成",
                    "success": insight_result["success"],
                    "data": insight_result.get("data"),
                    "timestamp": datetime.now().isoformat()
                })

            # 生成最终综合分析摘要
            workflow_results["final_summary"] = self._generate_workflow_summary(workflow_results)
            workflow_results["end_time"] = datetime.now().isoformat()
            workflow_results["duration"] = self._calculate_duration(workflow_results["start_time"], workflow_results["end_time"])

            # 保存到工作流历史
            self.task_history.append(workflow_results)

            logger.info(f"工作流 {workflow_id} 完成，耗时 {workflow_results['duration']}")
            return workflow_results

        except Exception as e:
            logger.error(f"工作流 {workflow_id} 执行失败: {e}")
            workflow_results["error"] = str(e)
            workflow_results["end_time"] = datetime.now().isoformat()
            return workflow_results

    def _generate_workflow_summary(self, workflow_results: Dict[str, Any]) -> Dict[str, Any]:
        """生成工作流执行摘要"""
        successful_steps = [step for step in workflow_results["steps"] if step["success"]]
        failed_steps = [step for step in workflow_results["steps"] if not step["success"]]

        return {
            "total_steps": len(workflow_results["steps"]),
            "successful_steps": len(successful_steps),
            "failed_steps": len(failed_steps),
            "success_rate": len(successful_steps) / len(workflow_results["steps"]) * 100 if workflow_results["steps"] else 0,
            "completed_tasks": [step["name"] for step in successful_steps],
            "failed_tasks": [step["name"] for step in failed_steps] if failed_steps else [],
            "status": "completed" if len(failed_steps) == 0 else "partial_failure" if successful_steps else "failed"
        }

    def _calculate_duration(self, start_time: str, end_time: str) -> str:
        """计算工作流执行时间"""
        try:
            start = datetime.fromisoformat(start_time)
            end = datetime.fromisoformat(end_time)
            duration = end - start
            return f"{duration.total_seconds():.2f}秒"
        except:
            return "未知"

    async def health_check_all_services(self) -> Dict[str, Any]:
        """检查所有MCP服务的健康状态"""
        health_status = {}

        for service_name, base_url in self.mcp_services.items():
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(f"{base_url}/health")
                    health_status[service_name] = {
                        "status": "healthy" if response.status_code == 200 else "unhealthy",
                        "response_code": response.status_code,
                        "url": base_url
                    }
            except Exception as e:
                health_status[service_name] = {
                    "status": "unreachable",
                    "error": str(e),
                    "url": base_url
                }

        return health_status

# 初始化任务编排器
task_orchestrator = TaskOrchestrator()

@server.list_tools()
async def handle_list_tools() -> List[Tool]:
    """列出可用工具"""
    return [
        Tool(
            name="comprehensive_stock_analysis",
            description="执行全面的股票综合分析。协调多个MCP服务提供完整的投资分析报告，包括实时数据、历史表现、财务状况、市场情感等。",
            inputSchema={
                "type": "object",
                "properties": {
                    "stock_code": {
                        "type": "string",
                        "description": "股票代码，如'688469'"
                    },
                    "analysis_type": {
                        "type": "string",
                        "enum": ["quick", "standard", "full"],
                        "description": "分析深度：快速、标准、全面",
                        "default": "standard"
                    },
                    "include_forecast": {
                        "type": "boolean",
                        "description": "是否包含趋势预测",
                        "default": False
                    }
                },
                "required": ["stock_code"]
            }
        ),
        Tool(
            name="cross_service_query",
            description="跨服务查询工具。可以同时查询多个MCP服务并整合结果。用于获取特定信息的综合视图。",
            inputSchema={
                "type": "object",
                "properties": {
                    "query_plan": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "service": {"type": "string"},
                                "tool": {"type": "string"},
                                "arguments": {"type": "object"}
                            },
                            "required": ["service", "tool", "arguments"]
                        },
                        "description": "查询计划，包含要调用的服务、工具和参数"
                    },
                    "parallel_execution": {
                        "type": "boolean",
                        "description": "是否并行执行查询",
                        "default": True
                    }
                },
                "required": ["query_plan"]
            }
        ),
        Tool(
            name="workflow_status",
            description="查看工作流执行状态和历史记录。可以查询特定工作流的详细信息或获取历史执行统计。",
            inputSchema={
                "type": "object",
                "properties": {
                    "workflow_id": {
                        "type": "string",
                        "description": "工作流ID，可选，如不提供则返回最近的工作流"
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回的历史记录数量",
                        "default": 10
                    }
                }
            }
        ),
        Tool(
            name="service_health_check",
            description="检查所有MCP服务的健康状态。用于监控系统状态和诊断服务可用性问题。",
            inputSchema={
                "type": "object",
                "properties": {
                    "detailed": {
                        "type": "boolean",
                        "description": "是否返回详细的健康检查信息",
                        "default": False
                    }
                }
            }
        )
    ]

@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> Sequence[TextContent]:
    """处理工具调用请求"""

    log_mcp_call(logger, name, arguments)

    try:
        if name == "comprehensive_stock_analysis":
            return await _handle_comprehensive_stock_analysis(arguments)
        elif name == "cross_service_query":
            return await _handle_cross_service_query(arguments)
        elif name == "workflow_status":
            return await _handle_workflow_status(arguments)
        elif name == "service_health_check":
            return await _handle_service_health_check(arguments)
        else:
            error_msg = f"未知的工具: {name}"
            log_mcp_call(logger, name, arguments, error=error_msg)
            return [TextContent(type="text", text=f"❌ 错误: {error_msg}")]

    except Exception as e:
        error_msg = f"工具调用异常: {str(e)}"
        log_mcp_call(logger, name, arguments, error=error_msg)
        return [TextContent(type="text", text=f"❌ 错误: {error_msg}")]

async def _handle_comprehensive_stock_analysis(arguments: dict) -> Sequence[TextContent]:
    """处理综合股票分析"""

    stock_code = arguments.get("stock_code", "")
    analysis_type = arguments.get("analysis_type", "standard")
    include_forecast = arguments.get("include_forecast", False)

    if not stock_code:
        return [TextContent(type="text", text="❌ 股票代码不能为空")]

    # 执行综合分析工作流
    workflow_result = await task_orchestrator.execute_comprehensive_analysis(stock_code, analysis_type)

    # 格式化结果
    result_text = f"📊 {stock_code} 综合分析报告\n"
    result_text += f"🆔 工作流ID: {workflow_result['workflow_id']}\n"
    result_text += f"📅 分析时间: {workflow_result['start_time'][:19]}\n"
    result_text += f"⏱️ 执行耗时: {workflow_result.get('duration', '未知')}\n"
    result_text += f"📈 分析深度: {analysis_type}\n\n"

    # 工作流执行摘要
    summary = workflow_result.get("final_summary", {})
    if summary:
        result_text += f"### 📋 执行摘要\n"
        result_text += f"• 总步骤: {summary['total_steps']}\n"
        result_text += f"• 成功步骤: {summary['successful_steps']}\n"
        result_text += f"• 成功率: {summary['success_rate']:.1f}%\n"
        result_text += f"• 状态: {summary['status']}\n\n"

        # 成功完成的任务
        if summary['completed_tasks']:
            result_text += f"✅ **完成的任务**:\n"
            for task in summary['completed_tasks']:
                result_text += f"  • {task}\n"
            result_text += "\n"

        # 失败的任务
        if summary['failed_tasks']:
            result_text += f"❌ **失败的任务**:\n"
            for task in summary['failed_tasks']:
                result_text += f"  • {task}\n"
            result_text += "\n"

    # 详细步骤结果
    result_text += f"### 📝 详细分析结果\n"
    for step in workflow_result["steps"]:
        status_icon = "✅" if step["success"] else "❌"
        result_text += f"{status_icon} **{step['name']}** (Step {step['step']})\n"

        if step["success"] and step.get("data"):
            # 简化显示数据内容
            data_preview = str(step["data"])[:200] + "..." if len(str(step["data"])) > 200 else str(step["data"])
            result_text += f"   结果: {data_preview}\n"
        elif not step["success"]:
            result_text += f"   失败原因: 服务调用失败\n"

        result_text += f"   时间: {step['timestamp'][:19]}\n\n"

    # 综合建议
    result_text += f"### 💡 投资建议\n"
    if summary.get("success_rate", 0) >= 80:
        result_text += f"✅ 数据获取完整，可信度高，建议基于以上分析进行投资决策。\n"
    elif summary.get("success_rate", 0) >= 50:
        result_text += f"⚠️ 部分数据获取成功，建议结合其他信息源综合判断。\n"
    else:
        result_text += f"❌ 数据获取不足，建议稍后重试或检查服务状态。\n"

    result_text += f"\n📋 如需查看详细工作流状态，请使用工作流ID: {workflow_result['workflow_id']}"

    log_mcp_call(logger, "comprehensive_stock_analysis", arguments, {
        "workflow_id": workflow_result['workflow_id'],
        "success_rate": summary.get("success_rate", 0)
    })

    return [TextContent(type="text", text=result_text)]

async def _handle_cross_service_query(arguments: dict) -> Sequence[TextContent]:
    """处理跨服务查询"""

    query_plan = arguments.get("query_plan", [])
    parallel_execution = arguments.get("parallel_execution", True)

    if not query_plan:
        return [TextContent(type="text", text="❌ 查询计划不能为空")]

    result_text = f"🔍 跨服务查询结果\n"
    result_text += f"📋 查询数量: {len(query_plan)}\n"
    result_text += f"⚡ 执行方式: {'并行' if parallel_execution else '串行'}\n"
    result_text += f"🕐 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    results = []

    if parallel_execution:
        # 并行执行
        tasks = []
        for i, query in enumerate(query_plan):
            task = task_orchestrator.call_mcp_service(
                query["service"],
                query["tool"],
                query["arguments"]
            )
            tasks.append((i, query, task))

        # 等待所有任务完成
        for i, query, task in tasks:
            try:
                result = await task
                results.append({
                    "index": i + 1,
                    "service": query["service"],
                    "tool": query["tool"],
                    "success": result["success"],
                    "result": result
                })
            except Exception as e:
                results.append({
                    "index": i + 1,
                    "service": query["service"],
                    "tool": query["tool"],
                    "success": False,
                    "error": str(e)
                })
    else:
        # 串行执行
        for i, query in enumerate(query_plan):
            try:
                result = await task_orchestrator.call_mcp_service(
                    query["service"],
                    query["tool"],
                    query["arguments"]
                )
                results.append({
                    "index": i + 1,
                    "service": query["service"],
                    "tool": query["tool"],
                    "success": result["success"],
                    "result": result
                })
            except Exception as e:
                results.append({
                    "index": i + 1,
                    "service": query["service"],
                    "tool": query["tool"],
                    "success": False,
                    "error": str(e)
                })

    # 格式化结果
    successful_queries = [r for r in results if r["success"]]
    failed_queries = [r for r in results if not r["success"]]

    result_text += f"### 📊 执行统计\n"
    result_text += f"• 成功查询: {len(successful_queries)}/{len(results)}\n"
    result_text += f"• 成功率: {len(successful_queries)/len(results)*100:.1f}%\n\n"

    # 成功的查询
    if successful_queries:
        result_text += f"### ✅ 成功查询结果\n"
        for r in successful_queries:
            result_text += f"**{r['index']}. {r['service']}.{r['tool']}**\n"
            data_preview = str(r["result"].get("data", ""))[:150] + "..." if len(str(r["result"].get("data", ""))) > 150 else str(r["result"].get("data", ""))
            result_text += f"   结果: {data_preview}\n\n"

    # 失败的查询
    if failed_queries:
        result_text += f"### ❌ 失败查询\n"
        for r in failed_queries:
            result_text += f"**{r['index']}. {r['service']}.{r['tool']}**\n"
            result_text += f"   错误: {r.get('error', '未知错误')}\n\n"

    log_mcp_call(logger, "cross_service_query", arguments, {
        "total_queries": len(results),
        "successful_queries": len(successful_queries)
    })

    return [TextContent(type="text", text=result_text)]

async def _handle_workflow_status(arguments: dict) -> Sequence[TextContent]:
    """处理工作流状态查询"""

    workflow_id = arguments.get("workflow_id")
    limit = arguments.get("limit", 10)

    if workflow_id:
        # 查询特定工作流
        workflow = None
        for w in task_orchestrator.task_history:
            if w["workflow_id"] == workflow_id:
                workflow = w
                break

        if not workflow:
            return [TextContent(type="text", text=f"❌ 未找到工作流ID: {workflow_id}")]

        result_text = f"🔍 工作流详情\n"
        result_text += f"🆔 工作流ID: {workflow['workflow_id']}\n"
        result_text += f"📊 股票代码: {workflow['stock_code']}\n"
        result_text += f"📈 分析类型: {workflow['analysis_type']}\n"
        result_text += f"🕐 开始时间: {workflow['start_time'][:19]}\n"
        result_text += f"🕐 结束时间: {workflow.get('end_time', '进行中')[:19] if workflow.get('end_time') else '进行中'}\n"
        result_text += f"⏱️ 执行时间: {workflow.get('duration', '未知')}\n\n"

        # 步骤详情
        result_text += f"### 📋 执行步骤详情\n"
        for step in workflow["steps"]:
            status_icon = "✅" if step["success"] else "❌"
            result_text += f"{status_icon} **Step {step['step']}: {step['name']}**\n"
            result_text += f"   执行时间: {step['timestamp'][:19]}\n"

            if step["success"]:
                result_text += f"   状态: 成功\n"
            else:
                result_text += f"   状态: 失败\n"
            result_text += "\n"

        # 最终摘要
        summary = workflow.get("final_summary", {})
        if summary:
            result_text += f"### 📊 执行摘要\n"
            result_text += f"• 总步骤: {summary['total_steps']}\n"
            result_text += f"• 成功步骤: {summary['successful_steps']}\n"
            result_text += f"• 成功率: {summary['success_rate']:.1f}%\n"
            result_text += f"• 最终状态: {summary['status']}\n"

    else:
        # 查询工作流历史
        history = task_orchestrator.task_history[-limit:] if task_orchestrator.task_history else []

        result_text = f"📊 工作流历史记录\n"
        result_text += f"📋 显示最近 {len(history)} 条记录\n\n"

        if not history:
            result_text += "暂无工作流执行记录。\n"
        else:
            for workflow in reversed(history):
                summary = workflow.get("final_summary", {})
                status_icon = "✅" if summary.get("status") == "completed" else "⚠️" if summary.get("status") == "partial_failure" else "❌"

                result_text += f"{status_icon} **{workflow['workflow_id']}** - {workflow['stock_code']}\n"
                result_text += f"   类型: {workflow['analysis_type']}\n"
                result_text += f"   时间: {workflow['start_time'][:19]}\n"
                result_text += f"   时长: {workflow.get('duration', '未知')}\n"
                if summary:
                    result_text += f"   成功率: {summary['success_rate']:.1f}%\n"
                result_text += "\n"

        # 统计信息
        if history:
            total_workflows = len(history)
            completed_workflows = len([w for w in history if w.get("final_summary", {}).get("status") == "completed"])
            avg_success_rate = sum([w.get("final_summary", {}).get("success_rate", 0) for w in history]) / len(history)

            result_text += f"### 📈 统计信息\n"
            result_text += f"• 总工作流: {total_workflows}\n"
            result_text += f"• 完全成功: {completed_workflows}\n"
            result_text += f"• 平均成功率: {avg_success_rate:.1f}%\n"

    log_mcp_call(logger, "workflow_status", arguments, {"query_type": "specific" if workflow_id else "history"})

    return [TextContent(type="text", text=result_text)]

async def _handle_service_health_check(arguments: dict) -> Sequence[TextContent]:
    """处理服务健康检查"""

    detailed = arguments.get("detailed", False)

    # 执行健康检查
    health_status = await task_orchestrator.health_check_all_services()

    result_text = f"🏥 MCP服务健康检查报告\n"
    result_text += f"🕐 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    result_text += f"📊 服务总数: {len(health_status)}\n\n"

    # 统计健康状态
    healthy_services = [s for s in health_status.values() if s["status"] == "healthy"]
    unhealthy_services = [s for s in health_status.values() if s["status"] != "healthy"]

    result_text += f"### 📊 总体状态\n"
    result_text += f"• 健康服务: {len(healthy_services)}/{len(health_status)}\n"
    result_text += f"• 服务可用率: {len(healthy_services)/len(health_status)*100:.1f}%\n\n"

    # 详细服务状态
    result_text += f"### 📋 服务详情\n"
    for service_name, status_info in health_status.items():
        status_icon = "✅" if status_info["status"] == "healthy" else "❌"

        result_text += f"{status_icon} **{service_name.replace('_', ' ').title()}**\n"
        result_text += f"   状态: {status_info['status']}\n"

        if detailed:
            result_text += f"   地址: {status_info['url']}\n"
            if "response_code" in status_info:
                result_text += f"   响应码: {status_info['response_code']}\n"
            if "error" in status_info:
                result_text += f"   错误信息: {status_info['error']}\n"

        result_text += "\n"

    # 建议
    if len(unhealthy_services) > 0:
        result_text += f"### ⚠️ 注意事项\n"
        result_text += f"发现 {len(unhealthy_services)} 个服务不健康，建议:\n"
        result_text += f"• 检查相关服务是否正常启动\n"
        result_text += f"• 验证网络连接和端口配置\n"
        result_text += f"• 查看服务日志排查问题\n"
    else:
        result_text += f"### 🎉 系统状态良好\n"
        result_text += f"所有MCP服务运行正常，可以执行完整的分析工作流。\n"

    log_mcp_call(logger, "service_health_check", arguments, {
        "total_services": len(health_status),
        "healthy_services": len(healthy_services)
    })

    return [TextContent(type="text", text=result_text)]

async def main():
    """主函数 - 启动MCP服务器"""
    logger.info("启动 Task Coordination MCP Server (端口8009)")

    # 运行MCP服务器
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="coordination-mcp",
                server_version="1.0.0",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={}
                )
            )
        )

if __name__ == "__main__":
    asyncio.run(main())