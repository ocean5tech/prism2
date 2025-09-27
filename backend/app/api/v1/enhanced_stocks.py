# -*- coding: utf-8 -*-
"""
增强的股票API - 集成完整日志记录
"""
import logging
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_db, get_redis_stock, get_redis_search
from app.services.enhanced_akshare_service import enhanced_akshare_service
from app.utils.logger import api_logger, log_api_calls
from app.schemas.stock import (
    StockSearchRequest, StockSearchResponse, StockSearchItem,
    StockInfo, RealtimeData, KLineData,
    DashboardRequest, DashboardResponse,
    ErrorResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


class LoggedStockService:
    """带日志记录的股票服务"""

    def __init__(self, db: Session):
        self.db = db
        self.akshare_service = enhanced_akshare_service

    @log_api_calls(api_logger)
    def search_stocks(self, query: str, limit: int = 10) -> List[StockSearchItem]:
        """股票搜索 - 带日志记录"""
        start_time = datetime.now()

        try:
            # 调用AKShare服务
            stocks = self.akshare_service.get_stock_list()

            # 过滤搜索结果
            results = []
            for stock in stocks:
                if (query.lower() in stock['name'].lower() or
                    query in stock['code'] or
                    query.lower() in stock['market'].lower()):
                    results.append(StockSearchItem(
                        code=stock['code'],
                        name=stock['name'],
                        market=stock['market']
                    ))

                if len(results) >= limit:
                    break

            execution_time = (datetime.now() - start_time).total_seconds()

            # 记录API日志
            api_logger.log_api_call(
                endpoint="search_stocks",
                method="GET",
                request_data={"query": query, "limit": limit},
                response_data={"results_count": len(results), "total_checked": len(stocks)},
                status_code=200,
                execution_time=execution_time
            )

            return results

        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()

            # 记录错误日志
            api_logger.log_api_call(
                endpoint="search_stocks",
                method="GET",
                request_data={"query": query, "limit": limit},
                response_data={"error": str(e)},
                status_code=500,
                execution_time=execution_time
            )
            raise

    @log_api_calls(api_logger)
    def get_stock_info(self, stock_code: str) -> StockInfo:
        """获取股票基本信息 - 带日志记录"""
        start_time = datetime.now()

        try:
            # 调用AKShare服务
            stock_data = self.akshare_service.get_stock_info(stock_code)

            if not stock_data:
                raise HTTPException(status_code=404, detail=f"Stock {stock_code} not found")

            # 判断市场
            market = "SH" if stock_code.startswith(('60', '68')) else "SZ"

            result = StockInfo(
                code=stock_data['code'],
                name=stock_data['name'],
                market=market,
                market_cap=stock_data.get('market_cap'),
                pe_ratio=stock_data.get('pe_ratio'),
                pb_ratio=stock_data.get('pb_ratio')
            )

            execution_time = (datetime.now() - start_time).total_seconds()

            # 记录API日志
            api_logger.log_api_call(
                endpoint="get_stock_info",
                method="GET",
                request_data={"stock_code": stock_code},
                response_data={"name": result.name, "market": result.market},
                status_code=200,
                execution_time=execution_time
            )

            return result

        except HTTPException:
            raise
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()

            # 记录错误日志
            api_logger.log_api_call(
                endpoint="get_stock_info",
                method="GET",
                request_data={"stock_code": stock_code},
                response_data={"error": str(e)},
                status_code=500,
                execution_time=execution_time
            )
            raise HTTPException(status_code=500, detail="Internal server error")

    @log_api_calls(api_logger)
    def get_realtime_data(self, stock_code: str) -> RealtimeData:
        """获取实时数据 - 带日志记录"""
        start_time = datetime.now()

        try:
            # 调用AKShare服务
            realtime_data = self.akshare_service.get_realtime_data(stock_code)

            if not realtime_data:
                raise HTTPException(status_code=404, detail=f"Realtime data for {stock_code} not found")

            result = RealtimeData(
                current_price=realtime_data['current_price'],
                change_amount=realtime_data['change_amount'],
                change_percent=realtime_data['change_percent'],
                volume=realtime_data['volume'],
                turnover=realtime_data['turnover'],
                high=realtime_data['high'],
                low=realtime_data['low'],
                open=realtime_data['open'],
                timestamp=datetime.now()
            )

            execution_time = (datetime.now() - start_time).total_seconds()

            # 记录API日志
            api_logger.log_api_call(
                endpoint="get_realtime_data",
                method="GET",
                request_data={"stock_code": stock_code},
                response_data={
                    "current_price": result.current_price,
                    "change_percent": result.change_percent,
                    "volume": result.volume
                },
                status_code=200,
                execution_time=execution_time
            )

            return result

        except HTTPException:
            raise
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()

            # 记录错误日志
            api_logger.log_api_call(
                endpoint="get_realtime_data",
                method="GET",
                request_data={"stock_code": stock_code},
                response_data={"error": str(e)},
                status_code=500,
                execution_time=execution_time
            )
            raise HTTPException(status_code=500, detail="Internal server error")


def get_logged_stock_service(db: Session = Depends(get_db)) -> LoggedStockService:
    """获取带日志记录的股票服务实例"""
    return LoggedStockService(db)


# API路由定义

@router.get("/stocks/search", response_model=StockSearchResponse)
async def search_stocks(
    request: Request,
    query: str = Query(..., description="搜索关键词"),
    limit: int = Query(10, ge=1, le=50, description="结果数量限制"),
    stock_service: LoggedStockService = Depends(get_logged_stock_service)
):
    """
    股票搜索API
    支持股票代码、名称搜索
    """
    start_time = datetime.now()

    try:
        logger.info(f"Stock search request: query={query}, limit={limit}")

        # 获取客户端IP
        client_ip = request.client.host

        # 执行搜索
        results = stock_service.search_stocks(query, limit)

        execution_time = (datetime.now() - start_time).total_seconds()

        # 记录API调用日志
        api_logger.log_api_call(
            endpoint="/stocks/search",
            method="GET",
            request_data={"query": query, "limit": limit},
            response_data={"results_count": len(results)},
            status_code=200,
            execution_time=execution_time,
            client_ip=client_ip
        )

        return StockSearchResponse(
            success=True,
            query=query,
            results=results,
            total=len(results)
        )

    except Exception as e:
        execution_time = (datetime.now() - start_time).total_seconds()

        logger.error(f"Stock search error: {e}")

        # 记录错误日志
        api_logger.log_api_call(
            endpoint="/stocks/search",
            method="GET",
            request_data={"query": query, "limit": limit},
            response_data={"error": str(e)},
            status_code=500,
            execution_time=execution_time,
            client_ip=getattr(request.client, 'host', 'unknown')
        )

        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="SEARCH_ERROR",
                error_message=f"搜索失败: {str(e)}",
                timestamp=datetime.now()
            ).dict()
        )


