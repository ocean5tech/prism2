# Frontend Module - 内部设计文档

## 📋 基本信息

- **模块名称**: Frontend Module (前端展示模块)
- **技术栈**: React 18 + TypeScript + Vite + Tailwind CSS
- **部署端口**: 3000 (开发) / 80,443 (生产)
- **依据**: 外部设计文档规范

---

## 📁 文件结构和权限

```
/home/wyatt/prism2/frontend/
├── public/                              # 静态文件 (755)
│   ├── index.html                       # (644)
│   ├── manifest.json                    # PWA配置 (644)
│   └── icons/                           # PWA图标 (755)
├── src/                                 # 源代码 (755)
│   ├── components/                      # 组件 (644)
│   │   ├── common/SearchBox.tsx         # 智能搜索组件
│   │   ├── charts/KLineChart.tsx        # K线图表
│   │   ├── charts/RadarChart.tsx        # 六维雷达图
│   │   └── dashboard/                   # Dashboard组件集
│   ├── pages/                           # 页面组件 (644)
│   │   ├── HomePage.tsx                 # Google式主页
│   │   ├── DashboardPage.tsx            # 股票详情页
│   │   └── ChatPage.tsx                 # AI助手页面
│   ├── services/api.ts                  # API服务层 (644)
│   ├── types/                           # 类型定义 (644)
│   │   ├── stock.ts                     # 股票数据类型
│   │   └── external-design.ts           # 外部设计接口类型
│   ├── hooks/                           # 自定义Hook (644)
│   └── utils/                           # 工具函数 (644)
├── package.json                         # 项目配置 (644)
├── vite.config.ts                       # 构建配置 (644)
└── .env                                 # 环境变量 (600)
```

---

## 🔌 API接口调用 (严格按照外部设计)

### 基础配置
```typescript
// 服务端点配置 (来自外部设计)
const SERVICES = {
  STOCK_SERVICE: process.env.VITE_STOCK_SERVICE || 'http://localhost:8000',
  RAG_SERVICE: process.env.VITE_RAG_SERVICE || 'http://localhost:8001',
  AUTH_SERVICE: process.env.VITE_AUTH_SERVICE || 'http://localhost:8004',
  NEWS_SERVICE: process.env.VITE_NEWS_SERVICE || 'http://localhost:8005'
}
```

### API1: 股票搜索 (对接Stock Service)
- **URL**: `POST ${STOCK_SERVICE}/api/stock/search`
- **输入参数**: 严格按照外部设计的 `StockSearchRequest`
  ```typescript
  {
    query: string;
    query_type: 'code' | 'name' | 'pinyin' | 'concept' | 'industry';
    market_filter?: 'SH' | 'SZ' | 'HK' | 'US' | 'all';
    limit?: number;
    user_id?: string;
    session_id?: string;
  }
  ```
- **输出结果**: 外部设计的 `StockSearchResponse`
- **资源**: Stock Analysis Service (8000端口)
- **逻辑**: 发送搜索请求，接收股票列表，用于搜索框智能提示和结果展示

### API2: Dashboard完整数据 (对接Stock Service)
- **URL**: `POST ${STOCK_SERVICE}/api/stock/dashboard`
- **输入参数**: 外部设计的 `DashboardDataRequest`
  ```typescript
  {
    stock_code: string;
    data_types: Array<'realtime' | 'kline' | 'company_info' | 'financial' | 'announcements' | 'ai_analysis'>;
    kline_period?: '1d' | '1w' | '1M';
    kline_limit?: number;
    user_id?: string;
  }
  ```
- **输出结果**: 外部设计的完整Dashboard数据结构
- **资源**:
  - stocks表 (基础信息)
  - stock_prices表 (实时价格)
  - ohlcv_data表 (K线数据)
  - ai_analysis_results表 (AI分析)
- **逻辑**: 一次性获取Dashboard页面所需的全部数据，包括实时行情、K线图、公司信息、财务数据、AI分析等

### API3: AI聊天助手 (对接AI Service)
- **URL**: `POST ${AI_SERVICE}/api/ai/generate`
- **输入参数**: 外部设计的 `AIAssistantRequest`
  ```typescript
  {
    message: string;
    session_id: string;
    context?: {
      current_stock?: string;
      conversation_history?: Array<{role, content, timestamp}>;
      user_preferences?: {risk_tolerance, investment_horizon, focus_areas};
    };
    analysis_preferences?: {
      include_technical: boolean;
      include_fundamental: boolean;
      include_news: boolean;
      detail_level: 'brief' | 'detailed' | 'comprehensive';
    };
    user_id?: string;
  }
  ```
