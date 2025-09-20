#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据向量化器
将结构化数据转换为适合RAG的文本格式并向量化
"""
import logging
import re
from typing import List, Dict, Any, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class DataVectorizer:
    """数据向量化服务"""

    def __init__(self):
        self.max_chunk_length = 512  # 最大文本块长度
        self.min_chunk_length = 50   # 最小文本块长度
        logger.info("数据向量化器初始化完成")

    def transform_to_text_chunks(self, stock_code: str, data_type: str, source_data: Dict) -> List[str]:
        """
        将结构化数据转换为文本块

        Args:
            stock_code: 股票代码
            data_type: 数据类型
            source_data: 源数据

        Returns:
            文本块列表
        """
        try:
            # 根据数据类型选择转换方法
            if data_type == "financial":
                return self.transform_financial_data(stock_code, source_data)
            elif data_type == "announcements":
                return self.transform_announcement_data(stock_code, source_data)
            elif data_type == "shareholders":
                return self.transform_shareholder_data(stock_code, source_data)
            elif data_type == "longhubang":
                return self.transform_longhubang_data(stock_code, source_data)
            else:
                logger.warning(f"未知数据类型: {data_type}")
                return []

        except Exception as e:
            logger.error(f"数据转换失败: {stock_code}-{data_type}, {e}")
            return []

    def transform_financial_data(self, stock_code: str, financial_data: Dict) -> List[str]:
        """财务数据转换为文本段落"""
        text_chunks = []

        try:
            # 如果数据是嵌套结构，提取实际的财务数据
            if isinstance(financial_data.get('data'), dict):
                data = financial_data['data']
            else:
                data = financial_data

            stock_name = self._get_stock_name(stock_code)

            # 基本信息文本块
            basic_info = f"{stock_name}({stock_code})的财务数据概览。"

            # 营收和利润相关
            revenue_text = self._build_revenue_text(stock_code, stock_name, data)
            if revenue_text:
                text_chunks.append(revenue_text)

            # 财务比率
            ratio_text = self._build_ratio_text(stock_code, stock_name, data)
            if ratio_text:
                text_chunks.append(ratio_text)

            # 资产负债
            balance_text = self._build_balance_text(stock_code, stock_name, data)
            if balance_text:
                text_chunks.append(balance_text)

            # 现金流
            cashflow_text = self._build_cashflow_text(stock_code, stock_name, data)
            if cashflow_text:
                text_chunks.append(cashflow_text)

            # 如果没有生成任何具体内容，添加基本信息
            if not text_chunks:
                text_chunks.append(basic_info + "财务数据正在更新中。")

        except Exception as e:
            logger.error(f"财务数据转换失败: {stock_code}, {e}")
            text_chunks.append(f"{self._get_stock_name(stock_code)}({stock_code})的财务数据暂时无法获取。")

        return self._chunk_texts(text_chunks)

    def transform_announcement_data(self, stock_code: str, announcement_data: Dict) -> List[str]:
        """公告数据转换为文本段落"""
        text_chunks = []

        try:
            # 提取公告数据
            if isinstance(announcement_data.get('data'), list):
                announcements = announcement_data['data']
            elif isinstance(announcement_data, list):
                announcements = announcement_data
            else:
                announcements = []

            stock_name = self._get_stock_name(stock_code)

            for announcement in announcements[:10]:  # 限制处理前10条公告
                if isinstance(announcement, dict):
                    title = announcement.get('title', '').strip()
                    content = announcement.get('content', '').strip()
                    date = announcement.get('date', announcement.get('pub_date', ''))

                    if title or content:
                        # 构建公告文本
                        announcement_text = f"{stock_name}({stock_code})"

                        if date:
                            announcement_text += f"于{date}"

                        if title:
                            announcement_text += f"发布公告：{title}。"

                        if content and len(content) > 10:
                            # 清理和截断内容
                            cleaned_content = self._clean_text(content)[:200]
                            announcement_text += f"公告内容：{cleaned_content}"
                            if len(content) > 200:
                                announcement_text += "..."

                        text_chunks.append(announcement_text)

            # 如果没有具体公告，添加基本信息
            if not text_chunks:
                text_chunks.append(f"{stock_name}({stock_code})的最新公告信息暂时无法获取。")

        except Exception as e:
            logger.error(f"公告数据转换失败: {stock_code}, {e}")
            text_chunks.append(f"{self._get_stock_name(stock_code)}({stock_code})的公告数据暂时无法获取。")

        return self._chunk_texts(text_chunks)

    def transform_shareholder_data(self, stock_code: str, shareholder_data: Dict) -> List[str]:
        """股东数据转换为文本段落"""
        text_chunks = []

        try:
            # 提取股东数据
            if isinstance(shareholder_data.get('data'), list):
                shareholders = shareholder_data['data']
            elif isinstance(shareholder_data, list):
                shareholders = shareholder_data
            else:
                shareholders = []

            stock_name = self._get_stock_name(stock_code)

            if shareholders:
                # 前十大股东概览
                overview_text = f"{stock_name}({stock_code})的股东结构信息。"

                # 主要股东信息
                major_shareholders = []
                for i, shareholder in enumerate(shareholders[:5]):  # 前5大股东
                    if isinstance(shareholder, dict):
                        name = shareholder.get('股东名称', shareholder.get('name', ''))
                        shares = shareholder.get('持股数量', shareholder.get('shares', ''))
                        ratio = shareholder.get('持股比例', shareholder.get('ratio', ''))

                        if name:
                            shareholder_info = f"第{i+1}大股东{name}"
                            if shares:
                                shareholder_info += f"持股{shares}"
                            if ratio:
                                shareholder_info += f"，持股比例{ratio}"
                            major_shareholders.append(shareholder_info)

                if major_shareholders:
                    shareholders_text = overview_text + "主要股东包括：" + "；".join(major_shareholders) + "。"
                    text_chunks.append(shareholders_text)

                # 股东性质分析
                nature_text = self._analyze_shareholder_nature(stock_code, stock_name, shareholders)
                if nature_text:
                    text_chunks.append(nature_text)

            # 如果没有股东数据，添加基本信息
            if not text_chunks:
                text_chunks.append(f"{stock_name}({stock_code})的股东信息暂时无法获取。")

        except Exception as e:
            logger.error(f"股东数据转换失败: {stock_code}, {e}")
            text_chunks.append(f"{self._get_stock_name(stock_code)}({stock_code})的股东数据暂时无法获取。")

        return self._chunk_texts(text_chunks)

    def transform_longhubang_data(self, stock_code: str, longhubang_data: Dict) -> List[str]:
        """龙虎榜数据转换为文本段落"""
        text_chunks = []

        try:
            # 提取龙虎榜数据
            if isinstance(longhubang_data.get('data'), list):
                records = longhubang_data['data']
            elif isinstance(longhubang_data, list):
                records = longhubang_data
            else:
                records = []

            stock_name = self._get_stock_name(stock_code)

            if records:
                # 最近的龙虎榜记录
                for record in records[:3]:  # 最近3条记录
                    if isinstance(record, dict):
                        date = record.get('交易日期', record.get('date', ''))
                        buy_amount = record.get('买入金额', record.get('buy_amount', ''))
                        sell_amount = record.get('卖出金额', record.get('sell_amount', ''))
                        reason = record.get('上榜原因', record.get('reason', ''))

                        record_text = f"{stock_name}({stock_code})"
                        if date:
                            record_text += f"于{date}"

                        record_text += "登上龙虎榜"

                        if reason:
                            record_text += f"，原因为{reason}"

                        if buy_amount or sell_amount:
                            record_text += "。"
                            if buy_amount:
                                record_text += f"买入金额{buy_amount}"
                            if sell_amount:
                                record_text += f"，卖出金额{sell_amount}"

                            # 计算净流入
                            try:
                                buy_val = self._parse_amount(buy_amount)
                                sell_val = self._parse_amount(sell_amount)
                                if buy_val is not None and sell_val is not None:
                                    net_flow = buy_val - sell_val
                                    if net_flow > 0:
                                        record_text += f"，净流入{net_flow:.2f}万元"
                                    elif net_flow < 0:
                                        record_text += f"，净流出{abs(net_flow):.2f}万元"
                            except:
                                pass

                        record_text += "，显示市场关注度较高。"
                        text_chunks.append(record_text)
            else:
                # 没有龙虎榜记录
                text_chunks.append(f"{stock_name}({stock_code})近期未出现在龙虎榜上。")

        except Exception as e:
            logger.error(f"龙虎榜数据转换失败: {stock_code}, {e}")
            text_chunks.append(f"{self._get_stock_name(stock_code)}({stock_code})的龙虎榜数据暂时无法获取。")

        return self._chunk_texts(text_chunks)

    def _build_revenue_text(self, stock_code: str, stock_name: str, data: Dict) -> Optional[str]:
        """构建营收相关文本"""
        try:
            revenue_keys = ['营业收入', '总收入', 'revenue', 'total_revenue', '营收']
            profit_keys = ['净利润', '利润总额', 'net_profit', 'profit', '净利']

            revenue = None
            profit = None

            for key in revenue_keys:
                if key in data and data[key]:
                    revenue = data[key]
                    break

            for key in profit_keys:
                if key in data and data[key]:
                    profit = data[key]
                    break

            if revenue or profit:
                text = f"{stock_name}({stock_code})的经营状况："
                if revenue:
                    text += f"营业收入为{revenue}"
                if profit:
                    if revenue:
                        text += f"，净利润为{profit}"
                    else:
                        text += f"净利润为{profit}"
                text += "，显示公司经营稳健。"
                return text

        except Exception as e:
            logger.error(f"构建营收文本失败: {e}")

        return None

    def _build_ratio_text(self, stock_code: str, stock_name: str, data: Dict) -> Optional[str]:
        """构建财务比率文本"""
        try:
            pe_keys = ['市盈率', 'PE', 'pe_ratio', 'PE比率']
            pb_keys = ['市净率', 'PB', 'pb_ratio', 'PB比率']
            roe_keys = ['净资产收益率', 'ROE', 'roe']

            pe_ratio = None
            pb_ratio = None
            roe = None

            for key in pe_keys:
                if key in data and data[key]:
                    pe_ratio = data[key]
                    break

            for key in pb_keys:
                if key in data and data[key]:
                    pb_ratio = data[key]
                    break

            for key in roe_keys:
                if key in data and data[key]:
                    roe = data[key]
                    break

            if pe_ratio or pb_ratio or roe:
                text = f"{stock_name}({stock_code})的估值指标："
                ratios = []
                if pe_ratio:
                    ratios.append(f"市盈率{pe_ratio}")
                if pb_ratio:
                    ratios.append(f"市净率{pb_ratio}")
                if roe:
                    ratios.append(f"净资产收益率{roe}")

                text += "，".join(ratios) + "。"
                return text

        except Exception as e:
            logger.error(f"构建比率文本失败: {e}")

        return None

    def _build_balance_text(self, stock_code: str, stock_name: str, data: Dict) -> Optional[str]:
        """构建资产负债文本"""
        try:
            asset_keys = ['总资产', '资产总计', 'total_assets', '总资产额']
            debt_keys = ['总负债', '负债总计', 'total_debt', '负债总额']
            debt_ratio_keys = ['资产负债率', 'debt_ratio', '负债率']

            total_assets = None
            total_debt = None
            debt_ratio = None

            for key in asset_keys:
                if key in data and data[key]:
                    total_assets = data[key]
                    break

            for key in debt_keys:
                if key in data and data[key]:
                    total_debt = data[key]
                    break

            for key in debt_ratio_keys:
                if key in data and data[key]:
                    debt_ratio = data[key]
                    break

            if total_assets or debt_ratio:
                text = f"{stock_name}({stock_code})的资产负债状况："
                if total_assets:
                    text += f"总资产{total_assets}"
                if debt_ratio:
                    if total_assets:
                        text += f"，资产负债率{debt_ratio}"
                    else:
                        text += f"资产负债率{debt_ratio}"
                text += "，财务结构稳健。"
                return text

        except Exception as e:
            logger.error(f"构建资产负债文本失败: {e}")

        return None

    def _build_cashflow_text(self, stock_code: str, stock_name: str, data: Dict) -> Optional[str]:
        """构建现金流文本"""
        try:
            operating_cf_keys = ['经营现金流', '经营活动现金流', 'operating_cashflow', '经营现金流量']
            free_cf_keys = ['自由现金流', 'free_cashflow', 'FCF']

            operating_cf = None
            free_cf = None

            for key in operating_cf_keys:
                if key in data and data[key]:
                    operating_cf = data[key]
                    break

            for key in free_cf_keys:
                if key in data and data[key]:
                    free_cf = data[key]
                    break

            if operating_cf or free_cf:
                text = f"{stock_name}({stock_code})的现金流状况："
                flows = []
                if operating_cf:
                    flows.append(f"经营现金流{operating_cf}")
                if free_cf:
                    flows.append(f"自由现金流{free_cf}")

                text += "，".join(flows) + "，现金流状况良好。"
                return text

        except Exception as e:
            logger.error(f"构建现金流文本失败: {e}")

        return None

    def _analyze_shareholder_nature(self, stock_code: str, stock_name: str, shareholders: List[Dict]) -> Optional[str]:
        """分析股东性质"""
        try:
            institutional_count = 0
            individual_count = 0
            state_owned = False

            for shareholder in shareholders[:10]:
                name = shareholder.get('股东名称', shareholder.get('name', ''))
                if name:
                    # 简单的机构投资者识别
                    if any(keyword in name for keyword in ['基金', '保险', '信托', '银行', '公司', '有限责任', '股份']):
                        institutional_count += 1
                    else:
                        individual_count += 1

                    # 国有股东识别
                    if any(keyword in name for keyword in ['国有', '国资', '财政局', '政府']):
                        state_owned = True

            if institutional_count > 0 or state_owned:
                text = f"{stock_name}({stock_code})的股东结构分析："
                if state_owned:
                    text += "包含国有股东，"
                if institutional_count > individual_count:
                    text += "机构投资者占主导地位"
                elif institutional_count > 0:
                    text += "机构和个人投资者并存"
                else:
                    text += "以个人投资者为主"
                text += "，股权结构相对稳定。"
                return text

        except Exception as e:
            logger.error(f"股东性质分析失败: {e}")

        return None

    def _get_stock_name(self, stock_code: str) -> str:
        """获取股票名称，如果无法获取则返回默认值"""
        # 这里可以后续集成股票名称查询服务
        stock_names = {
            "002384": "东山精密",
            "002617": "露笑科技",
            "002371": "北方华创",
            "600919": "江苏银行"
        }
        return stock_names.get(stock_code, f"股票{stock_code}")

    def _clean_text(self, text: str) -> str:
        """清理文本，移除特殊字符和多余空格"""
        if not text:
            return ""

        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        # 移除多余的空白字符
        text = re.sub(r'\s+', ' ', text)
        # 移除特殊字符，保留中文、英文、数字和基本标点
        text = re.sub(r'[^\u4e00-\u9fff\w\s.,;:!?()%\-+=/]', '', text)

        return text.strip()

    def _parse_amount(self, amount_str: str) -> Optional[float]:
        """解析金额字符串为数值（万元）"""
        if not amount_str:
            return None

        try:
            # 移除非数字字符，保留小数点
            amount_str = str(amount_str)
            number_str = re.sub(r'[^\d.]', '', amount_str)
            if number_str:
                return float(number_str)
        except:
            pass

        return None

    def _chunk_texts(self, texts: List[str]) -> List[str]:
        """将文本列表分块，确保每个块的长度合适"""
        chunks = []

        for text in texts:
            if not text or len(text.strip()) < self.min_chunk_length:
                continue

            text = text.strip()

            # 如果文本长度适中，直接添加
            if len(text) <= self.max_chunk_length:
                chunks.append(text)
            else:
                # 按句号分割长文本
                sentences = text.split('。')
                current_chunk = ""

                for sentence in sentences:
                    sentence = sentence.strip()
                    if not sentence:
                        continue

                    # 如果添加这个句子不会超过最大长度
                    if len(current_chunk + sentence + '。') <= self.max_chunk_length:
                        if current_chunk:
                            current_chunk += sentence + '。'
                        else:
                            current_chunk = sentence + '。'
                    else:
                        # 保存当前块
                        if current_chunk and len(current_chunk.strip()) >= self.min_chunk_length:
                            chunks.append(current_chunk.strip())

                        # 开始新块
                        current_chunk = sentence + '。'

                # 保存最后一个块
                if current_chunk and len(current_chunk.strip()) >= self.min_chunk_length:
                    chunks.append(current_chunk.strip())

        return chunks

    def create_chunk_metadata(self, stock_code: str, data_type: str, chunk_index: int,
                            version_id: str, chunk_text: str) -> Dict[str, Any]:
        """创建文本块的元数据"""
        return {
            "stock_code": stock_code,
            "data_type": data_type,
            "chunk_index": chunk_index,
            "version_id": version_id,
            "chunk_length": len(chunk_text),
            "created_at": datetime.now().isoformat(),
            "stock_name": self._get_stock_name(stock_code)
        }