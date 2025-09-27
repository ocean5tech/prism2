#!/usr/bin/env python3
"""
Claude API Integration Layer (Port 9000)

Provides a unified API interface that integrates Claude AI with the 4MCP architecture.
Acts as the main entry point for frontend applications and external integrations.
"""

import asyncio
import json
import httpx
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta
import uuid
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Shared modules imports
import sys
import os
sys.path.append('/home/wyatt/prism2/mcp_servers/shared')

from config import config
from logger import get_logger
from database import data_manager

logger = get_logger("Claude-Integration")

# Initialize FastAPI app
app = FastAPI(
    title="Claude Integration API",
    description="Unified API for Claude AI + 4MCP Architecture",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 在生产环境中应该限制为特定域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MCPOrchestrator:
    """MCP服务编排器 - 与Claude AI集成的核心组件"""

    def __init__(self):
        self.mcp_services = {
            "realtime_data": "http://localhost:8006",
            "structured_data": "http://localhost:8007",
            "rag_enhanced": "http://localhost:8008",
            "coordination": "http://localhost:8009"
        }
        self.session_history = {}

    async def call_mcp_service(self, service_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """调用MCP服务"""
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
                    return {"success": True, "data": result}
                else:
                    return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}

        except Exception as e:
            logger.error(f"MCP服务调用失败: {service_name}.{tool_name} - {e}")
            return {"success": False, "error": str(e)}

    async def get_claude_enhanced_analysis(self, query: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """获取Claude增强的分析结果"""
        try:
            # 这里应该调用Claude API，暂时使用模拟实现
            analysis_prompt = f"""
            基于以下用户查询和上下文数据，提供专业的金融分析：

            用户查询: {query}

            上下文数据: {json.dumps(context, ensure_ascii=False, indent=2) if context else "无"}

            请提供结构化的分析，包括：
            1. 数据解读
            2. 风险评估
            3. 投资建议
            4. 注意事项
            """

            # 模拟Claude API响应
            claude_response = {
                "analysis": f"基于查询'{query}'的专业分析",
                "key_insights": [
                    "数据显示当前市场趋势稳定",
                    "建议关注技术面指标变化",
                    "风险控制仍为首要考虑"
                ],
                "recommendations": [
                    "短期内保持观望态度",
                    "长期可考虑分批建仓",
                    "设置合理的止损位"
                ],
                "confidence_level": 0.85,
                "generated_at": datetime.now().isoformat()
            }

            return {"success": True, "data": claude_response}

        except Exception as e:
            logger.error(f"Claude API调用失败: {e}")
            return {"success": False, "error": str(e)}

# 全局MCP编排器实例
mcp_orchestrator = MCPOrchestrator()

# Pydantic模型定义
class AnalysisRequest(BaseModel):
    stock_code: str
    analysis_type: str = "standard"
    include_claude_insights: bool = True
    user_query: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None
    include_mcp_data: bool = True
    stock_context: Optional[List[str]] = None

class HealthCheckResponse(BaseModel):
    status: str
    timestamp: str
    services: Dict[str, Any]

# API路由定义

@app.get("/")
async def root():
    """API根路径"""
    return {
        "service": "Claude Integration API",
        "version": "1.0.0",
        "description": "Unified API for Claude AI + 4MCP Architecture",
        "endpoints": {
            "/health": "健康检查",
            "/api/v1/analysis": "股票分析",
            "/api/v1/chat": "智能对话",
            "/api/v1/services": "服务状态"
        }
    }

@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """健康检查端点"""
    try:
        # 检查数据库连接
        db_health = await data_manager.health_check()

        # 检查MCP服务状态
        mcp_health = {}
        for service_name, base_url in mcp_orchestrator.mcp_services.items():
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.get(f"{base_url}/health")
                    mcp_health[service_name] = {
                        "status": "healthy" if response.status_code == 200 else "unhealthy",
                        "url": base_url
                    }
            except:
                mcp_health[service_name] = {
                    "status": "unreachable",
                    "url": base_url
                }

        return HealthCheckResponse(
            status="healthy",
            timestamp=datetime.now().isoformat(),
            services={
                "database": db_health,
                "mcp_services": mcp_health
            }
        )

    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/analysis")
async def comprehensive_analysis(request: AnalysisRequest):
    """综合股票分析接口"""
    try:
        logger.info(f"开始分析股票 {request.stock_code}")

        # Step 1: 调用协调服务执行综合分析
        coordination_result = await mcp_orchestrator.call_mcp_service(
            "coordination",
            "comprehensive_stock_analysis",
            {
                "stock_code": request.stock_code,
                "analysis_type": request.analysis_type,
                "include_forecast": False
            }
        )

        analysis_data = {
            "stock_code": request.stock_code,
            "analysis_type": request.analysis_type,
            "mcp_analysis": coordination_result,
            "timestamp": datetime.now().isoformat()
        }

        # Step 2: 如果需要Claude洞察，调用Claude API
        if request.include_claude_insights and coordination_result.get("success"):
            claude_query = request.user_query or f"请分析股票{request.stock_code}的投资价值"
            claude_result = await mcp_orchestrator.get_claude_enhanced_analysis(
                claude_query,
                coordination_result.get("data")
            )
            analysis_data["claude_insights"] = claude_result

        # Step 3: 格式化综合结果
        response_data = {
            "request_id": str(uuid.uuid4()),
            "stock_code": request.stock_code,
            "analysis_summary": {
                "mcp_services_called": len(mcp_orchestrator.mcp_services),
                "data_sources_count": _count_data_sources(coordination_result),
                "analysis_completeness": _calculate_completeness(coordination_result),
                "claude_enhancement": request.include_claude_insights
            },
            "detailed_results": analysis_data,
            "recommendations": _generate_recommendations(analysis_data),
            "metadata": {
                "generated_at": datetime.now().isoformat(),
                "processing_time": "N/A",  # 实际实现中应该计算真实时间
                "api_version": "1.0.0"
            }
        }

        logger.info(f"股票 {request.stock_code} 分析完成")
        return response_data

    except Exception as e:
        logger.error(f"分析请求处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/chat")
async def intelligent_chat(request: ChatRequest):
    """智能对话接口"""
    try:
        session_id = request.session_id or str(uuid.uuid4())
        logger.info(f"处理对话请求 - Session: {session_id}")

        # 初始化会话历史
        if session_id not in mcp_orchestrator.session_history:
            mcp_orchestrator.session_history[session_id] = []

        # 添加用户消息到历史
        mcp_orchestrator.session_history[session_id].append({
            "role": "user",
            "content": request.message,
            "timestamp": datetime.now().isoformat()
        })

        response_data = {
            "session_id": session_id,
            "user_message": request.message,
            "timestamp": datetime.now().isoformat()
        }

        # 如果需要MCP数据支持
        if request.include_mcp_data:
            # 分析用户消息，提取股票代码等信息
            extracted_stocks = _extract_stock_codes(request.message)

            if extracted_stocks:
                logger.info(f"从消息中提取到股票代码: {extracted_stocks}")

                # 获取相关股票的基础数据
                stock_data = {}
                for stock_code in extracted_stocks[:3]:  # 限制最多3个股票
                    realtime_result = await mcp_orchestrator.call_mcp_service(
                        "structured_data",
                        "get_historical_data",
                        {"stock_code": stock_code, "period": "daily", "limit": 5}
                    )
                    stock_data[stock_code] = realtime_result

                response_data["mcp_data"] = {
                    "extracted_stocks": extracted_stocks,
                    "stock_data": stock_data
                }

        # 生成Claude响应
        claude_context = {
            "user_message": request.message,
            "session_history": mcp_orchestrator.session_history[session_id][-5:],  # 最近5轮对话
            "mcp_data": response_data.get("mcp_data")
        }

        claude_response = await mcp_orchestrator.get_claude_enhanced_analysis(
            f"作为金融助手回复: {request.message}",
            claude_context
        )

        # 构建最终响应
        assistant_message = "基于您的询问，我来为您提供分析："

        if claude_response.get("success"):
            claude_data = claude_response.get("data", {})
            assistant_message = claude_data.get("analysis", assistant_message)

        # 添加助手响应到历史
        mcp_orchestrator.session_history[session_id].append({
            "role": "assistant",
            "content": assistant_message,
            "timestamp": datetime.now().isoformat()
        })

        response_data.update({
            "assistant_response": assistant_message,
            "claude_insights": claude_response,
            "session_length": len(mcp_orchestrator.session_history[session_id])
        })

        logger.info(f"对话处理完成 - Session: {session_id}")
        return response_data

    except Exception as e:
        logger.error(f"对话请求处理失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/services")
async def get_service_status():
    """获取所有服务状态"""
    try:
        # 调用协调服务获取详细状态
        health_result = await mcp_orchestrator.call_mcp_service(
            "coordination",
            "service_health_check",
            {"detailed": True}
        )

        service_stats = {
            "claude_integration": {
                "status": "healthy",
                "port": 9000,
                "uptime": "N/A",  # 实际实现中应该计算真实运行时间
                "requests_processed": "N/A"
            },
            "mcp_cluster": health_result.get("data") if health_result.get("success") else {"error": "无法获取MCP集群状态"},
            "database": await data_manager.health_check(),
            "summary": {
                "total_services": len(mcp_orchestrator.mcp_services) + 1,  # +1 for Claude Integration
                "timestamp": datetime.now().isoformat(),
                "integration_ready": health_result.get("success", False)
            }
        }

        return service_stats

    except Exception as e:
        logger.error(f"服务状态查询失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# 辅助函数

def _count_data_sources(coordination_result: Dict[str, Any]) -> int:
    """计算数据源数量"""
    if not coordination_result.get("success"):
        return 0

    # 简单计算，实际实现中应该更精确
    return 3  # Redis, PostgreSQL, API

def _calculate_completeness(coordination_result: Dict[str, Any]) -> float:
    """计算分析完整度"""
    if not coordination_result.get("success"):
        return 0.0

    # 基于协调服务的成功率
    data = coordination_result.get("data", {})
    if isinstance(data, str):
        # 简单的字符串长度启发式
        return min(1.0, len(data) / 1000.0)

    return 0.8  # 默认完整度

def _generate_recommendations(analysis_data: Dict[str, Any]) -> List[str]:
    """生成投资建议"""
    recommendations = [
        "建议结合多个数据源进行综合判断",
        "注意控制投资风险，不要过度集中持仓",
        "定期关注公司财务报表和行业动态"
    ]

    # 根据分析结果调整建议
    if analysis_data.get("claude_insights", {}).get("success"):
        claude_recs = analysis_data["claude_insights"]["data"].get("recommendations", [])
        recommendations.extend(claude_recs)

    return recommendations

def _extract_stock_codes(message: str) -> List[str]:
    """从消息中提取股票代码"""
    import re

    # 简单的股票代码提取模式
    patterns = [
        r'\b\d{6}\b',  # 6位数字
        r'\b[A-Z]{2,4}\b'  # 2-4位字母
    ]

    stock_codes = []
    for pattern in patterns:
        matches = re.findall(pattern, message.upper())
        stock_codes.extend(matches)

    return list(set(stock_codes))  # 去重

@app.on_event("startup")
async def startup_event():
    """应用启动事件"""
    logger.info("Claude Integration API 启动中...")
    logger.info("初始化MCP服务连接...")

    # 这里可以添加启动时的初始化逻辑
    logger.info("Claude Integration API 启动完成 - Port 9000")

@app.on_event("shutdown")
async def shutdown_event():
    """应用关闭事件"""
    logger.info("Claude Integration API 关闭中...")

if __name__ == "__main__":
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=9000,
        reload=False,
        log_level="info"
    )