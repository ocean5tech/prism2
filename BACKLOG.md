# Prism2 开发积压清单 (BACKLOG)

## 🔄 待开发功能

### 🌍 翻译服务优化 (HIGH PRIORITY)

**背景**: 当前隔离架构使用Mock翻译，需要集成真实翻译API

**具体任务**:
1. **语言检测优化**:
   - 混合语言检测准确率从25%提升到80%+
   - 优化langdetect配置或替换更准确的检测算法

2. **翻译API集成**:
   - 将Mock翻译替换为Google Translate/DeepL/百度翻译
   - 实现多翻译服务的主备切换机制
   - 添加API配额管理和限流控制

3. **中文跳过率优化**:
   - 中文文章翻译跳过率从40%提升到90%+
   - 完善中文语言识别规则

4. **网络连接优化**:
   - 增强外部RSS源连接稳定性
   - 添加重试机制和错误恢复

**技术方案**:
```python
# 建议的翻译服务架构
class EnhancedTranslationService:
    def __init__(self):
        self.primary_translator = GoogleTranslator()
        self.fallback_translator = BaiduTranslator()
        self.language_detector = EnhancedLanguageDetector()

    def translate_with_fallback(self, text):
        try:
            return self.primary_translator.translate(text)
        except Exception:
            return self.fallback_translator.translate(text)
```

**预估工作量**: 2-3周
**优先级**: HIGH
**负责人**: 待分配

---

*创建时间: 2025-09-17*
*状态: 待开发*