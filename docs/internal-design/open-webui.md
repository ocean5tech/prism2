# Open WebUI - 内部设计文档

## 📋 基本信息

- **模块名称**: Open WebUI (AI模型管理界面)
- **技术栈**: Open WebUI + Docker + Ollama集成
- **部署端口**: 3001
- **依据**: 外部设计文档规范

---

## 📁 文件结构和权限

```
/home/wyatt/prism2/open-webui/
├── docker-compose.yml                    # Docker编排配置 (644)
├── .env                                  # 环境变量 (600)
├── config/                               # 配置目录 (755)
│   ├── nginx.conf                        # Nginx配置 (644)
│   ├── auth_config.json                  # 认证配置 (644)
│   └── model_config.json                 # 模型配置 (644)
├── data/                                 # 数据持久化目录 (755)
│   ├── database/                         # 数据库文件 (755)
│   ├── uploads/                          # 文件上传 (755)
│   └── logs/                             # 日志文件 (755)
├── customizations/                       # 自定义配置 (755)
│   ├── themes/                           # 主题样式 (755)
│   │   └── prism2-theme.css             # 自定义主题 (644)
│   ├── prompts/                          # 预设提示词 (755)
│   │   ├── financial_analysis.json      # 金融分析提示词 (644)
│   │   ├── stock_research.json          # 股票研究提示词 (644)
│   │   └── investment_advice.json       # 投资建议提示词 (644)
│   └── models/                           # 模型管理脚本 (755)
│       ├── model_downloader.py          # 模型下载脚本 (755)
│       └── model_validator.py           # 模型验证脚本 (755)
├── scripts/                              # 运维脚本 (755)
│   ├── backup.sh                         # 数据备份脚本 (755)
│   ├── restore.sh                        # 数据恢复脚本 (755)
│   └── health_check.sh                   # 健康检查脚本 (755)
└── README.md                            # 部署说明 (644)
```

---

## 🐳 Docker容器配置

### Docker Compose配置 (docker-compose.yml)
```yaml
version: '3.8'

services:
  open-webui:
    image: ghcr.io/open-webui/open-webui:main
    container_name: prism2-open-webui
    restart: unless-stopped
    ports:
      - "3001:8080"
    environment:
      # 基础配置
      - WEBUI_SECRET_KEY=${WEBUI_SECRET_KEY}
      - WEBUI_NAME=Prism2 AI Lab
      - WEBUI_URL=http://localhost:3001

      # Ollama连接配置
      - OLLAMA_BASE_URL=http://host.docker.internal:11434
      - ENABLE_OLLAMA_API=true

      # === 外部服务集成配置 ===
      - STOCK_SERVICE_URL=http://host.docker.internal:8000
      - RAG_SERVICE_URL=http://host.docker.internal:8001
      - AUTH_SERVICE_URL=http://host.docker.internal:8004
      - NEWS_SERVICE_URL=http://host.docker.internal:8005

      # RAG增强功能配置
      - ENABLE_RAG_ENHANCED_CHAT=true
      - RAG_CONTEXT_LIMIT=5
      - ENABLE_REALTIME_DATA=true
      - ENABLE_NEWS_INTEGRATION=true

      # 认证配置
      - ENABLE_SIGNUP=${ENABLE_SIGNUP:-false}
      - DEFAULT_USER_ROLE=${DEFAULT_USER_ROLE:-user}
      - ENABLE_LOGIN_FORM=true
      - ENABLE_EXTERNAL_AUTH=true

      # 功能配置 (调整为金融场景)
      - ENABLE_MODEL_FILTER=true
      - ENABLE_WEB_SEARCH=false
      - ENABLE_IMAGE_GENERATION=false
      - ENABLE_COMMUNITY_SHARING=false
      - ENABLE_STOCK_ANALYSIS_MODE=true

      # 存储配置
      - DATA_DIR=/app/backend/data
      - UPLOAD_DIR=/app/backend/data/uploads

      # 自定义配置
      - CUSTOM_THEME_PATH=/app/backend/data/themes
      - DEFAULT_PROMPT_TEMPLATE_PATH=/app/backend/data/prompts

    volumes:
      # 数据持久化
      - ./data:/app/backend/data

      # 自定义配置
      - ./customizations/themes:/app/backend/data/themes:ro
      - ./customizations/prompts:/app/backend/data/prompts:ro

      # 配置文件
      - ./config/auth_config.json:/app/backend/data/config/auth_config.json:ro

    networks:
      - prism2-network

    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

  # Nginx反向代理 (可选)
  nginx:
    image: nginx:alpine
    container_name: prism2-webui-nginx
    restart: unless-stopped
    ports:
      - "3001:80"
    volumes:
      - ./config/nginx.conf:/etc/nginx/nginx.conf:ro
    depends_on:
      - open-webui
    networks:
      - prism2-network
    profiles:
      - "with-nginx"

networks:
  prism2-network:
    external: true
    name: prism2_default

volumes:
  webui_data:
    driver: local
```

