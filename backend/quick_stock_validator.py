#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
快速股票验证器
快速检查股票代码的可用性
"""
import logging
import akshare as ak
import sys

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def quick_validate_stock(stock_code: str):
    """快速验证单个股票"""
    logger.info(f"🔍 验证股票: {stock_code}")

    results = {}

    # 1. 验证基本信息
    try:
        # 修正API调用
        stock_info = ak.stock_info_a_code_name()
        stock_data = stock_info[stock_info['code'] == stock_code]
        if not stock_data.empty:
            results['basic_info'] = f"✅ {stock_data.iloc[0]['name']}"
        else:
            results['basic_info'] = "❌ 代码未找到"
    except Exception as e:
        results['basic_info'] = f"❌ API错误: {str(e)[:50]}"

    # 2. 验证K线数据 (最简单的验证)
    try:
        kline_data = ak.stock_zh_a_hist(symbol=stock_code, period="daily",
                                       start_date="20240901", end_date="20240930")
        if not kline_data.empty:
            results['kline'] = f"✅ {len(kline_data)} 条K线记录"
        else:
            results['kline'] = "❌ 无K线数据"
    except Exception as e:
        results['kline'] = f"❌ K线获取失败: {str(e)[:50]}"

    # 3. 验证财务数据
    try:
        financial_data = ak.stock_financial_analysis_indicator(symbol=stock_code)
        if not financial_data.empty:
            results['financial'] = f"✅ {len(financial_data)} 条财务记录"
        else:
            results['financial'] = "❌ 无财务数据"
    except Exception as e:
        results['financial'] = f"❌ 财务获取失败: {str(e)[:50]}"

    return results

def main():
    test_stocks = ["688660", "600629", "600619", "600549"]  # 包含成功的600549对比

    all_results = {}

    for stock_code in test_stocks:
        try:
            results = quick_validate_stock(stock_code)
            all_results[stock_code] = results

            logger.info(f"📊 {stock_code} 结果:")
            for data_type, result in results.items():
                logger.info(f"   {data_type}: {result}")
            logger.info("")

        except Exception as e:
            logger.error(f"❌ {stock_code} 验证失败: {e}")
            all_results[stock_code] = {"error": str(e)}

    # 总结
    logger.info("📋 验证总结:")
    for stock_code, results in all_results.items():
        if 'error' in results:
            logger.info(f"   {stock_code}: ❌ 验证错误")
        else:
            success_count = sum(1 for result in results.values() if result.startswith('✅'))
            total_count = len(results)
            logger.info(f"   {stock_code}: {success_count}/{total_count} 成功")

if __name__ == "__main__":
    main()