# AI Service - 内部设计文档

## 📋 基本信息

- **模块名称**: AI Service (AI模型服务)
- **技术栈**: Ollama + Qwen2.5-7B + FastAPI + API封装
- **部署端口**: 11434
- **依据**: 外部设计文档规范

---

## 📁 文件结构和权限

```
/home/wyatt/prism2/ai-service/
├── ollama/                               # Ollama服务目录 (755)
│   ├── docker-compose.yml               # Ollama Docker配置 (644)
│   ├── .env                             # Ollama环境变量 (600)
│   └── models/                          # 模型存储目录 (755)
│       ├── qwen2.5-7b/                  # Qwen2.5-7B模型 (755)
│       ├── deepseek-coder-1.3b/         # DeepSeek Coder模型 (755)
│       └── bge-large-zh-v1.5/           # 中文向量模型 (755)
├── api_wrapper/                         # API封装层 (755)
│   ├── __init__.py                      # (644)
│   ├── main.py                          # FastAPI应用入口 (644)
│   ├── core/                            # 核心配置 (755)
│   │   ├── __init__.py                  # (644)
│   │   ├── config.py                    # 配置管理 (644)
│   │   └── dependencies.py              # 依赖注入 (644)
│   ├── api/                             # API路由 (755)
│   │   ├── __init__.py                  # (644)
│   │   └── v1/                          # API版本1 (755)
│   │       ├── __init__.py              # (644)
│   │       ├── generate.py              # 文本生成端点 (644)
│   │       ├── embed.py                 # 向量嵌入端点 (644)
│   │       ├── models.py                # 模型管理端点 (644)
│   │       └── health.py                # 健康检查端点 (644)
│   ├── services/                        # 业务服务层 (755)
│   │   ├── __init__.py                  # (644)
│   │   ├── ollama_client.py             # Ollama客户端 (644)
│   │   ├── generation_service.py        # 文本生成服务 (644)
│   │   ├── embedding_service.py         # 向量嵌入服务 (644)
│   │   ├── model_manager.py             # 模型管理服务 (644)
│   │   └── cache_service.py             # 缓存服务 (644)
│   ├── models/                          # 数据模型 (755)
│   │   ├── __init__.py                  # (644)
│   │   ├── requests.py                  # 请求模型 (644)
│   │   └── responses.py                 # 响应模型 (644)
│   ├── middleware/                      # 中间件 (755)
│   │   ├── __init__.py                  # (644)
│   │   ├── rate_limit.py                # 限流中间件 (644)
│   │   └── logging.py                   # 日志中间件 (644)
│   └── utils/                           # 工具函数 (755)
│       ├── __init__.py                  # (644)
│       ├── text_processor.py            # 文本处理工具 (644)
│       ├── performance_monitor.py       # 性能监控 (644)
│       └── prompt_templates.py          # 提示词模板 (644)
├── scripts/                             # 运维脚本 (755)
│   ├── install_models.sh                # 模型安装脚本 (755)
│   ├── start_services.sh                # 服务启动脚本 (755)
│   ├── health_check.sh                  # 健康检查脚本 (755)
│   └── benchmark.py                     # 性能基准测试 (755)
├── requirements.txt                     # Python依赖 (644)
└── README.md                            # 部署说明 (644)
```

---

## 🤖 Ollama服务配置

