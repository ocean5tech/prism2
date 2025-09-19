#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
增强版Dashboard API - 严格遵循三层架构
Redis → PostgreSQL → AKShare
"""
import logging
import time
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis
import psycopg2
from psycopg2.extras import RealDictCursor
import akshare as ak
import pandas as pd
import os

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 数据模型
class DashboardRequest(BaseModel):
    stock_code: str
    data_types: List[str]
    kline_period: str = "daily"
    kline_days: int = 60
    news_days: int = 7

class DashboardResponse(BaseModel):
    success: bool
    stock_code: str
    timestamp: datetime
    data_sources: Dict[str, List[str]]
    cache_info: Dict[str, str]
    data: Dict[str, Any]

# 三层架构数据服务
class ThreeTierDataService:
    def __init__(self):
        # Redis连接 (第一层缓存)
        self.redis_client = redis.Redis(
            host='localhost',
            port=6379,
            db=0,
            decode_responses=True
        )

        # PostgreSQL连接 (第二层存储)
        self.pg_config = {
            'host': 'localhost',
            'port': 5432,
            'database': 'prism2',
            'user': 'prism2',
            'password': 'prism2_secure_password'
        }

        # 数据缓存TTL配置
        self.cache_ttl = {
            'realtime': 30,          # 实时数据30秒
            'kline': 300,            # K线数据5分钟
            'basic_info': 3600,      # 基本信息1小时
            'news': 600,             # 新闻10分钟
            'financial': 21600,      # 财务数据6小时
            'announcements': 1800,   # 公告30分钟
            'shareholders': 86400,   # 股东信息24小时
            'longhubang': 3600,      # 龙虎榜1小时
            'technical': 300         # 技术指标5分钟
        }

    def clear_proxy(self):
        """清除代理设置"""
        proxy_vars = ['http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY']
        original_proxy = {}
        for var in proxy_vars:
            original_proxy[var] = os.environ.get(var)
            if var in os.environ:
                del os.environ[var]
        return original_proxy

    def restore_proxy(self, original_proxy):
        """恢复代理设置"""
        for var, value in original_proxy.items():
            if value is not None:
                os.environ[var] = value

    def get_cache_key(self, data_type: str, stock_code: str, **kwargs) -> str:
        """生成缓存键"""
        key_parts = [data_type, stock_code]
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")
        return ":".join(key_parts)

    def get_from_redis(self, cache_key: str) -> Optional[Dict]:
        """第一层：从Redis获取数据"""
        try:
            cached_data = self.redis_client.get(cache_key)
            if cached_data:
                logger.info(f"✅ Redis缓存命中: {cache_key}")
                return json.loads(cached_data)
            else:
                logger.info(f"❌ Redis缓存未命中: {cache_key}")
                return None
        except Exception as e:
            logger.error(f"Redis查询错误: {e}")
            return None

    def get_from_postgresql(self, data_type: str, stock_code: str, **kwargs) -> Optional[Dict]:
        """第二层：从PostgreSQL获取数据"""
        try:
            conn = psycopg2.connect(**self.pg_config)
            cursor = conn.cursor(cursor_factory=RealDictCursor)

            # 根据数据类型查询不同表
            if data_type == "basic_info":
                cursor.execute(
                    "SELECT * FROM stock_basic_info WHERE stock_code = %s",
                    (stock_code,)
                )
            elif data_type == "kline":
                days = kwargs.get('days', 60)
                cursor.execute(
                    """SELECT * FROM stock_kline_daily
                       WHERE stock_code = %s
                       ORDER BY trade_date DESC
                       LIMIT %s""",
                    (stock_code, days)
                )
            elif data_type == "news":
                days = kwargs.get('days', 7)
                since_date = datetime.now() - timedelta(days=days)
                cursor.execute(
                    """SELECT * FROM stock_news
                       WHERE stock_code = %s AND publish_time >= %s
                       ORDER BY publish_time DESC""",
                    (stock_code, since_date)
                )
            elif data_type == "financial":
                cursor.execute(
                    "SELECT * FROM stock_financial WHERE stock_code = %s",
                    (stock_code,)
                )
            elif data_type == "announcements":
                cursor.execute(
                    "SELECT * FROM stock_announcements WHERE stock_code = %s",
                    (stock_code,)
                )
            elif data_type == "shareholders":
                cursor.execute(
                    "SELECT * FROM stock_shareholders WHERE stock_code = %s",
                    (stock_code,)
                )
            elif data_type == "longhubang":
                cursor.execute(
                    "SELECT * FROM stock_longhubang WHERE stock_code = %s",
                    (stock_code,)
                )

            result = cursor.fetchall()
            cursor.close()
            conn.close()

            if result:
                logger.info(f"✅ PostgreSQL数据命中: {data_type} for {stock_code}")
                return {"data": [dict(row) for row in result], "source": "postgresql"}
            else:
                logger.info(f"❌ PostgreSQL数据未命中: {data_type} for {stock_code}")
                return None

        except Exception as e:
            logger.error(f"PostgreSQL查询错误: {e}")
            return None

    def get_from_akshare(self, data_type: str, stock_code: str, **kwargs) -> Optional[Dict]:
        """第三层：从AKShare获取数据"""
        try:
            original_proxy = self.clear_proxy()

            try:
                if data_type == "realtime":
                    # 获取实时数据
                    end_date = datetime.now().strftime("%Y%m%d")
                    start_date = (datetime.now() - timedelta(days=5)).strftime("%Y%m%d")

                    hist_data = ak.stock_zh_a_hist(
                        symbol=stock_code,
                        period="daily",
                        start_date=start_date,
                        end_date=end_date,
                        adjust=""
                    )

                    if not hist_data.empty:
                        latest_row = hist_data.iloc[-1]
                        current_price = float(latest_row.get('收盘', 0))
                        change_percent = float(latest_row.get('涨跌幅', 0))

                        data = {
                            "current_price": current_price,
                            "change_percent": change_percent,
                            "volume": int(latest_row.get('成交量', 0)),
                            "turnover": float(latest_row.get('成交额', 0)),
                            "timestamp": datetime.now().isoformat()
                        }
                        logger.info(f"✅ AKShare获取实时数据: {stock_code}")
                        return {"data": data, "source": "akshare"}

                elif data_type == "kline":
                    # 获取K线数据
                    days = kwargs.get('days', 60)
                    end_date = datetime.now().strftime("%Y%m%d")
                    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y%m%d")

                    kline_data = ak.stock_zh_a_hist(
                        symbol=stock_code,
                        period="daily",
                        start_date=start_date,
                        end_date=end_date,
                        adjust=""
                    )

                    if not kline_data.empty:
                        kline_list = []
                        for _, row in kline_data.iterrows():
                            kline_list.append({
                                "date": row['日期'],
                                "open": float(row['开盘']),
                                "high": float(row['最高']),
                                "low": float(row['最低']),
                                "close": float(row['收盘']),
                                "volume": int(row['成交量']),
                                "turnover": float(row['成交额'])
                            })

                        data = {
                            "period": "daily",
                            "days": len(kline_list),
                            "data": kline_list
                        }
                        logger.info(f"✅ AKShare获取K线数据: {stock_code}, {len(kline_list)}天")
                        return {"data": data, "source": "akshare"}

                elif data_type == "news":
                    # 获取新闻数据
                    news_data = ak.stock_news_em(symbol=stock_code)

                    if not news_data.empty:
                        news_list = []
                        days = kwargs.get('days', 7)
                        cutoff_date = datetime.now() - timedelta(days=days)

                        for _, row in news_data.head(20).iterrows():  # 取前20条新闻
                            publish_time_str = str(row.get('发布时间', ''))
                            try:
                                publish_time = datetime.strptime(publish_time_str, "%Y-%m-%d %H:%M:%S")
                                if publish_time >= cutoff_date:
                                    news_list.append({
                                        "title": str(row.get('新闻标题', '')),
                                        "publish_time": publish_time.isoformat(),
                                        "source": "东方财富",
                                        "url": str(row.get('新闻链接', ''))
                                    })
                            except:
                                continue

                        data = {
                            "count": len(news_list),
                            "days": days,
                            "data": news_list
                        }
                        logger.info(f"✅ AKShare获取新闻数据: {stock_code}, {len(news_list)}条")
                        return {"data": data, "source": "akshare"}

                elif data_type == "financial":
                    # 获取财务数据 - 使用ocean5tech项目验证的接口
                    try:
                        # 使用 stock_financial_abstract 获取财务摘要数据
                        financial_df = ak.stock_financial_abstract(symbol=stock_code)

                        if financial_df is not None and not financial_df.empty:
                            # 清理NaN值
                            financial_df_clean = financial_df.fillna('')

                            # 获取最近8个季度的数据列
                            date_columns = [col for col in financial_df_clean.columns if col not in ['选项', '指标']]
                            recent_columns = ['选项', '指标'] + date_columns[:8]  # 最近8个季度

                            # 筛选常用指标和最近数据
                            recent_data = financial_df_clean[recent_columns]

                            # 转换为易于使用的格式
                            financial_summary = {}
                            for _, row in recent_data.iterrows():
                                indicator = row['指标']
                                # 获取最新的非空值
                                latest_value = None
                                for col in date_columns[:8]:
                                    if col in row and row[col] != '' and str(row[col]) != 'nan':
                                        latest_value = row[col]
                                        break

                                if latest_value is not None:
                                    financial_summary[indicator] = latest_value

                            financial_data = {
                                "summary": financial_summary,
                                "detailed_data": recent_data.to_dict('records'),
                                "periods": date_columns[:8],
                                "total_indicators": len(financial_df_clean),
                                "updated_at": datetime.now().isoformat()
                            }

                            logger.info(f"✅ AKShare获取财务数据: {stock_code}, {len(financial_summary)}个指标")
                            return {"data": financial_data, "source": "akshare"}
                        else:
                            logger.warning(f"财务数据为空: {stock_code}")
                            return None

                    except Exception as e:
                        logger.error(f"获取财务数据失败: {e}")
                        return None

                elif data_type == "announcements":
                    # 获取公告信息 - 使用新闻接口作为替代方案
                    try:
                        # 使用news接口获取相关资讯作为公告替代
                        news_data = ak.stock_news_em(symbol=stock_code)

                        announcements_list = []
                        if news_data is not None and not news_data.empty:
                            # 过滤最近30天的新闻
                            cutoff_date = datetime.now() - timedelta(days=30)

                            for _, row in news_data.head(20).iterrows():
                                publish_time_str = str(row.get('发布时间', ''))
                                try:
                                    # 尝试解析发布时间
                                    publish_time = datetime.strptime(publish_time_str, "%Y-%m-%d %H:%M:%S")
                                    if publish_time >= cutoff_date:
                                        announcements_list.append({
                                            "title": str(row.get('新闻标题', '')),
                                            "publish_date": publish_time_str,
                                            "type": "新闻资讯",
                                            "url": str(row.get('新闻链接', '')),
                                            "source": str(row.get('文章来源', '东方财富'))
                                        })
                                except:
                                    # 如果时间解析失败，仍然添加但不过滤
                                    announcements_list.append({
                                        "title": str(row.get('新闻标题', '')),
                                        "publish_date": publish_time_str,
                                        "type": "新闻资讯",
                                        "url": str(row.get('新闻链接', '')),
                                        "source": str(row.get('文章来源', '东方财富'))
                                    })

                        data = {
                            "count": len(announcements_list),
                            "days": 30,
                            "data": announcements_list,
                            "data_source": "stock_news_em",
                            "updated_at": datetime.now().isoformat()
                        }

                        logger.info(f"✅ AKShare获取公告数据(新闻): {stock_code}, {len(announcements_list)}条")
                        return {"data": data, "source": "akshare"}
                    except Exception as e:
                        logger.error(f"获取公告数据失败: {e}")
                        return None

                elif data_type == "shareholders":
                    # 获取股东信息
                    try:
                        shareholder_data = ak.stock_zh_a_gdhs_detail_em(symbol=stock_code)

                        shareholders_list = []
                        if not shareholder_data.empty:
                            for _, row in shareholder_data.head(10).iterrows():
                                shareholders_list.append({
                                    "rank": int(row.get('序号', 0)),
                                    "shareholder_name": str(row.get('股东名称', '')),
                                    "shareholding_num": str(row.get('持股数量', '')),
                                    "shareholding_ratio": str(row.get('持股比例', '')),
                                    "change": str(row.get('较上期变化', ''))
                                })

                        data = {
                            "top_10": shareholders_list,
                            "updated_at": datetime.now().isoformat()
                        }

                        logger.info(f"✅ AKShare获取股东数据: {stock_code}, {len(shareholders_list)}个股东")
                        return {"data": data, "source": "akshare"}
                    except Exception as e:
                        logger.error(f"获取股东数据失败: {e}")
                        return None

                elif data_type == "longhubang":
                    # 获取龙虎榜数据
                    try:
                        end_date = datetime.now().strftime("%Y%m%d")
                        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y%m%d")

                        # 获取整体龙虎榜数据，然后筛选当前股票
                        longhubang_data = ak.stock_lhb_detail_em(start_date=start_date, end_date=end_date)

                        longhubang_list = []
                        if not longhubang_data.empty:
                            # 筛选当前股票的龙虎榜记录
                            stock_lhb = longhubang_data[longhubang_data['代码'] == stock_code]
                            for _, row in stock_lhb.iterrows():
                                longhubang_list.append({
                                    "date": str(row.get('上榜日', '')),
                                    "reason": str(row.get('上榜原因', '')),
                                    "close_price": str(row.get('收盘价', '')),
                                    "change_percent": str(row.get('涨跌幅', '')),
                                    "turnover": str(row.get('龙虎榜成交额', ''))
                                })

                        data = {
                            "records": longhubang_list,
                            "days": 30,
                            "updated_at": datetime.now().isoformat()
                        }

                        logger.info(f"✅ AKShare获取龙虎榜数据: {stock_code}, {len(longhubang_list)}条记录")
                        return {"data": data, "source": "akshare"}
                    except Exception as e:
                        logger.error(f"获取龙虎榜数据失败: {e}")
                        return None

                elif data_type == "basic_info":
                    # 获取基本信息
                    try:
                        info_data = ak.stock_individual_info_em(symbol=stock_code)
                        if isinstance(info_data, pd.DataFrame) and not info_data.empty:
                            stock_name_row = info_data[info_data['item'] == '股票简称']
                            stock_name = stock_name_row['value'].iloc[0] if not stock_name_row.empty else f'Stock{stock_code}'

                            # 确定市场和行业
                            market = "SZ" if stock_code.startswith("00") or stock_code.startswith("30") else "SH"
                            industry_map = {"002222": "电子", "601169": "银行", "601838": "银行"}
                            industry = industry_map.get(stock_code, "其他")

                            data = {
                                "code": stock_code,
                                "name": stock_name,
                                "market": market,
                                "industry": industry,
                                "updated_at": datetime.now().isoformat()
                            }
                            logger.info(f"✅ AKShare获取基本信息: {stock_code}")
                            return {"data": data, "source": "akshare"}
                    except:
                        pass

                    # 如果基本信息接口失败，使用备用方案
                    market = "SZ" if stock_code.startswith("00") or stock_code.startswith("30") else "SH"
                    industry_map = {"002222": "电子", "601169": "银行", "601838": "银行"}

                    data = {
                        "code": stock_code,
                        "name": f"Stock{stock_code}",
                        "market": market,
                        "industry": industry_map.get(stock_code, "其他"),
                        "updated_at": datetime.now().isoformat()
                    }
                    return {"data": data, "source": "akshare"}

            finally:
                self.restore_proxy(original_proxy)

        except Exception as e:
            logger.error(f"AKShare获取数据失败: {data_type}, {stock_code}, {e}")
            return None

    def save_to_postgresql(self, data_type: str, stock_code: str, data: Dict):
        """保存数据到PostgreSQL"""
        try:
            conn = psycopg2.connect(**self.pg_config)
            cursor = conn.cursor()

            if data_type == "kline" and "data" in data:
                # 保存K线数据（简化版）
                for kline in data["data"]:
                    cursor.execute(
                        """INSERT INTO stock_kline_daily (stock_code, trade_date, open_price, high_price, low_price, close_price, volume, turnover)
                           VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                           ON CONFLICT (stock_code, trade_date) DO UPDATE SET
                           open_price = EXCLUDED.open_price,
                           high_price = EXCLUDED.high_price,
                           low_price = EXCLUDED.low_price,
                           close_price = EXCLUDED.close_price,
                           volume = EXCLUDED.volume,
                           turnover = EXCLUDED.turnover""",
                        (stock_code, kline["date"], kline["open"], kline["high"],
                         kline["low"], kline["close"], kline["volume"], kline["turnover"])
                    )

            elif data_type == "basic_info":
                # 保存基本信息
                cursor.execute(
                    """INSERT INTO stock_basic_info (stock_code, stock_name, market, industry, updated_at)
                       VALUES (%s, %s, %s, %s, %s)
                       ON CONFLICT (stock_code) DO UPDATE SET
                       stock_name = EXCLUDED.stock_name,
                       market = EXCLUDED.market,
                       industry = EXCLUDED.industry,
                       updated_at = EXCLUDED.updated_at""",
                    (data["code"], data["name"], data["market"], data["industry"], datetime.now())
                )

            elif data_type == "financial":
                # 保存财务数据到新的表结构
                cursor.execute(
                    """INSERT INTO stock_financial (stock_code, summary_data, detailed_data, periods)
                       VALUES (%s, %s, %s, %s)
                       ON CONFLICT (stock_code) DO UPDATE SET
                       summary_data = EXCLUDED.summary_data,
                       detailed_data = EXCLUDED.detailed_data,
                       periods = EXCLUDED.periods,
                       updated_at = CURRENT_TIMESTAMP""",
                    (stock_code,
                     json.dumps(data.get("summary", {}), ensure_ascii=False),
                     json.dumps(data.get("detailed_data", []), ensure_ascii=False),
                     json.dumps(data.get("periods", []), ensure_ascii=False))
                )

            elif data_type == "announcements":
                # 保存公告数据到新的表结构
                cursor.execute(
                    """INSERT INTO stock_announcements (stock_code, announcement_data, count)
                       VALUES (%s, %s, %s)
                       ON CONFLICT (stock_code) DO UPDATE SET
                       announcement_data = EXCLUDED.announcement_data,
                       count = EXCLUDED.count,
                       updated_at = CURRENT_TIMESTAMP""",
                    (stock_code,
                     json.dumps(data, ensure_ascii=False),
                     data.get("count", 0))
                )

            elif data_type == "shareholders":
                # 保存股东数据到新的表结构
                cursor.execute(
                    """INSERT INTO stock_shareholders (stock_code, shareholders_data, top_10_count)
                       VALUES (%s, %s, %s)
                       ON CONFLICT (stock_code) DO UPDATE SET
                       shareholders_data = EXCLUDED.shareholders_data,
                       top_10_count = EXCLUDED.top_10_count,
                       updated_at = CURRENT_TIMESTAMP""",
                    (stock_code,
                     json.dumps(data, ensure_ascii=False),
                     len(data.get("top_10", [])))
                )

            elif data_type == "longhubang":
                # 保存龙虎榜数据到新的表结构
                cursor.execute(
                    """INSERT INTO stock_longhubang (stock_code, longhubang_data, records_count, query_days)
                       VALUES (%s, %s, %s, %s)
                       ON CONFLICT (stock_code) DO UPDATE SET
                       longhubang_data = EXCLUDED.longhubang_data,
                       records_count = EXCLUDED.records_count,
                       query_days = EXCLUDED.query_days,
                       updated_at = CURRENT_TIMESTAMP""",
                    (stock_code,
                     json.dumps(data, ensure_ascii=False),
                     len(data.get("records", [])),
                     data.get("days", 30))
                )

            conn.commit()
            cursor.close()
            conn.close()
            logger.info(f"✅ 数据已保存到PostgreSQL: {data_type}, {stock_code}")

        except Exception as e:
            logger.error(f"保存到PostgreSQL失败: {data_type}, {stock_code}, {e}")

    def save_to_redis(self, cache_key: str, data: Dict, ttl: int):
        """保存数据到Redis缓存"""
        try:
            self.redis_client.setex(cache_key, ttl, json.dumps(data, default=str))
            logger.info(f"✅ 数据已缓存到Redis: {cache_key}, TTL: {ttl}s")
        except Exception as e:
            logger.error(f"保存到Redis失败: {cache_key}, {e}")

    def get_data(self, data_type: str, stock_code: str, **kwargs) -> Dict:
        """三层架构数据获取主函数"""
        cache_key = self.get_cache_key(data_type, stock_code, **kwargs)

        # 1. 首先从Redis获取
        redis_result = self.get_from_redis(cache_key)
        if redis_result:
            return {
                "data": redis_result,
                "source": "redis",
                "cache_info": "hit"
            }

        # 2. 从PostgreSQL获取
        pg_result = self.get_from_postgresql(data_type, stock_code, **kwargs)
        if pg_result:
            # 缓存到Redis
            ttl = self.cache_ttl.get(data_type, 300)
            self.save_to_redis(cache_key, pg_result["data"], ttl)

            return {
                "data": pg_result["data"],
                "source": "postgresql",
                "cache_info": "miss_cached"
            }

        # 3. 从AKShare获取
        akshare_result = self.get_from_akshare(data_type, stock_code, **kwargs)
        if akshare_result:
            # 保存到PostgreSQL
            self.save_to_postgresql(data_type, stock_code, akshare_result["data"])

            # 缓存到Redis
            ttl = self.cache_ttl.get(data_type, 300)
            self.save_to_redis(cache_key, akshare_result["data"], ttl)

            return {
                "data": akshare_result["data"],
                "source": "akshare",
                "cache_info": "fetched_cached"
            }

        # 4. 所有数据源都失败
        return {
            "data": None,
            "source": "none",
            "cache_info": "failed"
        }

# FastAPI应用
app = FastAPI(
    title="增强版Dashboard API - 三层架构",
    version="2.0.0",
    description="Redis → PostgreSQL → AKShare 三层查询架构"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 初始化数据服务
data_service = ThreeTierDataService()

@app.post("/api/v1/stocks/dashboard", response_model=DashboardResponse)
async def get_enhanced_dashboard_data(request: DashboardRequest):
    """增强版Dashboard API - 严格遵循三层架构"""
    logger.info(f"增强Dashboard请求: {request.stock_code}, 数据类型: {request.data_types}")

    start_time = time.time()
    results = {}
    data_sources = {
        "redis": [],
        "postgresql": [],
        "akshare": []
    }
    cache_info = {}

    # 并行获取不同类型数据
    for data_type in request.data_types:
        kwargs = {}
        if data_type == "kline":
            kwargs["days"] = request.kline_days
        elif data_type == "news":
            kwargs["days"] = request.news_days

        result = data_service.get_data(data_type, request.stock_code, **kwargs)

        if result["data"]:
            results[data_type] = result["data"]
            data_sources[result["source"]].append(data_type)
            cache_info[data_type] = result["cache_info"]
        else:
            results[data_type] = None
            cache_info[data_type] = "failed"

    end_time = time.time()
    response_time = end_time - start_time

    logger.info(f"Dashboard响应完成: {request.stock_code}, 耗时: {response_time:.2f}s")

    return DashboardResponse(
        success=True,
        stock_code=request.stock_code,
        timestamp=datetime.now(),
        data_sources=data_sources,
        cache_info=cache_info,
        data=results
    )

@app.get("/")
async def root():
    return {
        "message": "增强版Dashboard API - 三层架构",
        "version": "2.0.0",
        "architecture": "Redis → PostgreSQL → AKShare",
        "docs": "/docs"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)