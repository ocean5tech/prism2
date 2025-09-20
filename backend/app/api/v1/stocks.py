"""
¡hpnAPI
úŽ01-úš¥ãÄ.mdšI„¥ã
"""
import logging
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from redis import Redis

from app.core.database import get_db, get_redis_stock, get_redis_search
from app.services.stock_service import StockService
from app.schemas.stock import (
    StockSearchRequest, StockSearchResponse, StockSearchItem,
    StockInfo, RealtimeData, KLineData,
    DashboardRequest, DashboardResponse,
    ErrorResponse
)

logger = logging.getLogger(__name__)

router = APIRouter()


def get_stock_service(
    db: Session = Depends(get_db),
    redis_stock: Redis = Depends(get_redis_stock),
    redis_search: Redis = Depends(get_redis_search)
) -> StockService:
    """·Ö¡h¡ž‹"""
    return StockService(db, redis_stock, redis_search)


@router.get("/stocks/search", response_model=StockSearchResponse)
async def search_stocks(
    query: str = Query(..., description=""s.Í¡hãð	"),
    limit: int = Query(10, ge=1, le=50, description="ÔÞÓœpÏP6"),
    stock_service: StockService = Depends(get_stock_service)
):
    """
    ¡h"API
    /¡hãŒð„!Ê"
    """
    try:
        logger.info(f"Stock search request: query={query}, limit={limit}")

        # gL"
        results = stock_service.search_stocks(query, limit)

        return StockSearchResponse(
            success=True,
            query=query,
            results=results,
            total=len(results)
        )

    except Exception as e:
        logger.error(f"Stock search error: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="SEARCH_ERROR",
                error_message=f""1%: {str(e)}",
                timestamp=datetime.now()
            ).dict()
        )


@router.get("/stocks/{stock_code}/info", response_model=StockInfo)
async def get_stock_info(
    stock_code: str,
    stock_service: StockService = Depends(get_stock_service)
):
    """
    ·Ö¡hú@áo
    	§åâRedis ’ PostgreSQL ’ AKShare
    """
    try:
        logger.info(f"Stock info request: {stock_code}")

        stock_info = stock_service.get_stock_info(stock_code)
        if not stock_info:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error_code="STOCK_NOT_FOUND",
                    error_message=f"¡h {stock_code} *~0",
                    timestamp=datetime.now()
                ).dict()
            )

        return stock_info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get stock info error: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="STOCK_INFO_ERROR",
                error_message=f"·Ö¡háo1%: {str(e)}",
                timestamp=datetime.now()
            ).dict()
        )


@router.get("/stocks/{stock_code}/realtime", response_model=RealtimeData)
async def get_realtime_data(
    stock_code: str,
    stock_service: StockService = Depends(get_stock_service)
):
    """
    ·Ö¡hžö÷<pn
    ô¥ÎAKShare·ÖÝÁžö'
    """
    try:
        logger.info(f"Realtime data request: {stock_code}")

        realtime_data = stock_service.get_realtime_data(stock_code)
        if not realtime_data:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error_code="REALTIME_DATA_NOT_FOUND",
                    error_message=f"¡h {stock_code} žöpn*~0",
                    timestamp=datetime.now()
                ).dict()
            )

        return realtime_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get realtime data error: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="REALTIME_DATA_ERROR",
                error_message=f"·Öžöpn1%: {str(e)}",
                timestamp=datetime.now()
            ).dict()
        )


@router.post("/stocks/dashboard", response_model=DashboardResponse)
async def get_dashboard_data(
    request: DashboardRequest,
    stock_service: StockService = Depends(get_stock_service)
):
    """
    ·ÖDashboardüpn
    /Ípn{‹„Ä·Ö
    pn{‹basic_info, realtime, kline, financial, news, announcements, longhubang, ai_analysis
    """
    try:
        logger.info(f"Dashboard request: stock_code={request.stock_code}, data_types={request.data_types}")

        # ŒÁ¡hã<
        if not request.stock_code or len(request.stock_code) != 6:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error_code="INVALID_STOCK_CODE",
                    error_message="¡hã<cn”:6MpW",
                    timestamp=datetime.now()
                ).dict()
            )

        # ŒÁpn{‹
        valid_types = {"basic_info", "realtime", "kline", "financial", "news", "announcements", "longhubang", "ai_analysis"}
        invalid_types = set(request.data_types) - valid_types
        if invalid_types:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error_code="INVALID_DATA_TYPES",
                    error_message=f"àH„pn{‹: {invalid_types}",
                    timestamp=datetime.now()
                ).dict()
            )

        # ·ÖDashboardpn
        dashboard_data = stock_service.get_dashboard_data(request)

        return DashboardResponse(
            success=True,
            stock_code=request.stock_code,
            timestamp=datetime.now(),
            data=dashboard_data
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Dashboard data error: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="DASHBOARD_ERROR",
                error_message=f"·ÖDashboardpn1%: {str(e)}",
                timestamp=datetime.now()
            ).dict()
        )


@router.get("/stocks/{stock_code}/kline", response_model=KLineData)
async def get_kline_data(
    stock_code: str,
    period: str = Query("daily", description="K¿hdaily, weekly, monthly"),
    stock_service: StockService = Depends(get_stock_service)
):
    """
    ·ÖK¿pn
    	§åâRedis ’ PostgreSQL ’ AKShare
    """
    try:
        logger.info(f"K-line data request: {stock_code}, period={period}")

        # ŒÁhÂp
        valid_periods = {"daily", "weekly", "monthly"}
        if period not in valid_periods:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error_code="INVALID_PERIOD",
                    error_message=f"àH„K¿h: {period}",
                    timestamp=datetime.now()
                ).dict()
            )

        kline_data = stock_service.get_kline_data(stock_code, period)
        if not kline_data:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error_code="KLINE_DATA_NOT_FOUND",
                    error_message=f"¡h {stock_code} K¿pn*~0",
                    timestamp=datetime.now()
                ).dict()
            )

        return kline_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get K-line data error: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error_code="KLINE_DATA_ERROR",
                error_message=f"·ÖK¿pn1%: {str(e)}",
                timestamp=datetime.now()
            ).dict()
        )