---

## 🔧 核心配置管理

### 模型配置 (config/model_config.json)
```json
{
  "default_models": {
    "primary": "qwen2.5:7b",
    "fallback": "deepseek-coder:1.3b"
  },
  "model_settings": {
    "qwen2.5:7b": {
      "display_name": "Qwen2.5-7B (通用分析)",
      "description": "适用于综合金融分析和投资建议",
      "default_parameters": {
        "temperature": 0.7,
        "top_p": 0.9,
        "max_tokens": 2048,
        "context_length": 8192
      },
      "system_prompts": {
        "default": "你是一位专业的金融分析师，具有丰富的股票投资经验。请基于提供的信息给出客观、专业的分析建议。",
        "technical": "你是技术分析专家，专注于K线图表、技术指标分析和市场趋势判断。",
        "fundamental": "你是基本面分析专家，专注于财务报表分析、公司估值和行业比较。"
      },
      "use_cases": ["投资分析", "市场预测", "风险评估", "策略建议"]
    },
    "deepseek-coder:1.3b": {
      "display_name": "DeepSeek-Coder-1.3B (代码生成)",
      "description": "专门用于代码生成和技术实现",
      "default_parameters": {
        "temperature": 0.3,
        "top_p": 0.8,
        "max_tokens": 1024,
        "context_length": 4096
      },
      "system_prompts": {
        "default": "你是一位资深程序员，专注于Python和JavaScript开发。请提供清晰、高效的代码解决方案。",
        "financial": "你是金融科技开发专家，熟悉金融数据处理和量化分析编程。"
      },
      "use_cases": ["代码生成", "算法实现", "数据处理", "API开发"]
    }
  },
  "auto_load_models": true,
  "model_timeout": 300,
  "concurrent_requests": 5
}
```

### 认证配置 (config/auth_config.json)
```json
{
  "authentication": {
    "method": "local",
    "session_duration": 86400,
    "enable_registration": false,
    "require_email_verification": false
  },
  "default_users": [
    {
      "email": "admin@prism2.local",
      "name": "Prism2 Admin",
      "role": "admin",
      "password_hash": "$2b$12$..."
    }
  ],
  "user_roles": {
    "admin": {
      "permissions": ["model:manage", "user:manage", "system:config"],
      "model_access": ["all"],
      "rate_limits": {
        "requests_per_minute": 100,
        "max_tokens_per_day": 50000
      }
    },
    "user": {
      "permissions": ["chat:create", "model:use"],
      "model_access": ["qwen2.5:7b"],
      "rate_limits": {
        "requests_per_minute": 20,
        "max_tokens_per_day": 10000
      }
    },
    "guest": {
      "permissions": ["chat:read"],
      "model_access": [],
      "rate_limits": {
        "requests_per_minute": 5,
        "max_tokens_per_day": 1000
      }
    }
  },
  "security": {
    "session_secret": "your-session-secret-key",
    "csrf_protection": true,
    "rate_limiting": true,
    "ip_whitelist": []
  }
}
```

---

## 🎨 界面自定义配置