### Docker Compose配置 (ollama/docker-compose.yml)
```yaml
version: '3.8'

services:
  ollama:
    image: ollama/ollama:latest
    container_name: prism2-ollama
    restart: unless-stopped
    ports:
      - "11434:11434"
    environment:
      # GPU配置 (如果有GPU)
      - NVIDIA_VISIBLE_DEVICES=all
      - NVIDIA_DRIVER_CAPABILITIES=compute,utility

      # Ollama配置
      - OLLAMA_HOST=0.0.0.0
      - OLLAMA_ORIGINS=*
      - OLLAMA_MAX_LOADED_MODELS=2
      - OLLAMA_NUM_PARALLEL=4
      - OLLAMA_MAX_QUEUE=10

      # 模型配置
      - OLLAMA_MODELS=/root/.ollama/models
      - OLLAMA_KEEP_ALIVE=24h

    volumes:
      # 模型持久化存储
      - ./models:/root/.ollama/models
      - ./logs:/var/log/ollama

    deploy:
      resources:
        limits:
          memory: 8G
        reservations:
          memory: 4G

    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:11434/api/tags"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s

    networks:
      - prism2-network

    # GPU支持 (如果有NVIDIA GPU)
    runtime: nvidia

networks:
  prism2-network:
    external: true
    name: prism2_default
```

### Ollama环境配置 (ollama/.env)
```bash
# Ollama服务配置
OLLAMA_HOST=0.0.0.0
OLLAMA_PORT=11434
OLLAMA_ORIGINS=*

# 性能配置
OLLAMA_MAX_LOADED_MODELS=2
OLLAMA_NUM_PARALLEL=4
OLLAMA_MAX_QUEUE=10
OLLAMA_KEEP_ALIVE=24h

# 模型存储
OLLAMA_MODELS=/root/.ollama/models

# GPU配置 (如果有GPU)
CUDA_VISIBLE_DEVICES=0
NVIDIA_VISIBLE_DEVICES=all

# 日志配置
OLLAMA_LOG_LEVEL=INFO
```

---

## 🔌 API接口定义 (严格按照外部设计)

### 基础配置
```python
# API封装服务配置
API_SERVICE_PORT = int(os.getenv('API_SERVICE_PORT', '11435'))
OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
MAX_CONCURRENT_REQUESTS = int(os.getenv('MAX_CONCURRENT_REQUESTS', '5'))
REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '300'))
```

### API1: 文本生成 (对接外部设计接口)
- **URL**: `POST /api/ai/generate`
- **输入参数**: 严格按照外部设计的AI生成请求
  ```python
  class AIGenerateRequest(BaseModel):
      prompt: str                          # 用户提示词
      context: Optional[str] = None        # 背景上下文信息
      model: str = "qwen2.5:7b"           # 使用的模型
      max_tokens: int = 1000              # 最大token数
      temperature: float = 0.7            # 温度参数 0-1
      top_p: float = 0.9                  # Top-p采样
      top_k: int = 40                     # Top-k采样
      system_prompt: Optional[str] = None  # 系统提示词
      stream: bool = False                 # 是否流式返回
  ```
- **输出结果**: 外部设计的AIGenerateResponse
  ```python
  class AIGenerateResponse(BaseModel):
      generated_text: str                  # 生成的文本
      model_used: str                      # 使用的模型
      tokens_used: int                     # 消耗的token数
      generation_time: float               # 生成时间(秒)
      confidence_score: float              # 置信度评分 0-1
      finish_reason: str                   # 完成原因: stop/length/error
      metadata: Dict[str, Any]             # 扩展元数据
  ```
- **资源**: Ollama服务、模型推理引擎
- **逻辑**: 接收生成请求，验证参数有效性，调用Ollama API执行推理，监控生成过程，计算性能指标，返回生成结果和统计信息

### API2: 文本向量嵌入 (对接RAG Service)
- **URL**: `POST /api/ai/embed`
- **输入参数**: 外部设计的向量嵌入请求
  ```python
  class EmbeddingRequest(BaseModel):
      text: Union[str, List[str]]          # 待嵌入的文本(支持批量)
      model: str = "bge-large-zh-v1.5"    # 向量模型
      normalize: bool = True               # 是否标准化向量
      encoding_format: str = "float"       # 编码格式: float/base64
  ```
- **输出结果**: 外部设计的EmbeddingResponse
  ```python
  class EmbeddingResponse(BaseModel):
      embedding: Union[List[float], List[List[float]]]  # 向量数据
      model_used: str                      # 使用的模型
      text_length: int                     # 文本长度
      embedding_time: float                # 嵌入时间(秒)
      dimension: int                       # 向量维度
      token_count: int                     # token数量
  ```
