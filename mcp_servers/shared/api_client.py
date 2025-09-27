#!/usr/bin/env python3
"""
Shared API client utilities for external services
"""

import asyncio
import httpx
import requests
import akshare as ak
from typing import Dict, Any, Optional, List
from config import config
from logger import get_logger
import time

logger = get_logger("APIClient")

class EnhancedDashboardAPIClient:
    """Client for Enhanced Dashboard API"""

    def __init__(self):
        self.base_url = config.external_apis.enhanced_dashboard_url
        self.timeout = config.mcp_servers.request_timeout

    async def call_dashboard_api(self, stock_code: str, data_types: List[str]) -> Dict[str, Any]:
        """Call Enhanced Dashboard API"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.base_url}/api/v1/stocks/dashboard",
                    json={
                        "stock_code": stock_code,
                        "data_types": data_types
                    }
                )

                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"Enhanced Dashboard API success for {stock_code}: {data_types}")
                    return {
                        "success": True,
                        "data": data,
                        "source": "enhanced_dashboard_api"
                    }
                else:
                    logger.warning(f"Enhanced Dashboard API returned {response.status_code} for {stock_code}")
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}",
                        "source": "enhanced_dashboard_api"
                    }

        except httpx.TimeoutException:
            logger.error(f"Enhanced Dashboard API timeout for {stock_code}")
            return {
                "success": False,
                "error": "Request timeout",
                "source": "enhanced_dashboard_api"
            }
        except Exception as e:
            logger.error(f"Enhanced Dashboard API error for {stock_code}: {e}")
            return {
                "success": False,
                "error": str(e),
                "source": "enhanced_dashboard_api"
            }

class RAGServiceClient:
    """Client for RAG Service"""

    def __init__(self):
        self.base_url = config.external_apis.rag_service_url
        self.timeout = config.mcp_servers.request_timeout

    async def query_rag(self, query: str, stock_code: Optional[str] = None) -> Dict[str, Any]:
        """Query RAG service for background information"""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                payload = {"query": query}
                if stock_code:
                    payload["stock_code"] = stock_code

                response = await client.post(
                    f"{self.base_url}/api/v2/query",
                    json=payload
                )

                if response.status_code == 200:
                    data = response.json()
                    logger.info(f"RAG service success for query: {query[:50]}...")
                    return {
                        "success": True,
                        "data": data,
                        "source": "rag_service"
                    }
                else:
                    logger.warning(f"RAG service returned {response.status_code}")
                    return {
                        "success": False,
                        "error": f"HTTP {response.status_code}: {response.text}",
                        "source": "rag_service"
                    }

        except httpx.TimeoutException:
            logger.error(f"RAG service timeout for query: {query[:50]}...")
            return {
                "success": False,
                "error": "Request timeout",
                "source": "rag_service"
            }
        except Exception as e:
            logger.error(f"RAG service error: {e}")
            return {
                "success": False,
                "error": str(e),
                "source": "rag_service"
            }

    async def health_check(self) -> bool:
        """Check if RAG service is healthy"""
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(f"{self.base_url}/api/v2/heartbeat")
                return response.status_code == 200
        except Exception:
            return False

class AKShareClient:
    """Client for AKShare data"""

    def __init__(self):
        self.timeout = config.external_apis.akshare_timeout

    def get_realtime_price(self, stock_code: str) -> Dict[str, Any]:
        """Get real-time stock price from AKShare"""
        try:
            # Convert stock code format for AKShare
            if stock_code.startswith('6'):
                symbol = f"{stock_code}.SH"
            elif stock_code.startswith('0') or stock_code.startswith('3'):
                symbol = f"{stock_code}.SZ"
            elif stock_code.startswith('688') or stock_code.startswith('689'):
                symbol = f"{stock_code}.SH"
            else:
                symbol = stock_code

            # Get real-time data
            df = ak.stock_zh_a_spot_em()
            stock_data = df[df['代码'] == stock_code]

            if not stock_data.empty:
                row = stock_data.iloc[0]
                result = {
                    "success": True,
                    "data": {
                        "code": stock_code,
                        "name": row['名称'],
                        "current_price": row['最新价'],
                        "change_percent": row['涨跌幅'],
                        "change_amount": row['涨跌额'],
                        "volume": row['成交量'],
                        "turnover": row['成交额'],
                        "high": row['最高'],
                        "low": row['最低'],
                        "open": row['今开'],
                        "yesterday_close": row['昨收'],
                        "timestamp": time.time()
                    },
                    "source": "akshare_realtime"
                }
                logger.info(f"AKShare real-time data success for {stock_code}")
                return result
            else:
                logger.warning(f"No real-time data found for {stock_code} in AKShare")
                return {
                    "success": False,
                    "error": f"No data found for {stock_code}",
                    "source": "akshare_realtime"
                }

        except Exception as e:
            logger.error(f"AKShare real-time data error for {stock_code}: {e}")
            return {
                "success": False,
                "error": str(e),
                "source": "akshare_realtime"
            }

    def get_historical_data(self, stock_code: str, period: str = "daily", adjust: str = "qfq") -> Dict[str, Any]:
        """Get historical stock data from AKShare"""
        try:
            # Get historical data
            df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period=period,
                adjust=adjust,
                start_date="20240101",
                end_date="20241231"
            )

            if not df.empty:
                # Convert DataFrame to list of dictionaries
                data_list = []
                for _, row in df.iterrows():
                    data_list.append({
                        "date": row['日期'].strftime('%Y-%m-%d'),
                        "open": float(row['开盘']),
                        "close": float(row['收盘']),
                        "high": float(row['最高']),
                        "low": float(row['最低']),
                        "volume": int(row['成交量']),
                        "turnover": float(row['成交额'])
                    })

                result = {
                    "success": True,
                    "data": {
                        "code": stock_code,
                        "period": period,
                        "adjust": adjust,
                        "kline_data": data_list,
                        "total_records": len(data_list)
                    },
                    "source": "akshare_historical"
                }
                logger.info(f"AKShare historical data success for {stock_code}: {len(data_list)} records")
                return result
            else:
                logger.warning(f"No historical data found for {stock_code} in AKShare")
                return {
                    "success": False,
                    "error": f"No historical data found for {stock_code}",
                    "source": "akshare_historical"
                }

        except Exception as e:
            logger.error(f"AKShare historical data error for {stock_code}: {e}")
            return {
                "success": False,
                "error": str(e),
                "source": "akshare_historical"
            }

    def get_financial_data(self, stock_code: str) -> Dict[str, Any]:
        """Get financial data from AKShare"""
        try:
            # Get financial data
            df = ak.stock_financial_hk_report_em(symbol=stock_code)

            if not df.empty:
                # Convert to list of dictionaries
                financial_list = []
                for _, row in df.iterrows():
                    financial_list.append({
                        "report_date": row['报告期'].strftime('%Y-%m-%d'),
                        "revenue": row.get('营业总收入', 0),
                        "net_profit": row.get('净利润', 0),
                        "roe": row.get('净资产收益率', 0),
                        "roa": row.get('总资产收益率', 0),
                        "debt_ratio": row.get('资产负债率', 0),
                        "eps": row.get('每股收益', 0)
                    })

                result = {
                    "success": True,
                    "data": {
                        "code": stock_code,
                        "financial_data": financial_list,
                        "total_records": len(financial_list)
                    },
                    "source": "akshare_financial"
                }
                logger.info(f"AKShare financial data success for {stock_code}: {len(financial_list)} records")
                return result
            else:
                logger.warning(f"No financial data found for {stock_code} in AKShare")
                return {
                    "success": False,
                    "error": f"No financial data found for {stock_code}",
                    "source": "akshare_financial"
                }

        except Exception as e:
            logger.error(f"AKShare financial data error for {stock_code}: {e}")
            return {
                "success": False,
                "error": str(e),
                "source": "akshare_financial"
            }

# Global instances
enhanced_dashboard_client = EnhancedDashboardAPIClient()
rag_service_client = RAGServiceClient()
akshare_client = AKShareClient()