### 自定义主题 (customizations/themes/prism2-theme.css)
```css
/* Prism2 专用主题样式 */
:root {
  /* 主色调 - 金融蓝 */
  --primary-color: #1e3a8a;
  --primary-light: #3b82f6;
  --primary-dark: #1e40af;

  /* 辅助色调 */
  --success-color: #059669;  /* 涨幅绿 */
  --danger-color: #dc2626;   /* 跌幅红 */
  --warning-color: #d97706;  /* 警告橙 */
  --info-color: #0891b2;     /* 信息青 */

  /* 背景色 */
  --bg-primary: #ffffff;
  --bg-secondary: #f8fafc;
  --bg-tertiary: #e2e8f0;

  /* 文字色 */
  --text-primary: #1f2937;
  --text-secondary: #6b7280;
  --text-muted: #9ca3af;

  /* 边框和阴影 */
  --border-color: #e5e7eb;
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1);
}

/* 顶部导航栏 */
.navbar {
  background: linear-gradient(135deg, var(--primary-color), var(--primary-light));
  border-bottom: 1px solid var(--border-color);
}

.navbar-brand {
  font-weight: 700;
  color: white !important;
}

.navbar-brand::before {
  content: "🔮 ";
  margin-right: 0.5rem;
}

/* 侧边栏 */
.sidebar {
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
}

.sidebar .nav-item.active {
  background: var(--primary-light);
  color: white;
  border-radius: 0.375rem;
}

/* 聊天界面 */
.chat-container {
  background: var(--bg-primary);
}

.message.user {
  background: var(--primary-light);
  color: white;
  border-radius: 1rem 1rem 0.25rem 1rem;
}

.message.assistant {
  background: var(--bg-secondary);
  color: var(--text-primary);
  border-radius: 1rem 1rem 1rem 0.25rem;
  border-left: 3px solid var(--primary-color);
}

/* 模型选择器 */
.model-selector {
  border: 2px solid var(--primary-light);
  border-radius: 0.5rem;
  background: var(--bg-primary);
}

.model-selector.active {
  background: var(--primary-light);
  color: white;
}

/* 按钮样式 */
.btn-primary {
  background: var(--primary-color);
  border-color: var(--primary-color);
}

.btn-primary:hover {
  background: var(--primary-dark);
  border-color: var(--primary-dark);
}

/* 代码块样式 */
.code-block {
  background: #1f2937;
  color: #f9fafb;
  border-radius: 0.5rem;
  border-left: 4px solid var(--primary-light);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .sidebar {
    transform: translateX(-100%);
    transition: transform 0.3s ease;
  }

  .sidebar.open {
    transform: translateX(0);
  }
}

/* 滚动条样式 */
::-webkit-scrollbar {
  width: 8px;
}

::-webkit-scrollbar-track {
  background: var(--bg-secondary);
}

::-webkit-scrollbar-thumb {
  background: var(--primary-light);
  border-radius: 4px;
}

::-webkit-scrollbar-thumb:hover {
  background: var(--primary-dark);
}
```

---

## 📝 预设提示词库

### 金融分析提示词 (customizations/prompts/financial_analysis.json)
```json
{
  "name": "financial_analysis_prompts",
  "version": "1.0",
  "prompts": [
    {
      "id": "comprehensive_analysis",
      "title": "综合投资分析",
      "category": "investment",
      "system_prompt": "你是一位资深的金融投资分析师，拥有15年的A股和港股投资经验。请基于提供的股票信息，从技术面、基本面、消息面三个维度进行全面分析，并给出明确的投资建议和风险提示。",
      "user_template": "请分析股票 {stock_code} ({stock_name}) 的投资价值。\n\n当前信息：\n- 股价：{current_price}\n- 涨跌幅：{change_percent}%\n- 市值：{market_cap}\n- PE：{pe_ratio}\n- 最新财报：{latest_financial}\n\n请给出详细的投资分析报告。",
      "parameters": {
        "temperature": 0.7,
        "max_tokens": 2048
      }
    },
    {
      "id": "technical_analysis",
      "title": "技术分析",
      "category": "technical",
      "system_prompt": "你是专业的技术分析师，精通各种技术指标和图表分析。请基于K线数据和技术指标，分析股票的技术走势，识别支撑阻力位，判断趋势方向。",
      "user_template": "请对股票 {stock_code} 进行技术分析：\n\nK线数据：{kline_data}\n技术指标：{technical_indicators}\n\n请分析：\n1. 当前趋势方向\n2. 关键支撑阻力位\n3. 买卖点建议\n4. 风险控制策略",
      "parameters": {
        "temperature": 0.6,
        "max_tokens": 1536
      }
    },
    {
      "id": "fundamental_analysis",
      "title": "基本面分析",
      "category": "fundamental",
      "system_prompt": "你是基本面分析专家，专注于财务报表分析、行业比较和估值研究。请深入分析公司的盈利能力、成长性、财务健康度和估值水平。",
      "user_template": "请分析 {company_name} ({stock_code}) 的基本面：\n\n财务数据：{financial_data}\n行业信息：{industry_info}\n竞争对手：{competitors}\n\n请重点分析：\n1. 盈利能力和成长性\n2. 财务健康状况\n3. 估值水平\n4. 行业地位和竞争优势",
      "parameters": {
        "temperature": 0.5,
        "max_tokens": 2048
      }
    },
    {
      "id": "risk_assessment",
      "title": "风险评估",
      "category": "risk",
      "system_prompt": "你是风险管理专家，专门识别和评估投资风险。请全面分析股票投资的各类风险，并提供风险控制建议。",
      "user_template": "请评估股票 {stock_code} 的投资风险：\n\n公司信息：{company_info}\n市场环境：{market_environment}\n近期新闻：{recent_news}\n\n请分析：\n1. 系统性风险\n2. 非系统性风险\n3. 流动性风险\n4. 风险控制策略",
      "parameters": {
        "temperature": 0.4,
        "max_tokens": 1536
      }
    }
  ]
}
```