- **资源**: bge-large-zh-v1.5向量模型、向量计算引擎
- **逻辑**: 接收文本嵌入请求，支持单个和批量文本处理，调用中文向量模型生成embedding，执行向量标准化，返回向量数据和性能统计

### API3: 模型管理 (对接Open WebUI)
- **URL**: `GET /api/ai/models`
- **输入参数**: 模型查询请求
  ```python
  class ModelListRequest(BaseModel):
      include_details: bool = False        # 是否包含详细信息
      filter_loaded: Optional[bool] = None # 过滤已加载的模型
  ```
- **输出结果**: 模型信息列表
  ```python
  class ModelInfo(BaseModel):
      name: str                           # 模型名称
      size: str                           # 模型大小
      modified_at: datetime               # 修改时间
      digest: str                         # 模型摘要
      status: str                         # 状态: "loaded" | "unloaded"
      parameters: Dict[str, Any]          # 模型参数
      capabilities: List[str]             # 模型能力

  class ModelListResponse(BaseModel):
      models: List[ModelInfo]
      total_count: int
      loaded_count: int
      available_memory: str
  ```
- **资源**: Ollama模型管理、系统资源监控
- **逻辑**: 查询Ollama中的模型列表，获取模型状态和元数据，检查系统资源使用情况，返回完整的模型信息和状态

### API4: 模型加载/卸载
- **URL**: `POST /api/ai/models/{model_name}/load`
- **URL**: `POST /api/ai/models/{model_name}/unload`
- **输入参数**: 模型操作请求
  ```python
  class ModelOperationRequest(BaseModel):
      force: bool = False                 # 是否强制操作
      timeout: int = 300                  # 操作超时时间
  ```
- **输出结果**: 操作结果
  ```python
  class ModelOperationResponse(BaseModel):
      success: bool                       # 操作是否成功
      model_name: str                     # 模型名称
      operation: str                      # 操作类型
      execution_time: float               # 执行时间
      memory_usage: str                   # 内存使用情况
      message: str                        # 状态消息
  ```
- **资源**: Ollama模型管理、内存监控
- **逻辑**: 执行模型的加载或卸载操作，监控内存使用情况，处理操作超时和错误，返回操作状态和资源信息

### API5: 流式文本生成 (支持实时推理)
- **URL**: `POST /api/ai/generate/stream`
- **输入参数**: 流式生成请求
  ```python
  class StreamGenerateRequest(BaseModel):
      prompt: str                         # 用户提示词
      model: str = "qwen2.5:7b"          # 使用的模型
      max_tokens: int = 1000             # 最大token数
      temperature: float = 0.7            # 温度参数
      system_prompt: Optional[str] = None # 系统提示词
  ```
- **输出结果**: 服务器端事件流 (SSE)
  ```python
  # SSE事件格式
  data: {
      "type": "token",
      "content": "生成的文本片段",
      "token_count": 10,
      "is_final": false
  }

  data: {
      "type": "final",
      "total_tokens": 150,
      "generation_time": 2.5,
      "finish_reason": "stop"
  }
  ```
- **资源**: Ollama流式API、WebSocket连接
- **逻辑**: 建立流式连接，逐token生成文本内容，实时推送生成进度，监控生成状态，在完成时发送最终统计信息

---

## 🔧 核心服务实现

### 1. OllamaClient (Ollama客户端)
- **文件**: `api_wrapper/services/ollama_client.py`
- **功能**: Ollama服务的统一客户端接口
- **输入**: API请求参数
- **输出**: Ollama响应数据
- **资源**: HTTP客户端、连接池
- **逻辑**: 管理与Ollama的HTTP连接，实现请求重试和错误处理，提供统一的API调用接口，处理并发请求和连接池管理

