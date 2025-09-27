import re
import logging
from typing import List
import jieba

logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    """清理文本内容"""
    if not text:
        return ""

    # 移除HTML标签
    text = re.sub(r'<[^>]+>', '', text)

    # 移除多余的空白字符
    text = re.sub(r'\s+', ' ', text)

    # 移除特殊字符，保留中文、英文、数字和基本标点
    text = re.sub(r'[^\u4e00-\u9fff\w\s.,!?;:()（）【】「」\-]', '', text)

    return text.strip()


def split_text_into_chunks(
    text: str,
    max_chunk_size: int = 500,
    overlap_size: int = 50
) -> List[str]:
    """将长文本分割为重叠的文本块"""
    if not text or len(text) <= max_chunk_size:
        return [text] if text else []

    chunks = []
    start = 0

    while start < len(text):
        end = min(start + max_chunk_size, len(text))

        # 尝试在句子边界分割
        if end < len(text):
            # 查找最近的句号、问号、感叹号
            sentence_end = max(
                text.rfind('。', start, end),
                text.rfind('！', start, end),
                text.rfind('？', start, end)
            )

            if sentence_end > start:
                end = sentence_end + 1

        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)

        # 计算下一个chunk的起始位置，考虑重叠
        if end >= len(text):
            break

        start = max(start + max_chunk_size - overlap_size, end - overlap_size)

    return chunks


def extract_keywords(text: str, top_k: int = 10) -> List[str]:
    """提取文本关键词"""
    try:
        # 使用jieba进行中文分词
        words = jieba.cut(text)

        # 过滤停用词和短词
        stop_words = {'的', '了', '在', '是', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}

        keywords = [word.strip() for word in words
                   if len(word.strip()) > 1 and word.strip() not in stop_words]

        # 简单频率统计
        word_freq = {}
        for word in keywords:
            word_freq[word] = word_freq.get(word, 0) + 1

        # 按频率排序返回top_k
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        return [word for word, freq in sorted_words[:top_k]]

    except Exception as e:
        logger.warning(f"关键词提取失败: {str(e)}")
        return []


def calculate_text_quality_score(text: str) -> float:
    """计算文本质量评分"""
    if not text or not text.strip():
        return 0.0

    score = 0.0

    # 长度评分 (0.3权重)
    length = len(text.strip())
    if length < 50:
        length_score = length / 50 * 0.5
    elif length < 200:
        length_score = 0.5 + (length - 50) / 150 * 0.3
    else:
        length_score = 0.8 + min((length - 200) / 800, 0.2)

    score += length_score * 0.3

    # 信息密度评分 (0.3权重)
    # 计算中文字符和数字的比例
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', text))
    digits = len(re.findall(r'\d', text))
    info_density = (chinese_chars + digits * 0.5) / length if length > 0 else 0
    score += min(info_density, 1.0) * 0.3

    # 结构化程度评分 (0.2权重)
    # 检查是否包含标点符号
    punctuation_count = len(re.findall(r'[。！？，；：]', text))
    structure_score = min(punctuation_count / (length / 50), 1.0) if length > 0 else 0
    score += structure_score * 0.2

    # 重复度评分 (0.2权重)
    # 简单检查重复短语
    words = text.split()
    unique_words = len(set(words))
    total_words = len(words)
    uniqueness = unique_words / total_words if total_words > 0 else 1.0
    score += uniqueness * 0.2

    return min(score, 1.0)


def is_financial_relevant(text: str) -> bool:
    """判断文本是否与金融相关"""
    financial_keywords = [
        '股票', '股价', '市场', '投资', '收益', '利润', '财报', '业绩',
        '涨跌', '交易', '基金', '债券', '银行', '保险', '证券',
        '上市', 'IPO', '股东', '分红', '重组', '并购', '估值',
        '营收', '净利', '资产', '负债', '现金流', '毛利率'
    ]

    text_lower = text.lower()
    for keyword in financial_keywords:
        if keyword in text:
            return True

    return False