### 股票研究提示词 (customizations/prompts/stock_research.json)
```json
{
  "name": "stock_research_prompts",
  "version": "1.0",
  "prompts": [
    {
      "id": "company_profile",
      "title": "公司研究报告",
      "category": "research",
      "system_prompt": "你是专业的股票研究分析师，擅长撰写深度研究报告。请基于公司信息，撰写结构清晰、逻辑严密的研究报告。",
      "user_template": "请为 {company_name} 撰写研究报告：\n\n公司基本信息：{basic_info}\n业务模式：{business_model}\n财务数据：{financial_data}\n\n报告结构：\n1. 公司概况\n2. 业务分析\n3. 财务分析\n4. 竞争力评估\n5. 投资评级",
      "parameters": {
        "temperature": 0.6,
        "max_tokens": 3072
      }
    },
    {
      "id": "industry_analysis",
      "title": "行业分析",
      "category": "industry",
      "system_prompt": "你是行业研究专家，对各个行业的发展趋势、竞争格局、政策影响有深入了解。请分析行业现状和前景。",
      "user_template": "请分析 {industry_name} 行业：\n\n行业数据：{industry_data}\n政策环境：{policy_environment}\n主要公司：{major_companies}\n\n请分析：\n1. 行业发展趋势\n2. 竞争格局\n3. 投资机会\n4. 风险因素",
      "parameters": {
        "temperature": 0.7,
        "max_tokens": 2048
      }
    }
  ]
}
```

---

## 🔌 API接口集成 (严格按照外部设计)

### 核心接口定义 (遵循外部设计规范)
```python
# === RAG增强聊天接口 (核心功能) ===
class EnhancedChatRequest(BaseModel):
    message: str                           # 用户消息
    stock_context: str = None              # 股票代码上下文
    enable_rag: bool = True                # 启用RAG增强
    enable_realtime: bool = True           # 启用实时数据
    model: str = "qwen2.5:7b"             # 使用的模型
    system_prompt: str = None              # 自定义系统提示词
    temperature: float = 0.7               # 温度参数
    max_tokens: int = 2048                 # 最大token数

class EnhancedChatResponse(BaseModel):
    response: str                          # AI回复
    data_sources: List[str]                # 使用的数据源
    rag_context: List[str] = []           # RAG检索的上下文
    realtime_data: Dict = {}               # 实时数据
    confidence: float                      # 回复置信度
    model_used: str                        # 使用的模型

# === 股票查询集成接口 ===
class StockQueryRequest(BaseModel):
    query: str                             # 股票查询 (代码/名称)
    analysis_type: List[str] = ["basic"]   # ["basic", "technical", "fundamental"]
    include_news: bool = True              # 包含相关新闻

class StockQueryResponse(BaseModel):
    stock_info: Dict                       # 基础股票信息
    analysis_data: Dict = {}               # 分析数据
    related_news: List[Dict] = []          # 相关新闻
    ai_summary: str                        # AI生成的总结

# === 模型管理接口 ===
class ModelSwitchRequest(BaseModel):
    model_name: str                        # "qwen2.5:7b" | "deepseek-coder:1.3b"
    force_reload: bool = False             # 是否强制重新加载

class ChatRequest(BaseModel):
    message: str                           # 用户消息
    model: str                             # 使用的模型
    system_prompt: str                     # 系统提示词
    temperature: float = 0.7               # 温度参数
    max_tokens: int = 2048                 # 最大token数
```