### 2. GenerationService (文本生成服务)
- **文件**: `api_wrapper/services/generation_service.py`
- **功能**: 智能文本生成和推理管理
- **输入**: 生成请求和参数
- **输出**: 生成文本和性能统计
- **资源**: Ollama推理引擎、提示词模板
- **逻辑**: 处理文本生成请求，优化提示词模板，管理生成参数，监控推理性能，实现缓存策略提高效率

### 3. EmbeddingService (向量嵌入服务)
- **文件**: `api_wrapper/services/embedding_service.py`
- **功能**: 文本向量化和嵌入管理
- **输入**: 文本内容和嵌入参数
- **输出**: 向量数据和处理统计
- **逻辑**: 调用向量模型生成文本嵌入，支持批量处理提高效率，实现向量缓存减少重复计算，提供向量标准化和格式转换

### 4. ModelManager (模型管理服务)
- **文件**: `api_wrapper/services/model_manager.py`
- **功能**: AI模型生命周期管理
- **输入**: 模型操作请求
- **输出**: 模型状态和资源信息
- **逻辑**: 管理模型的加载、卸载和切换，监控模型内存使用，实现智能模型调度，维护模型状态缓存

### 5. CacheService (缓存服务)
- **文件**: `api_wrapper/services/cache_service.py`
- **功能**: 智能缓存和性能优化
- **输入**: 请求参数和缓存策略
- **输出**: 缓存命中或原始结果
- **逻辑**: 实现多层级缓存策略，缓存常用的生成结果和向量数据，管理缓存过期和清理，提供缓存命中率统计

---

## 🚀 模型配置和优化

### 支持的AI模型配置
```python
# 模型配置字典
SUPPORTED_MODELS = {
    "qwen2.5:7b": {
        "type": "text_generation",
        "size": "7B",
        "context_length": 8192,
        "memory_requirement": "6GB",
        "optimal_batch_size": 1,
        "default_parameters": {
            "temperature": 0.7,
            "top_p": 0.9,
            "top_k": 40,
            "repeat_penalty": 1.1
        },
        "specialties": ["financial_analysis", "general_chat", "reasoning"],
        "languages": ["zh", "en"]
    },
    "deepseek-coder:1.3b": {
        "type": "code_generation",
        "size": "1.3B",
        "context_length": 4096,
        "memory_requirement": "2GB",
        "optimal_batch_size": 2,
        "default_parameters": {
            "temperature": 0.3,
            "top_p": 0.8,
            "top_k": 20
        },
        "specialties": ["code_generation", "programming", "algorithms"],
        "languages": ["python", "javascript", "sql"]
    },
    "bge-large-zh-v1.5": {
        "type": "text_embedding",
        "size": "335M",
        "embedding_dimension": 1024,
        "memory_requirement": "1GB",
        "optimal_batch_size": 8,
        "specialties": ["chinese_embedding", "semantic_search"],
        "languages": ["zh"]
    }
}
```

### 性能优化配置
```python
# 推理优化配置
INFERENCE_CONFIG = {
    "batch_processing": {
        "enabled": True,
        "max_batch_size": 4,
        "batch_timeout": 100  # ms
    },
    "caching": {
        "enabled": True,
        "ttl": 3600,  # 1 hour
        "max_cache_size": "1GB"
    },
    "model_switching": {
        "auto_unload": True,
        "idle_timeout": 1800,  # 30 minutes
        "memory_threshold": 0.8
    },
    "concurrent_requests": {
        "max_concurrent": 5,
        "queue_size": 20,
        "timeout": 300
    }
}
```

---

## 📊 性能监控和基准测试

