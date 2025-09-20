#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据源验证器
验证指定股票代码在各个数据源的可用性
"""
import asyncio
import logging
import sys
import traceback
from datetime import datetime
import akshare as ak
import pandas as pd

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataSourceValidator:
    """数据源验证器"""

    def __init__(self):
        self.test_stocks = ["688660", "600629", "600619", "600549"]  # 包含成功的600549作为对比

    def validate_stock_basic_info(self, stock_code: str):
        """验证股票基本信息"""
        try:
            logger.info(f"验证 {stock_code} 基本信息...")

            # 使用stock_info接口
            stock_info = ak.stock_info_a_code_name(symbol=stock_code)
            if not stock_info.empty:
                logger.info(f"✅ {stock_code} 基本信息获取成功: {stock_info.iloc[0]['short_name']}")
                return True, stock_info.iloc[0]['short_name']
            else:
                logger.warning(f"❌ {stock_code} 基本信息为空")
                return False, "无数据"

        except Exception as e:
            logger.error(f"❌ {stock_code} 基本信息获取失败: {e}")
            return False, str(e)

    def validate_realtime_data(self, stock_code: str):
        """验证实时数据"""
        try:
            logger.info(f"验证 {stock_code} 实时数据...")

            # 尝试获取实时行情
            realtime_data = ak.stock_zh_a_spot_em()
            stock_data = realtime_data[realtime_data['代码'] == stock_code]

            if not stock_data.empty:
                logger.info(f"✅ {stock_code} 实时数据获取成功: {stock_data.iloc[0]['名称']}")
                return True, stock_data.iloc[0]['名称']
            else:
                logger.warning(f"❌ {stock_code} 在实时数据中未找到")
                return False, "未在实时数据中找到"

        except Exception as e:
            logger.error(f"❌ {stock_code} 实时数据获取失败: {e}")
            return False, str(e)

    def validate_kline_data(self, stock_code: str):
        """验证K线数据"""
        try:
            logger.info(f"验证 {stock_code} K线数据...")

            # 尝试获取日K线数据
            kline_data = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                           start_date="20240101", end_date="20241231")

            if not kline_data.empty:
                logger.info(f"✅ {stock_code} K线数据获取成功: {len(kline_data)} 条记录")
                return True, f"{len(kline_data)} 条记录"
            else:
                logger.warning(f"❌ {stock_code} K线数据为空")
                return False, "无K线数据"

        except Exception as e:
            logger.error(f"❌ {stock_code} K线数据获取失败: {e}")
            return False, str(e)

    def validate_financial_data(self, stock_code: str):
        """验证财务数据"""
        try:
            logger.info(f"验证 {stock_code} 财务数据...")

            # 尝试获取财务数据
            financial_data = ak.stock_financial_analysis_indicator(symbol=stock_code)

            if not financial_data.empty:
                logger.info(f"✅ {stock_code} 财务数据获取成功: {len(financial_data)} 条记录")
                return True, f"{len(financial_data)} 条记录"
            else:
                logger.warning(f"❌ {stock_code} 财务数据为空")
                return False, "无财务数据"

        except Exception as e:
            logger.error(f"❌ {stock_code} 财务数据获取失败: {e}")
            return False, str(e)

    def validate_announcement_data(self, stock_code: str):
        """验证公告数据"""
        try:
            logger.info(f"验证 {stock_code} 公告数据...")

            # 尝试获取公告数据
            announcement_data = ak.stock_notice_report(symbol=stock_code)

            if not announcement_data.empty:
                logger.info(f"✅ {stock_code} 公告数据获取成功: {len(announcement_data)} 条记录")
                return True, f"{len(announcement_data)} 条记录"
            else:
                logger.warning(f"❌ {stock_code} 公告数据为空")
                return False, "无公告数据"

        except Exception as e:
            logger.error(f"❌ {stock_code} 公告数据获取失败: {e}")
            return False, str(e)

    def validate_longhubang_data(self, stock_code: str):
        """验证龙虎榜数据"""
        try:
            logger.info(f"验证 {stock_code} 龙虎榜数据...")

            # 尝试获取龙虎榜数据
            lhb_data = ak.stock_lhb_detail_em(symbol=stock_code,
                                             start_date="20240101",
                                             end_date="20241231")

            if not lhb_data.empty:
                logger.info(f"✅ {stock_code} 龙虎榜数据获取成功: {len(lhb_data)} 条记录")
                return True, f"{len(lhb_data)} 条记录"
            else:
                logger.warning(f"❌ {stock_code} 龙虎榜数据为空")
                return False, "无龙虎榜数据"

        except Exception as e:
            logger.error(f"❌ {stock_code} 龙虎榜数据获取失败: {e}")
            return False, str(e)

    def validate_shareholder_data(self, stock_code: str):
        """验证股东数据"""
        try:
            logger.info(f"验证 {stock_code} 股东数据...")

            # 尝试获取股东数据
            shareholder_data = ak.stock_zh_a_gdhs_detail_em(symbol=stock_code)

            if not shareholder_data.empty:
                logger.info(f"✅ {stock_code} 股东数据获取成功: {len(shareholder_data)} 条记录")
                return True, f"{len(shareholder_data)} 条记录"
            else:
                logger.warning(f"❌ {stock_code} 股东数据为空")
                return False, "无股东数据"

        except Exception as e:
            logger.error(f"❌ {stock_code} 股东数据获取失败: {e}")
            return False, str(e)

    def comprehensive_validation(self):
        """综合验证所有股票的所有数据类型"""
        results = {}

        for stock_code in self.test_stocks:
            logger.info(f"\n{'='*60}")
            logger.info(f"🔍 开始验证股票: {stock_code}")
            logger.info(f"{'='*60}")

            stock_results = {
                "basic_info": self.validate_stock_basic_info(stock_code),
                "realtime": self.validate_realtime_data(stock_code),
                "kline": self.validate_kline_data(stock_code),
                "financial": self.validate_financial_data(stock_code),
                "announcement": self.validate_announcement_data(stock_code),
                "longhubang": self.validate_longhubang_data(stock_code),
                "shareholder": self.validate_shareholder_data(stock_code)
            }

            results[stock_code] = stock_results

            # 统计成功率
            success_count = sum(1 for result in stock_results.values() if result[0])
            total_count = len(stock_results)
            success_rate = (success_count / total_count) * 100

            logger.info(f"\n📊 {stock_code} 数据可用性总结:")
            logger.info(f"   成功: {success_count}/{total_count} ({success_rate:.1f}%)")

            for data_type, (success, message) in stock_results.items():
                status = "✅" if success else "❌"
                logger.info(f"   {status} {data_type}: {message}")

        return results

    def generate_report(self, results):
        """生成验证报告"""
        logger.info(f"\n{'='*80}")
        logger.info(f"📋 数据源验证总报告")
        logger.info(f"{'='*80}")

        # 按数据类型统计
        data_types = ["basic_info", "realtime", "kline", "financial", "announcement", "longhubang", "shareholder"]

        logger.info(f"\n📊 按数据类型统计:")
        for data_type in data_types:
            success_stocks = [stock for stock, stock_results in results.items()
                            if stock_results[data_type][0]]
            total_stocks = len(results)
            success_rate = (len(success_stocks) / total_stocks) * 100

            logger.info(f"   {data_type}: {len(success_stocks)}/{total_stocks} ({success_rate:.1f}%)")
            if success_stocks:
                logger.info(f"      成功股票: {', '.join(success_stocks)}")

        # 按股票统计
        logger.info(f"\n📊 按股票统计:")
        for stock_code, stock_results in results.items():
            success_count = sum(1 for result in stock_results.values() if result[0])
            total_count = len(stock_results)
            success_rate = (success_count / total_count) * 100

            status = "✅" if success_rate > 50 else "⚠️" if success_rate > 0 else "❌"
            logger.info(f"   {status} {stock_code}: {success_count}/{total_count} ({success_rate:.1f}%)")

        # 问题分析
        logger.info(f"\n🔍 问题分析:")
        problem_stocks = []
        for stock_code, stock_results in results.items():
            success_count = sum(1 for result in stock_results.values() if result[0])
            if success_count == 0:
                problem_stocks.append(stock_code)

        if problem_stocks:
            logger.info(f"   完全无数据的股票: {', '.join(problem_stocks)}")
            logger.info(f"   可能原因:")
            logger.info(f"   1. 股票代码不存在或已退市")
            logger.info(f"   2. 新上市股票，历史数据不完整")
            logger.info(f"   3. 数据源暂时不支持")
            logger.info(f"   4. 网络或API限制")
        else:
            logger.info(f"   所有股票都有部分数据可用")

        return results

def main():
    """主函数"""
    logger.info("🚀 启动数据源验证器")

    validator = DataSourceValidator()

    try:
        # 执行综合验证
        results = validator.comprehensive_validation()

        # 生成报告
        validator.generate_report(results)

        logger.info(f"\n✅ 数据源验证完成")

    except Exception as e:
        logger.error(f"❌ 验证过程发生错误: {e}")
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()