### WebUI核心功能端点
```python
# === RAG增强对话 (主要功能) ===
POST /api/chat/enhanced                   # RAG增强对话
POST /api/chat/stock-analysis            # 股票分析对话
POST /api/chat/news-summary              # 新闻总结对话

# === 外部服务集成端点 ===
GET  /api/integration/stock/{code}        # 获取股票信息
GET  /api/integration/news/latest        # 获取最新新闻
POST /api/integration/rag/search         # RAG语义搜索

# === 传统模型管理 ===
GET  /api/models                          # 获取模型列表
POST /api/models/switch                   # 切换模型
POST /api/models/pull                     # 下载模型
DELETE /api/models/{model_name}           # 删除模型

# === 对话管理 ===
GET  /api/chats                           # 获取对话列表
POST /api/chats                           # 创建新对话
GET  /api/chats/{chat_id}                 # 获取对话详情
DELETE /api/chats/{chat_id}               # 删除对话

# === 消息生成 ===
POST /api/generate                        # 生成回复
POST /api/chat/completions                # 兼容OpenAI格式

# === 用户管理 ===
POST /auth/signin                         # 用户登录
POST /auth/signup                         # 用户注册
GET  /api/users/profile                   # 获取用户信息
POST /api/settings                        # 保存设置
```

### 外部服务集成配置
```python
# === 外部服务URL配置 ===
EXTERNAL_SERVICES = {
    "stock_service": "http://host.docker.internal:8000",
    "rag_service": "http://host.docker.internal:8001",
    "auth_service": "http://host.docker.internal:8004",
    "news_service": "http://host.docker.internal:8005",
    "ollama_service": "http://host.docker.internal:11434"
}

# === API集成配置 ===
class ExternalAPIConfig:
    # Stock Service集成
    STOCK_SEARCH_ENDPOINT = "/api/stock/search"
    STOCK_REALTIME_ENDPOINT = "/api/stock/{code}/realtime"
    STOCK_ANALYSIS_ENDPOINT = "/api/stock/analysis"

    # RAG Service集成
    RAG_SEARCH_ENDPOINT = "/api/rag/search"
    RAG_CONTEXT_ENDPOINT = "/api/rag/context"

    # News Service集成
    NEWS_LATEST_ENDPOINT = "/api/news/feed"
    NEWS_SEARCH_ENDPOINT = "/api/news/search"

    # Authentication集成
    AUTH_CHECK_ENDPOINT = "/api/auth/check-permission"
    USER_PROFILE_ENDPOINT = "/api/auth/profile"
```

---

## 🧠 RAG增强对话核心逻辑