### 性能基准测试脚本 (scripts/benchmark.py)
```python
#!/usr/bin/env python3
"""
AI Service 性能基准测试脚本
"""
import asyncio
import time
import statistics
import requests
import json
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any

class AIServiceBenchmark:
    def __init__(self, base_url="http://localhost:11434"):
        self.base_url = base_url
        self.results = {}

    async def test_text_generation(self, model="qwen2.5:7b", num_requests=10):
        """测试文本生成性能"""
        print(f"测试文本生成性能 ({model})...")

        test_prompts = [
            "分析平安银行的投资价值",
            "解释什么是股票市场",
            "描述技术分析的基本原理",
            "什么是财务报表分析"
        ]

        latencies = []
        token_rates = []

        for i in range(num_requests):
            prompt = test_prompts[i % len(test_prompts)]
            start_time = time.time()

            response = requests.post(f"{self.base_url}/api/ai/generate", json={
                "prompt": prompt,
                "model": model,
                "max_tokens": 500,
                "temperature": 0.7
            })

            end_time = time.time()
            latency = end_time - start_time

            if response.status_code == 200:
                data = response.json()
                tokens_used = data.get("tokens_used", 0)
                token_rate = tokens_used / latency if latency > 0 else 0

                latencies.append(latency)
                token_rates.append(token_rate)

                print(f"  请求 {i+1}: {latency:.2f}s, {token_rate:.1f} tokens/s")

        # 统计结果
        avg_latency = statistics.mean(latencies)
        avg_token_rate = statistics.mean(token_rates)
        p95_latency = statistics.quantiles(latencies, n=20)[18] if len(latencies) >= 20 else max(latencies)

        self.results[f"{model}_generation"] = {
            "avg_latency": avg_latency,
            "p95_latency": p95_latency,
            "avg_token_rate": avg_token_rate,
            "success_rate": len(latencies) / num_requests
        }

        print(f"  平均延迟: {avg_latency:.2f}s")
        print(f"  P95延迟: {p95_latency:.2f}s")
        print(f"  平均生成速度: {avg_token_rate:.1f} tokens/s")

    async def test_embedding_performance(self, num_requests=50):
        """测试向量嵌入性能"""
        print("测试向量嵌入性能...")

        test_texts = [
            "平安银行是中国主要的股份制商业银行之一",
            "技术分析是通过研究价格图表来预测市场走势的方法",
            "基本面分析关注公司的财务健康状况和内在价值",
            "投资组合管理需要考虑风险分散和资产配置"
        ]

        latencies = []

        for i in range(num_requests):
            text = test_texts[i % len(test_texts)]
            start_time = time.time()

            response = requests.post(f"{self.base_url}/api/ai/embed", json={
                "text": text,
                "model": "bge-large-zh-v1.5"
            })

            end_time = time.time()
            latency = end_time - start_time

            if response.status_code == 200:
                latencies.append(latency)
                print(f"  嵌入 {i+1}: {latency:.3f}s")

        # 统计结果
        avg_latency = statistics.mean(latencies)
        throughput = len(latencies) / sum(latencies)

        self.results["embedding"] = {
            "avg_latency": avg_latency,
            "throughput": throughput,
            "success_rate": len(latencies) / num_requests
        }

        print(f"  平均延迟: {avg_latency:.3f}s")
        print(f"  吞吐量: {throughput:.1f} req/s")

    async def test_concurrent_load(self, concurrent_users=5, requests_per_user=5):
        """测试并发负载性能"""
        print(f"测试并发负载 ({concurrent_users} 用户, 每用户 {requests_per_user} 请求)...")

        async def user_session(user_id):
            latencies = []
            for i in range(requests_per_user):
                start_time = time.time()

                response = requests.post(f"{self.base_url}/api/ai/generate", json={
                    "prompt": f"用户{user_id}的测试请求{i+1}",
                    "model": "qwen2.5:7b",
                    "max_tokens": 100
                })

                end_time = time.time()
                if response.status_code == 200:
                    latencies.append(end_time - start_time)

            return latencies

        # 执行并发测试
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = [executor.submit(asyncio.run, user_session(i)) for i in range(concurrent_users)]
            all_latencies = []
            for future in futures:
                all_latencies.extend(future.result())

        # 统计结果
        if all_latencies:
            avg_latency = statistics.mean(all_latencies)
            max_latency = max(all_latencies)
            throughput = len(all_latencies) / max(all_latencies)

            self.results["concurrent_load"] = {
                "avg_latency": avg_latency,
                "max_latency": max_latency,
                "throughput": throughput,
                "success_rate": len(all_latencies) / (concurrent_users * requests_per_user)
            }

            print(f"  平均延迟: {avg_latency:.2f}s")
            print(f"  最大延迟: {max_latency:.2f}s")
            print(f"  系统吞吐量: {throughput:.1f} req/s")

    def generate_report(self):
        """生成测试报告"""
        print("\n" + "="*50)
        print("AI Service 性能测试报告")
        print("="*50)

        for test_name, metrics in self.results.items():
            print(f"\n{test_name.upper()}:")
            for metric, value in metrics.items():
                if isinstance(value, float):
                    print(f"  {metric}: {value:.3f}")
                else:
                    print(f"  {metric}: {value}")

        # 保存报告到文件
        with open("benchmark_report.json", "w") as f:
            json.dump(self.results, f, indent=2, default=str)

        print(f"\n详细报告已保存到: benchmark_report.json")

async def main():
    benchmark = AIServiceBenchmark()

    # 执行各项测试
    await benchmark.test_text_generation("qwen2.5:7b", 10)
    await benchmark.test_embedding_performance(20)
    await benchmark.test_concurrent_load(3, 5)

    # 生成报告
    benchmark.generate_report()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 🔒 环境配置

### API封装服务环境变量 (api_wrapper/.env)
```bash
# API服务配置
API_SERVICE_PORT=11435
DEBUG=false

