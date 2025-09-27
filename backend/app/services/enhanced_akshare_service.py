# -*- coding: utf-8 -*-
"""
增强的AKShare服务 - 集成完整日志记录
"""
import logging
import time
import os
from typing import List, Dict, Any, Optional
from functools import wraps
import pandas as pd

try:
    import akshare as ak
    AKSHARE_AVAILABLE = True
except ImportError:
    AKSHARE_AVAILABLE = False

from app.utils.logger import akshare_logger, log_akshare_calls

logger = logging.getLogger(__name__)


def clear_proxy_for_akshare():
    """清除代理环境变量，确保AKShare正常工作"""
    proxy_vars = ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']
    for var in proxy_vars:
        if var in os.environ:
            del os.environ[var]


def rate_limit(calls_per_minute: int = 30):
    """AKShare API频率限制装饰器"""
    def decorator(func):
        last_called = [0.0]

        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            wait_time = 60.0 / calls_per_minute

            if elapsed < wait_time:
                sleep_time = wait_time - elapsed
                logger.info(f"Rate limiting: sleeping {sleep_time:.2f}s")
                time.sleep(sleep_time)

            last_called[0] = time.time()
            return func(*args, **kwargs)

        return wrapper
    return decorator


class EnhancedAKShareService:
    """增强的AKShare服务，集成完整日志记录"""

    def __init__(self):
        if not AKSHARE_AVAILABLE:
            logger.warning("AKShare not available - using mock data")
        else:
            # 清除代理设置
            clear_proxy_for_akshare()
            logger.info("AKShare service initialized with logging")

    @log_akshare_calls(akshare_logger)
    @rate_limit(calls_per_minute=30)
    def get_stock_list(self) -> List[Dict[str, Any]]:
        """
        获取股票列表
        返回格式: [{"code": "000001", "name": "平安银行", "market": "SZ"}, ...]
        """
        if not AKSHARE_AVAILABLE:
            return self._get_mock_stock_list()

        try:
            logger.info("Fetching stock list from AKShare")
            df = ak.stock_info_a_code_name()

            stocks = []
            for _, row in df.iterrows():
                # AKShare返回的数据格式处理
                code = str(row.get('code', '')).zfill(6)
                name = str(row.get('name', ''))

                # 判断市场
                if code.startswith(('60', '68', '90')):
                    market = 'SH'
                elif code.startswith(('00', '30')):
                    market = 'SZ'
                else:
                    market = 'OTHER'

                stocks.append({
                    "code": code,
                    "name": name,
                    "market": market
                })

            logger.info(f"Retrieved {len(stocks)} stocks from AKShare")
            return stocks

        except Exception as e:
            logger.error(f"AKShare stock list error: {e}")
            return self._get_mock_stock_list()

    @log_akshare_calls(akshare_logger)
    @rate_limit(calls_per_minute=30)
    def get_stock_info(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """获取股票基本信息"""
        if not AKSHARE_AVAILABLE:
            return self._get_mock_stock_info(stock_code)

        try:
            logger.info(f"Fetching stock info for {stock_code}")

            # 获取股票基本信息
            info_df = ak.stock_individual_info_em(symbol=stock_code)

            if info_df is not None and not info_df.empty:
                # 转换为字典格式
                info_dict = {}
                for _, row in info_df.iterrows():
                    item = row.get('item', '')
                    value = row.get('value', '')
                    info_dict[item] = value

                result = {
                    "code": stock_code,
                    "name": info_dict.get('股票简称', f'Stock{stock_code}'),
                    "market_cap": info_dict.get('总市值', 0),
                    "pe_ratio": info_dict.get('市盈率', 0),
                    "pb_ratio": info_dict.get('市净率', 0)
                }

                logger.info(f"Successfully retrieved info for {stock_code}: {result['name']}")
                return result

        except Exception as e:
            logger.error(f"AKShare stock info error for {stock_code}: {e}")
            return self._get_mock_stock_info(stock_code)

        return None

    @log_akshare_calls(akshare_logger)
    @rate_limit(calls_per_minute=30)
    def get_realtime_data(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """获取股票实时数据"""
        if not AKSHARE_AVAILABLE:
            return self._get_mock_realtime_data(stock_code)

        try:
            logger.info(f"Fetching realtime data for {stock_code}")

            # 获取实时数据
            realtime_df = ak.stock_zh_a_spot_em()

            if realtime_df is not None and not realtime_df.empty:
                # 查找指定股票
                stock_data = realtime_df[realtime_df['代码'] == stock_code]

                if not stock_data.empty:
                    row = stock_data.iloc[0]
                    result = {
                        "code": stock_code,
                        "current_price": float(row.get('最新价', 0)),
                        "change_amount": float(row.get('涨跌额', 0)),
                        "change_percent": float(row.get('涨跌幅', 0)),
                        "volume": int(row.get('成交量', 0)),
                        "turnover": float(row.get('成交额', 0)),
                        "high": float(row.get('最高', 0)),
                        "low": float(row.get('最低', 0)),
                        "open": float(row.get('今开', 0))
                    }

                    logger.info(f"Successfully retrieved realtime data for {stock_code}: {result['current_price']}")
                    return result

        except Exception as e:
            logger.error(f"AKShare realtime data error for {stock_code}: {e}")
            return self._get_mock_realtime_data(stock_code)

        return None

    @log_akshare_calls(akshare_logger)
    @rate_limit(calls_per_minute=30)
    def get_historical_data(self, stock_code: str, period: str = "daily", start_date: str = None, end_date: str = None) -> Optional[pd.DataFrame]:
        """获取历史K线数据"""
        if not AKSHARE_AVAILABLE:
            return self._get_mock_historical_data(stock_code)

        try:
            logger.info(f"Fetching historical data for {stock_code}, period: {period}")

            # 设置默认日期
            if not end_date:
                end_date = pd.Timestamp.now().strftime("%Y%m%d")
            if not start_date:
                start_date = (pd.Timestamp.now() - pd.Timedelta(days=30)).strftime("%Y%m%d")

            # 获取历史数据
            hist_df = ak.stock_zh_a_hist(
                symbol=stock_code,
                period=period,
                start_date=start_date,
                end_date=end_date,
                adjust=""
            )

            if hist_df is not None and not hist_df.empty:
                logger.info(f"Successfully retrieved {len(hist_df)} records for {stock_code}")
                return hist_df

        except Exception as e:
            logger.error(f"AKShare historical data error for {stock_code}: {e}")
            return self._get_mock_historical_data(stock_code)

        return None

    @log_akshare_calls(akshare_logger)
    @rate_limit(calls_per_minute=30)
    def get_financial_data(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """获取财务数据"""
        if not AKSHARE_AVAILABLE:
            return self._get_mock_financial_data(stock_code)

        try:
            logger.info(f"Fetching financial data for {stock_code}")

            # 获取财务数据
            financial_df = ak.stock_financial_em(symbol=stock_code)

            if financial_df is not None and not financial_df.empty:
                # 获取最新一期数据
                latest_row = financial_df.iloc[0]

                result = {
                    "code": stock_code,
                    "revenue": float(latest_row.get('营业收入', 0)),
                    "net_profit": float(latest_row.get('净利润', 0)),
                    "total_assets": float(latest_row.get('总资产', 0)),
                    "total_equity": float(latest_row.get('股东权益合计', 0)),
                    "report_date": str(latest_row.get('报告期', ''))
                }

                logger.info(f"Successfully retrieved financial data for {stock_code}: {result['revenue']}")
                return result

        except Exception as e:
            logger.error(f"AKShare financial data error for {stock_code}: {e}")
            return self._get_mock_financial_data(stock_code)

        return None

    @log_akshare_calls(akshare_logger)
    @rate_limit(calls_per_minute=30)
    def get_shareholders_data(self, stock_code: str) -> Optional[List[Dict[str, Any]]]:
        """获取股东数据"""
        if not AKSHARE_AVAILABLE:
            return self._get_mock_shareholders_data(stock_code)

        try:
            logger.info(f"Fetching shareholders data for {stock_code}")

            # 获取十大股东数据
            shareholders_df = ak.stock_zh_a_gdhs(symbol=stock_code)

            if shareholders_df is not None and not shareholders_df.empty:
                shareholders = []
                for _, row in shareholders_df.iterrows():
                    shareholders.append({
                        "shareholder_name": str(row.get('股东名称', '')),
                        "holding_ratio": float(row.get('持股比例', 0)),
                        "holding_count": int(row.get('持股数量', 0)),
                        "shareholder_type": str(row.get('股东性质', ''))
                    })

                logger.info(f"Successfully retrieved {len(shareholders)} shareholders for {stock_code}")
                return shareholders

        except Exception as e:
            logger.error(f"AKShare shareholders data error for {stock_code}: {e}")
            return self._get_mock_shareholders_data(stock_code)

        return None

    @log_akshare_calls(akshare_logger)
    @rate_limit(calls_per_minute=30)
    def get_longhubang_data(self, stock_code: str) -> Optional[List[Dict[str, Any]]]:
        """获取龙虎榜数据"""
        if not AKSHARE_AVAILABLE:
            return self._get_mock_longhubang_data(stock_code)

        try:
            logger.info(f"Fetching longhubang data for {stock_code}")

            # 获取龙虎榜数据
            longhubang_df = ak.stock_lhb_detail_em(symbol=stock_code)

            if longhubang_df is not None and not longhubang_df.empty:
                longhubang_records = []
                for _, row in longhubang_df.iterrows():
                    longhubang_records.append({
                        "trade_date": str(row.get('交易日期', '')),
                        "rank": int(row.get('序号', 0)),
                        "营业部": str(row.get('营业部名称', '')),
                        "buy_amount": float(row.get('买入金额', 0)),
                        "sell_amount": float(row.get('卖出金额', 0)),
                        "net_amount": float(row.get('净买额', 0))
                    })

                logger.info(f"Successfully retrieved {len(longhubang_records)} longhubang records for {stock_code}")
                return longhubang_records

        except Exception as e:
            logger.error(f"AKShare longhubang data error for {stock_code}: {e}")
            return self._get_mock_longhubang_data(stock_code)

        return None

    # Mock数据方法
    def _get_mock_stock_list(self) -> List[Dict[str, Any]]:
        """Mock股票列表"""
        return [
            {"code": "000001", "name": "平安银行", "market": "SZ"},
            {"code": "000002", "name": "万科A", "market": "SZ"},
            {"code": "600000", "name": "浦发银行", "market": "SH"},
        ]

    def _get_mock_stock_info(self, stock_code: str) -> Dict[str, Any]:
        """Mock股票信息"""
        return {
            "code": stock_code,
            "name": f"Mock股票{stock_code}",
            "market_cap": 100000000000,
            "pe_ratio": 15.5,
            "pb_ratio": 1.2
        }

    def _get_mock_realtime_data(self, stock_code: str) -> Dict[str, Any]:
        """Mock实时数据"""
        return {
            "code": stock_code,
            "current_price": 10.50,
            "change_amount": 0.15,
            "change_percent": 1.45,
            "volume": 1000000,
            "turnover": 10500000.0,
            "high": 10.80,
            "low": 10.20,
            "open": 10.35
        }

    def _get_mock_historical_data(self, stock_code: str) -> pd.DataFrame:
        """Mock历史数据"""
        import pandas as pd
        from datetime import datetime, timedelta

        dates = [(datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(10, 0, -1)]

        return pd.DataFrame({
            "日期": dates,
            "开盘": [10.0 + i * 0.1 for i in range(10)],
            "收盘": [10.1 + i * 0.1 for i in range(10)],
            "最高": [10.2 + i * 0.1 for i in range(10)],
            "最低": [9.9 + i * 0.1 for i in range(10)],
            "成交量": [1000000 + i * 100000 for i in range(10)]
        })

    def _get_mock_financial_data(self, stock_code: str) -> Dict[str, Any]:
        """Mock财务数据"""
        return {
            "code": stock_code,
            "revenue": 1000000000,
            "net_profit": 100000000,
            "total_assets": 5000000000,
            "total_equity": 2000000000,
            "report_date": "2025-09-30"
        }

    def _get_mock_shareholders_data(self, stock_code: str) -> List[Dict[str, Any]]:
        """Mock股东数据"""
        return [
            {
                "shareholder_name": "Mock机构投资者1",
                "holding_ratio": 10.5,
                "holding_count": 50000000,
                "shareholder_type": "机构"
            },
            {
                "shareholder_name": "Mock个人投资者1",
                "holding_ratio": 5.2,
                "holding_count": 25000000,
                "shareholder_type": "个人"
            }
        ]

    def _get_mock_longhubang_data(self, stock_code: str) -> List[Dict[str, Any]]:
        """Mock龙虎榜数据"""
        return [
            {
                "trade_date": "2025-09-22",
                "rank": 1,
                "营业部": "Mock证券营业部1",
                "buy_amount": 50000000,
                "sell_amount": 20000000,
                "net_amount": 30000000
            },
            {
                "trade_date": "2025-09-22",
                "rank": 2,
                "营业部": "Mock证券营业部2",
                "buy_amount": 30000000,
                "sell_amount": 45000000,
                "net_amount": -15000000
            }
        ]


# 创建全局实例
enhanced_akshare_service = EnhancedAKShareService()