### 增强对话处理流程
```python
"""
Open WebUI RAG增强对话核心实现逻辑
"""

class EnhancedChatHandler:
    def __init__(self):
        self.stock_service_client = HTTPClient(EXTERNAL_SERVICES["stock_service"])
        self.rag_service_client = HTTPClient(EXTERNAL_SERVICES["rag_service"])
        self.news_service_client = HTTPClient(EXTERNAL_SERVICES["news_service"])
        self.ollama_client = OllamaClient(EXTERNAL_SERVICES["ollama_service"])

    async def process_enhanced_chat(self, request: EnhancedChatRequest) -> EnhancedChatResponse:
        """
        RAG增强对话处理主流程:
        1. 分析用户消息，识别股票相关内容
        2. 如果涉及股票，获取实时数据
        3. 使用RAG检索相关背景信息
        4. 获取相关新闻信息
        5. 构建增强上下文
        6. 生成AI回复
        """

        # Step 1: 消息分析和股票识别
        stock_codes = self._extract_stock_codes(request.message)

        # Step 2: 并行获取实时数据
        realtime_data = {}
        if stock_codes and request.enable_realtime:
            realtime_data = await self._fetch_realtime_data(stock_codes)

        # Step 3: RAG背景信息检索
        rag_context = []
        if request.enable_rag:
            rag_context = await self._fetch_rag_context(request.message, stock_codes)

        # Step 4: 相关新闻获取
        related_news = []
        if stock_codes:
            related_news = await self._fetch_related_news(stock_codes)

        # Step 5: 构建增强Prompt
        enhanced_prompt = self._build_enhanced_prompt(
            user_message=request.message,
            realtime_data=realtime_data,
            rag_context=rag_context,
            related_news=related_news,
            system_prompt=request.system_prompt
        )

        # Step 6: AI推理生成回复
        ai_response = await self._generate_ai_response(
            prompt=enhanced_prompt,
            model=request.model,
            temperature=request.temperature,
            max_tokens=request.max_tokens
        )

        # Step 7: 构建增强响应
        return EnhancedChatResponse(
            response=ai_response.generated_text,
            data_sources=self._identify_data_sources(realtime_data, rag_context, related_news),
            rag_context=[doc.content for doc in rag_context],
            realtime_data=realtime_data,
            confidence=ai_response.confidence_score,
            model_used=ai_response.model_used
        )

    def _extract_stock_codes(self, message: str) -> List[str]:
        """从用户消息中提取股票代码"""
        # 股票代码识别逻辑: 正则匹配 + NLP识别
        import re
        codes = []

        # 匹配6位数字股票代码
        code_patterns = re.findall(r'\b\d{6}\b', message)
        codes.extend(code_patterns)

        # TODO: 添加股票名称到代码的映射逻辑
        return codes

    async def _fetch_realtime_data(self, stock_codes: List[str]) -> Dict:
        """获取股票实时数据"""
        realtime_data = {}

        for code in stock_codes:
            try:
                # 调用Stock Service获取实时数据
                response = await self.stock_service_client.get(
                    f"/api/stock/{code}/realtime"
                )
                if response.status_code == 200:
                    realtime_data[code] = response.json()
            except Exception as e:
                print(f"获取股票{code}实时数据失败: {e}")

        return realtime_data

    async def _fetch_rag_context(self, message: str, stock_codes: List[str]) -> List[Dict]:
        """RAG上下文检索"""
        try:
            # 构建RAG搜索请求
            search_query = message
            if stock_codes:
                # 如果有股票代码，构建更精确的搜索查询
                search_query = f"{message} {' '.join(stock_codes)}"

            # 调用RAG Service进行语义搜索
            response = await self.rag_service_client.post(
                "/api/rag/search",
                json={
                    "query": search_query,
                    "stock_codes": stock_codes,
                    "limit": 5,
                    "search_type": "semantic"
                }
            )

            if response.status_code == 200:
                return response.json().get("results", [])

        except Exception as e:
            print(f"RAG上下文检索失败: {e}")

        return []

    async def _fetch_related_news(self, stock_codes: List[str]) -> List[Dict]:
        """获取相关新闻"""
        try:
            # 调用News Service获取相关新闻
            response = await self.news_service_client.get(
                "/api/news/feed",
                params={
                    "stock_codes": ",".join(stock_codes),
                    "limit": 3,
                    "sort": "publish_time"
                }
            )

            if response.status_code == 200:
                return response.json().get("items", [])

        except Exception as e:
            print(f"获取相关新闻失败: {e}")

        return []

    def _build_enhanced_prompt(self, user_message: str, realtime_data: Dict,
                             rag_context: List[Dict], related_news: List[Dict],
                             system_prompt: str = None) -> str:
        """构建RAG增强的Prompt"""

        # 基础系统Prompt
        base_system = system_prompt or """
你是一位专业的金融分析师和投资顾问，具有丰富的股票分析经验。
请基于提供的实时数据、背景信息和相关新闻，给出专业、客观的分析建议。
"""

        # 构建增强上下文
        enhanced_context = []

        # 添加实时数据
        if realtime_data:
            enhanced_context.append("=== 实时股票数据 ===")
            for code, data in realtime_data.items():
                enhanced_context.append(f"股票 {code}:")
                enhanced_context.append(f"- 当前价格: {data.get('current_price', 'N/A')}")
                enhanced_context.append(f"- 涨跌幅: {data.get('change_percent', 'N/A')}%")
                enhanced_context.append(f"- 成交量: {data.get('volume', 'N/A')}")

        # 添加RAG检索的背景信息
        if rag_context:
            enhanced_context.append("\n=== 相关背景信息 ===")
            for i, doc in enumerate(rag_context[:3], 1):
                enhanced_context.append(f"{i}. {doc.get('content', '')[:200]}...")

        # 添加相关新闻
        if related_news:
            enhanced_context.append("\n=== 相关新闻 ===")
            for i, news in enumerate(related_news, 1):
                enhanced_context.append(f"{i}. {news.get('title', '')}")
                enhanced_context.append(f"   {news.get('summary', '')[:150]}...")

        # 构建完整Prompt
        full_prompt = f"""{base_system}

{chr(10).join(enhanced_context)}

=== 用户问题 ===
{user_message}

请基于以上信息提供专业分析:
"""

        return full_prompt

    async def _generate_ai_response(self, prompt: str, model: str,
                                  temperature: float, max_tokens: int) -> Dict:
        """调用AI模型生成回复"""
        try:
            response = await self.ollama_client.post(
                "/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens
                    }
                }
            )

            if response.status_code == 200:
                result = response.json()
                return {
                    "generated_text": result.get("response", ""),
                    "model_used": model,
                    "confidence_score": 0.85  # TODO: 实际置信度计算
                }

        except Exception as e:
            print(f"AI回复生成失败: {e}")

        return {
            "generated_text": "抱歉，当前无法生成回复，请稍后再试。",
            "model_used": model,
            "confidence_score": 0.0
        }

    def _identify_data_sources(self, realtime_data: Dict, rag_context: List[Dict],
                              related_news: List[Dict]) -> List[str]:
        """识别使用的数据源"""
        sources = []

        if realtime_data:
            sources.append("实时股票数据")
        if rag_context:
            sources.append("历史分析报告")
        if related_news:
            sources.append("相关新闻资讯")

        return sources

# 使用示例
async def handle_enhanced_chat(request: EnhancedChatRequest):
    handler = EnhancedChatHandler()
    return await handler.process_enhanced_chat(request)
```