# Ollama连接配置
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_REQUEST_TIMEOUT=300
OLLAMA_MAX_RETRIES=3

# 性能配置
MAX_CONCURRENT_REQUESTS=5
REQUEST_QUEUE_SIZE=20
MODEL_LOAD_TIMEOUT=600

# 缓存配置
REDIS_URL=redis://localhost:6379/6
CACHE_TTL=3600
MAX_CACHE_SIZE=1048576000  # 1GB

# 限流配置
RATE_LIMIT_REQUESTS_PER_MINUTE=60
RATE_LIMIT_TOKENS_PER_DAY=50000

# 监控配置
ENABLE_METRICS=true
METRICS_PORT=9090
LOG_LEVEL=INFO

# 安全配置
API_KEY_REQUIRED=true
ALLOWED_HOSTS=["localhost", "127.0.0.1"]
CORS_ORIGINS=["http://localhost:3000", "http://localhost:3001"]
```

### 依赖配置 (requirements.txt)
```txt
fastapi==0.104.1
uvicorn==0.24.0
httpx==0.25.2
redis==5.0.1
pydantic==2.5.0
python-multipart==0.0.6
slowapi==0.1.9
prometheus-client==0.19.0
structlog==23.2.0
tenacity==8.2.3
```

---

## 📊 监控和告警

### 关键性能指标
- **推理延迟**: 文本生成和向量嵌入的响应时间
- **吞吐量**: 每秒处理的请求数量
- **模型利用率**: 各模型的使用频率和负载
- **内存使用**: 模型占用的内存和系统资源
- **错误率**: 推理失败和超时的比例

### 告警规则配置
```python
ALERT_RULES = {
    'high_latency': {
        'threshold': 10.0,              # 延迟超过10秒
        'action': 'slack+email'
    },
    'low_throughput': {
        'threshold': 0.5,               # 吞吐量低于0.5 req/s
        'action': 'slack'
    },
    'memory_usage': {
        'threshold': 0.9,               # 内存使用超过90%
        'action': 'email+restart'
    },
    'model_load_failure': {
        'threshold': 1,                 # 模型加载失败
        'action': 'email+slack'
    }
}
```

---

*文档更新时间: 2025-09-16*
*严格遵循外部设计规范，确保接口一致性*