- **输出结果**: AI生成的回复和分析
- **资源**: Ollama服务 (11434端口)
- **逻辑**: 发送带上下文的用户消息，获取AI智能回复，支持股票分析和投资建议

### API4: 实时数据WebSocket (对接Stock Service)
- **URL**: `WebSocket ws://${STOCK_SERVICE}/ws/stock-data`
- **输入参数**: 外部设计的 `RealtimeSubscriptionRequest`
  ```typescript
  {
    subscription_type: 'stock_price';
    targets: {
      stock_codes: string[];
    };
    user_id: string;
    session_id: string;
  }
  ```
- **输出结果**: 实时价格更新推送
- **资源**: Redis实时数据缓存
- **逻辑**: 订阅指定股票的实时价格变动，自动更新Dashboard页面显示

### API5: 新闻监控配置 (对接News Service)
- **URL**: `POST ${NEWS_SERVICE}/api/news/keywords`
- **输入参数**: 外部设计的 `NewsMonitoringConfig`
- **资源**: News Service (8005端口)
- **逻辑**: 配置用户关注的股票和关键词，设置新闻推送规则

---

## 🗄️ 本地数据存储 (基于外部设计接口)

### LocalStorage数据结构
```typescript
// 存储外部设计中定义的用户偏好
interface StoredUserPreferences {
  // 对应外部设计的 UserPreferencesUpdate
  watchlist: string[];
  default_market: string;
  refresh_interval: number;
  chart_preferences: {
    default_period: string;
    default_indicators: string[];
    color_scheme: 'light' | 'dark' | 'auto';
  };
  notification_settings: {
    price_alerts: boolean;
    news_alerts: boolean;
    ai_insights: boolean;
    email_notifications: boolean;
  };
  ai_assistant_settings: {
    response_style: 'concise' | 'detailed' | 'educational';
    include_reasoning: boolean;
    focus_areas: string[];
  };
}

// 搜索历史
interface SearchHistory {
  searches: Array<{
    query: string;
    type: 'code' | 'name' | 'concept';
    timestamp: string;
    result_count: number;
  }>;
}
```

---

## 🔧 核心组件实现

### 1. HomePage组件
- **文件**: `src/pages/HomePage.tsx`
- **功能**: Google式极简股票搜索主页
- **输入**: 用户搜索输入 (股票代码/公司名/概念)
- **输出**: 页面跳转或搜索结果展示
- **资源**: SearchSuggestions接口数据
- **逻辑**: 接收用户输入，调用股票搜索API，如果只有1个结果直接跳转到Dashboard，多个结果显示选择列表，支持拼音搜索和概念搜索

### 2. DashboardPage组件
- **文件**: `src/pages/DashboardPage.tsx`
- **功能**: 股票详情仪表板 (完全按照外部设计的Dashboard描述)
- **输入**: URL参数股票代码
- **输出**: 完整的股票分析界面
- **资源**:
  - Dashboard API (获取全部数据)
  - WebSocket (实时价格更新)
- **逻辑**:
  1. 从URL获取股票代码
  2. 调用Dashboard API获取所有类型数据
  3. 渲染页面布局: 顶部股票信息条 + 左侧K线图(60%) + 右侧信息面板(40%) + 底部AI分析
  4. 建立WebSocket连接订阅实时价格
  5. 每5秒刷新价格，30秒刷新图表

### 3. AIAssistant组件 (智能助手界面)
- **文件**: `src/components/chat/AIAssistant.tsx`
- **功能**: 类ChatGPT的投资顾问对话
- **输入**: 用户文本消息
- **输出**: AI回复和相关分析
- **资源**: AI Service API
- **逻辑**:
  1. 维护对话历史上下文
  2. 发送消息时附带当前浏览的股票信息
  3. 显示AI推理过程透明化
  4. 支持一键跳转到相关股票Dashboard

