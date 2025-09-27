#!/usr/bin/env python3
"""
独立翻译服务
提供HTTP API接口，隔离翻译功能与RAG系统
"""

import sys
import os
import json
import hashlib
import time
from datetime import datetime
from typing import Optional, Dict
import requests
from langdetect import detect, DetectorFactory

# 设置langdetect为确定性
DetectorFactory.seed = 0

class TranslationService:
    def __init__(self):
        self.translation_cache = {}
        self.stats = {
            'total_requests': 0,
            'cache_hits': 0,
            'translations': 0,
            'errors': 0
        }

    def detect_language(self, text: str) -> str:
        """检测文本语言"""
        try:
            # 只检测前500个字符避免太长文本
            sample_text = text[:500]
            lang = detect(sample_text)
            return lang
        except Exception as e:
            print(f"⚠️ 语言检测失败: {e}")
            return 'unknown'

    def translate_text(self, text: str, source_lang: str = 'auto', target_lang: str = 'zh-CN') -> Dict:
        """
        翻译文本
        返回: {
            'success': bool,
            'original_text': str,
            'translated_text': str,
            'detected_language': str,
            'translation_needed': bool,
            'cached': bool,
            'error': str (if any)
        }
        """
        self.stats['total_requests'] += 1

        if not text or not text.strip():
            return {
                'success': True,
                'original_text': text,
                'translated_text': text,
                'detected_language': 'unknown',
                'translation_needed': False,
                'cached': False
            }

        # 生成缓存key
        text_hash = hashlib.md5(text.encode()).hexdigest()

        # 检查缓存
        if text_hash in self.translation_cache:
            self.stats['cache_hits'] += 1
            result = self.translation_cache[text_hash].copy()
            result['cached'] = True
            return result

        try:
            # 检测语言
            detected_lang = self.detect_language(text)

            # 如果是中文，不需要翻译
            if detected_lang in ['zh', 'zh-cn', 'zh-tw']:
                result = {
                    'success': True,
                    'original_text': text,
                    'translated_text': text,
                    'detected_language': detected_lang,
                    'translation_needed': False,
                    'cached': False
                }
                self.translation_cache[text_hash] = result.copy()
                return result

            # 需要翻译
            translated_text = self._perform_translation(text, detected_lang, target_lang)

            result = {
                'success': True,
                'original_text': text,
                'translated_text': translated_text,
                'detected_language': detected_lang,
                'translation_needed': True,
                'cached': False
            }

            # 缓存结果
            self.translation_cache[text_hash] = result.copy()
            self.stats['translations'] += 1

            return result

        except Exception as e:
            self.stats['errors'] += 1
            error_msg = f"Translation error: {str(e)}"
            print(f"❌ {error_msg}")

            return {
                'success': False,
                'original_text': text,
                'translated_text': text,  # 返回原文作为fallback
                'detected_language': 'unknown',
                'translation_needed': True,
                'cached': False,
                'error': error_msg
            }

    def _perform_translation(self, text: str, source_lang: str, target_lang: str) -> str:
        """
        执行实际翻译 - 可以替换为不同的翻译服务
        """
        # 方法1: 使用deep_translator (如果可用)
        try:
            from deep_translator import GoogleTranslator
            translator = GoogleTranslator(source='auto', target=target_lang)
            return translator.translate(text)
        except ImportError:
            pass
        except Exception as e:
            print(f"⚠️ deep_translator失败: {e}")

        # 方法2: 简单的Mock翻译 (用于测试)
        print(f"🔄 Mock翻译: {source_lang} -> {target_lang}")
        return f"[翻译] {text}"

    def get_stats(self) -> Dict:
        """获取翻译服务统计信息"""
        cache_hit_rate = 0
        if self.stats['total_requests'] > 0:
            cache_hit_rate = self.stats['cache_hits'] / self.stats['total_requests'] * 100

        return {
            **self.stats,
            'cache_hit_rate': f"{cache_hit_rate:.1f}%",
            'cache_size': len(self.translation_cache),
            'status': 'running'
        }

    def batch_translate(self, texts: list, source_lang: str = 'auto', target_lang: str = 'zh-CN') -> list:
        """批量翻译"""
        results = []
        for text in texts:
            result = self.translate_text(text, source_lang, target_lang)
            results.append(result)
            # 避免请求过于频繁
            time.sleep(0.1)
        return results

# HTTP服务接口 (简化版本，可以用Flask/FastAPI扩展)
class SimpleTranslationServer:
    def __init__(self):
        self.service = TranslationService()

    def handle_translate_request(self, data: Dict) -> Dict:
        """处理翻译请求"""
        text = data.get('text', '')
        source_lang = data.get('source_lang', 'auto')
        target_lang = data.get('target_lang', 'zh-CN')

        return self.service.translate_text(text, source_lang, target_lang)

    def handle_batch_translate_request(self, data: Dict) -> Dict:
        """处理批量翻译请求"""
        texts = data.get('texts', [])
        source_lang = data.get('source_lang', 'auto')
        target_lang = data.get('target_lang', 'zh-CN')

        results = self.service.batch_translate(texts, source_lang, target_lang)

        return {
            'success': True,
            'results': results,
            'total_processed': len(results)
        }

    def handle_stats_request(self) -> Dict:
        """处理统计信息请求"""
        return self.service.get_stats()

# 命令行测试接口
def test_translation_service():
    """测试翻译服务"""
    print("🧪 测试翻译服务...")

    service = TranslationService()

    # 测试用例
    test_cases = [
        "Hello world",
        "The Federal Reserve announces new policy",
        "你好世界",  # 中文测试
        "Thomson Reuters reports Q3 earnings",
        ""  # 空文本测试
    ]

    for text in test_cases:
        print(f"\n📝 测试文本: {text[:50]}...")
        result = service.translate_text(text)
        print(f"✅ 成功: {result['success']}")
        print(f"🌍 检测语言: {result['detected_language']}")
        print(f"🔄 需要翻译: {result['translation_needed']}")
        print(f"💾 缓存命中: {result['cached']}")
        if result['success']:
            print(f"📄 译文: {result['translated_text'][:100]}...")
        if 'error' in result:
            print(f"❌ 错误: {result['error']}")

    # 显示统计
    print(f"\n📊 服务统计:")
    stats = service.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_translation_service()
    else:
        print("🌐 翻译服务启动")
        print("使用方法:")
        print("  python3 translation_service.py test  # 运行测试")
        server = SimpleTranslationServer()
        print("✅ 翻译服务已就绪")