### 专业金融对话模板
```python
class FinancialChatTemplates:
    """金融专业对话模板库"""

    STOCK_ANALYSIS_TEMPLATE = """
你是一位资深的股票分析师。用户询问关于 {stock_codes} 的投资建议。

实时数据显示:
{realtime_data_summary}

相关背景信息:
{rag_context_summary}

最新相关新闻:
{news_summary}

请从以下角度进行分析:
1. 技术面分析 (价格走势、技术指标)
2. 基本面评估 (财务状况、业务表现)
3. 消息面影响 (政策、新闻对股价的影响)
4. 风险提示和投资建议

用户问题: {user_message}
"""

    MARKET_OVERVIEW_TEMPLATE = """
你是市场分析专家。请基于当前市场数据和新闻信息，提供市场整体走势分析。

当前市场数据:
{market_data}

重要新闻事件:
{important_news}

请分析:
1. 市场整体趋势
2. 主要影响因素
3. 投资机会和风险
4. 后市预期

用户问题: {user_message}
"""

    RISK_ASSESSMENT_TEMPLATE = """
你是风险管理专家。请对用户的投资问题进行风险评估。

相关数据:
{risk_data}

请评估:
1. 市场风险
2. 个股风险
3. 流动性风险
4. 风险控制建议

用户问题: {user_message}
"""
```

---

## 🚀 部署和运维脚本

### 模型下载脚本 (customizations/models/model_downloader.py)
```python
#!/usr/bin/env python3
"""
Prism2 模型下载和管理脚本
"""
import requests
import json
import subprocess
import time
from pathlib import Path

class OllamaModelManager:
    def __init__(self, ollama_url="http://localhost:11434"):
        self.ollama_url = ollama_url
        self.required_models = [
            "qwen2.5:7b",
            "deepseek-coder:1.3b",
            "bge-large-zh-v1.5"
        ]

    def pull_model(self, model_name):
        """下载指定模型"""
        print(f"正在下载模型: {model_name}")
        try:
            result = subprocess.run([
                "ollama", "pull", model_name
            ], capture_output=True, text=True, timeout=3600)

            if result.returncode == 0:
                print(f"✅ 模型 {model_name} 下载成功")
                return True
            else:
                print(f"❌ 模型 {model_name} 下载失败: {result.stderr}")
                return False
        except subprocess.TimeoutExpired:
            print(f"⏰ 模型 {model_name} 下载超时")
            return False

    def check_model_status(self, model_name):
        """检查模型状态"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                for model in models:
                    if model.get("name") == model_name:
                        return True
            return False
        except:
            return False

    def setup_all_models(self):
        """设置所有必需的模型"""
        print("🚀 开始设置Prism2所需的AI模型...")

        for model in self.required_models:
            if not self.check_model_status(model):
                self.pull_model(model)
            else:
                print(f"✅ 模型 {model} 已存在")

        print("🎉 模型设置完成!")

if __name__ == "__main__":
    manager = OllamaModelManager()
    manager.setup_all_models()
```