### 4. KLineChart组件
- **文件**: `src/components/charts/KLineChart.tsx`
- **功能**: 专业K线图表 (支持多周期和技术指标)
- **输入**: 外部设计的 KLineData 接口数据
- **输出**: 交互式K线图表
- **资源**: Lightweight Charts库
- **逻辑**:
  1. 接收K线数据和技术指标数据
  2. 支持分时/日K/周K/月K切换
  3. 叠加MA、MACD、RSI、BOLL等指标
  4. 实时更新最新价格点

### 5. SixDimensionRadar组件 (六维雷达图)
- **文件**: `src/components/charts/SixDimensionRadar.tsx`
- **功能**: AI综合评价六维雷达图
- **输入**: 外部设计的 AIComprehensiveAnalysis.six_dimension_scores
- **输出**: 雷达图展示
- **逻辑**:
  1. 接收六个维度评分 (技术面、基本面、消息面、概念热度、市场趋势、资金关注度)
  2. 渲染雷达图，每个维度0-100分
  3. 支持点击查看具体分析详情

---

## 🌐 状态管理 (基于外部设计数据结构)

### 全局状态定义
```typescript
interface AppState {
  // 当前股票状态
  currentStock: string | null;
  currentStockData: StockRealtimeData | null;

  // 自选股管理
  watchlist: string[];

  // 实时数据缓存
  realtimeDataCache: Record<string, StockRealtimeData>;

  // AI分析缓存
  aiAnalysisCache: Record<string, AIComprehensiveAnalysis>;

  // WebSocket连接状态
  websocketConnected: boolean;

  // Actions
  setCurrentStock: (code: string) => void;
  updateRealtimeData: (code: string, data: StockRealtimeData) => void;
  cacheAIAnalysis: (code: string, analysis: AIComprehensiveAnalysis) => void;
}
```

---

## 📱 PWA配置

### Manifest配置
```json
{
  "name": "Prism2 股票分析平台",
  "short_name": "Prism2",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#3b82f6",
  "icons": [
    {
      "src": "/icons/icon-192x192.png",
      "sizes": "192x192",
      "type": "image/png"
    }
  ]
}
```

### Service Worker策略
- **静态资源**: 缓存优先策略
- **API数据**: 网络优先，失败时使用缓存
- **实时数据**: 仅网络，不缓存

---

## ⚡ 性能优化策略

### 代码分割
- 页面级分割: HomePage、DashboardPage、ChatPage独立加载
- 库分割: React、图表库、工具库分离打包
- 按需加载: 路由懒加载和组件懒加载

### 数据缓存
- 股票基础信息: 缓存1小时
- 实时价格: 缓存5秒
- AI分析结果: 缓存1小时
- 搜索结果: 缓存5分钟

---

## 🔒 环境配置

### 环境变量 (.env)
```bash
# 服务端点 (对应外部设计的端口分配)
VITE_STOCK_SERVICE=http://localhost:8000
VITE_RAG_SERVICE=http://localhost:8001
VITE_AUTH_SERVICE=http://localhost:8004
VITE_NEWS_SERVICE=http://localhost:8005
VITE_AI_SERVICE=http://localhost:11434

# WebSocket配置
VITE_WS_STOCK=ws://localhost:8000/ws/stock-data
VITE_WS_NEWS=ws://localhost:8005/ws/news-alerts

# 应用配置
VITE_APP_NAME=Prism2
VITE_APP_VERSION=1.0.0
```

### Vite构建配置
```typescript
// vite.config.ts - 代理配置对应外部设计的服务端口
export default defineConfig({
  server: {
    port: 3000,
    proxy: {
      '/api/stock': 'http://localhost:8000',
      '/api/rag': 'http://localhost:8001',
      '/api/auth': 'http://localhost:8004',
      '/api/news': 'http://localhost:8005',
      '/api/ai': 'http://localhost:11434'
    }
  }
})
```

---

## 📊 数据流设计

### 页面数据流
1. **HomePage → 搜索** → Stock Service搜索API → 结果展示/跳转
2. **DashboardPage → 加载** → Stock Service批量数据API → 页面渲染 → WebSocket实时更新
3. **ChatPage → 对话** → AI Service生成API → 回复展示 → 相关股票跳转

### 缓存数据流
1. **API请求** → 检查缓存 → 缓存命中返回/缓存未命中请求API → 更新缓存 → 返回数据
2. **WebSocket更新** → 更新缓存 → 通知组件重新渲染

---

*文档更新时间: 2025-09-16*
*严格遵循外部设计规范，确保接口一致性*