@router.get("/stocks/{stock_code}/info", response_model=StockInfo)
async def get_stock_info(
    request: Request,
    stock_code: str,
    stock_service: LoggedStockService = Depends(get_logged_stock_service)
):
    """
    获取股票基本信息
    集成Redis → PostgreSQL → AKShare三层架构
    """
    start_time = datetime.now()

    try:
        logger.info(f"Stock info request: {stock_code}")

        # 获取客户端IP
        client_ip = request.client.host

        # 获取股票信息
        stock_info = stock_service.get_stock_info(stock_code)
        execution_time = (datetime.now() - start_time).total_seconds()

        # 记录API调用日志
        api_logger.log_api_call(
            endpoint=f"/stocks/{stock_code}/info",
            method="GET",
            request_data={"stock_code": stock_code},
            response_data={"name": stock_info.name, "market": stock_info.market},
            status_code=200,
            execution_time=execution_time,
            client_ip=client_ip
        )

        return stock_info

    except HTTPException:
        raise
    except Exception as e:
        execution_time = (datetime.now() - start_time).total_seconds()

        logger.error(f"Get stock info error: {e}")

        # 记录错误日志
        api_logger.log_api_call(
            endpoint=f"/stocks/{stock_code}/info",
            method="GET",
            request_data={"stock_code": stock_code},
            response_data={"error": str(e)},
            status_code=500,
            execution_time=execution_time,
            client_ip=getattr(request.client, 'host', 'unknown')
        )

        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="STOCK_INFO_ERROR",
                error_message=f"获取股票信息失败: {str(e)}",
                timestamp=datetime.now()
            ).dict()
        )


@router.get("/stocks/{stock_code}/realtime", response_model=RealtimeData)
async def get_realtime_data(
    request: Request,
    stock_code: str,
    stock_service: LoggedStockService = Depends(get_logged_stock_service)
):
    """
    获取股票实时数据
    使用AKShare获取最新数据
    """
    start_time = datetime.now()

    try:
        logger.info(f"Realtime data request: {stock_code}")

        # 获取客户端IP
        client_ip = request.client.host

        # 获取实时数据
        realtime_data = stock_service.get_realtime_data(stock_code)
        execution_time = (datetime.now() - start_time).total_seconds()

        # 记录API调用日志
        api_logger.log_api_call(
            endpoint=f"/stocks/{stock_code}/realtime",
            method="GET",
            request_data={"stock_code": stock_code},
            response_data={
                "current_price": realtime_data.current_price,
                "change_percent": realtime_data.change_percent
            },
            status_code=200,
            execution_time=execution_time,
            client_ip=client_ip
        )

        return realtime_data

    except HTTPException:
        raise
    except Exception as e:
        execution_time = (datetime.now() - start_time).total_seconds()

        logger.error(f"Get realtime data error: {e}")

        # 记录错误日志
        api_logger.log_api_call(
            endpoint=f"/stocks/{stock_code}/realtime",
            method="GET",
            request_data={"stock_code": stock_code},
            response_data={"error": str(e)},
            status_code=500,
            execution_time=execution_time,
            client_ip=getattr(request.client, 'host', 'unknown')
        )

        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="REALTIME_DATA_ERROR",
                error_message=f"获取实时数据失败: {str(e)}",
                timestamp=datetime.now()
            ).dict()
        )