### 健康检查脚本 (scripts/health_check.sh)
```bash
#!/bin/bash
# Open WebUI 健康检查脚本

set -e

WEBUI_URL="http://localhost:3001"
OLLAMA_URL="http://localhost:11434"
LOG_FILE="/var/log/prism2/webui-health.log"

# 创建日志目录
mkdir -p "$(dirname "$LOG_FILE")"

# 日志函数
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# 检查Open WebUI状态
check_webui() {
    log "检查Open WebUI状态..."

    if curl -f -s -o /dev/null "$WEBUI_URL/health"; then
        log "✅ Open WebUI 运行正常"
        return 0
    else
        log "❌ Open WebUI 无响应"
        return 1
    fi
}

# 检查Ollama连接
check_ollama() {
    log "检查Ollama连接..."

    if curl -f -s -o /dev/null "$OLLAMA_URL/api/tags"; then
        log "✅ Ollama 连接正常"
        return 0
    else
        log "❌ Ollama 连接失败"
        return 1
    fi
}

# 检查模型状态
check_models() {
    log "检查模型状态..."

    local models=("qwen2.5:7b" "deepseek-coder:1.3b")
    local all_loaded=true

    for model in "${models[@]}"; do
        if curl -s "$OLLAMA_URL/api/tags" | jq -e ".models[] | select(.name == \"$model\")" > /dev/null; then
            log "✅ 模型 $model 已加载"
        else
            log "⚠️ 模型 $model 未加载"
            all_loaded=false
        fi
    done

    if $all_loaded; then
        return 0
    else
        return 1
    fi
}

# 主检查流程
main() {
    log "开始Open WebUI健康检查..."

    local exit_code=0

    if ! check_webui; then
        exit_code=1
    fi

    if ! check_ollama; then
        exit_code=1
    fi

    if ! check_models; then
        exit_code=1
    fi

    if [ $exit_code -eq 0 ]; then
        log "🎉 所有服务运行正常"
    else
        log "⚠️ 发现服务异常，请检查日志"
    fi

    return $exit_code
}

# 执行检查
main "$@"
```

---

## 🔒 环境配置

### 环境变量 (.env)
```bash
# Open WebUI配置
WEBUI_SECRET_KEY=your-super-secret-webui-key
WEBUI_NAME=Prism2 AI Lab
WEBUI_URL=http://localhost:3001

# 认证配置
ENABLE_SIGNUP=false
DEFAULT_USER_ROLE=user
ADMIN_EMAIL=admin@prism2.local
ADMIN_PASSWORD=your-admin-password

# Ollama连接配置
OLLAMA_BASE_URL=http://host.docker.internal:11434
ENABLE_OLLAMA_API=true

# === 外部服务集成配置 ===
STOCK_SERVICE_URL=http://host.docker.internal:8000
RAG_SERVICE_URL=http://host.docker.internal:8001
AUTH_SERVICE_URL=http://host.docker.internal:8004
NEWS_SERVICE_URL=http://host.docker.internal:8005

# RAG增强功能配置
ENABLE_RAG_ENHANCED_CHAT=true
RAG_CONTEXT_LIMIT=5
ENABLE_REALTIME_DATA=true
ENABLE_NEWS_INTEGRATION=true

# 功能开关 (金融场景优化)
ENABLE_MODEL_FILTER=true
ENABLE_WEB_SEARCH=false
ENABLE_IMAGE_GENERATION=false
ENABLE_COMMUNITY_SHARING=false
ENABLE_STOCK_ANALYSIS_MODE=true
ENABLE_EXTERNAL_AUTH=true

# 存储配置
DATA_DIR=/app/backend/data
UPLOAD_DIR=/app/backend/data/uploads
MAX_FILE_SIZE=10MB

# 自定义配置
CUSTOM_THEME_PATH=/app/backend/data/themes
DEFAULT_PROMPT_TEMPLATE_PATH=/app/backend/data/prompts

# 性能配置
MAX_CONCURRENT_REQUESTS=5
REQUEST_TIMEOUT=300
MODEL_LOAD_TIMEOUT=600

# 安全配置
SESSION_DURATION=86400
CSRF_PROTECTION=true
RATE_LIMITING=true

# 日志配置
LOG_LEVEL=INFO
LOG_FILE=/var/log/prism2/webui.log
```

---

## 📊 监控和维护

### 关键性能指标
- **响应时间**: 页面加载和API响应时间
- **并发用户**: 同时在线用户数量
- **模型使用**: 各模型的使用频率和性能
- **错误率**: 系统错误和用户操作失败率

### 维护任务
```bash
# 定期任务 (crontab)
# 每小时执行健康检查
0 * * * * /home/wyatt/prism2/open-webui/scripts/health_check.sh

# 每天备份数据
0 2 * * * /home/wyatt/prism2/open-webui/scripts/backup.sh

# 每周清理日志
0 3 * * 0 find /var/log/prism2 -name "*.log" -mtime +7 -delete
```

---

*文档更新时间: 2025-09-16*
*严格遵循外部设计规范，确保接口一致性*