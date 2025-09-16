# Authentication Service - 内部设计文档

## 📋 基本信息

- **模块名称**: Authentication Service (认证授权服务)
- **技术栈**: FastAPI + JWT + Redis + PostgreSQL
- **部署端口**: 8004
- **依据**: 外部设计文档规范

---

## 📁 文件结构和权限

```
/home/wyatt/prism2/auth-service/
├── app/                                  # 应用源代码 (755)
│   ├── __init__.py                       # (644)
│   ├── main.py                           # FastAPI应用入口 (644)
│   ├── core/                             # 核心配置 (755)
│   │   ├── __init__.py                   # (644)
│   │   ├── config.py                     # 环境配置 (644)
│   │   ├── security.py                   # 安全配置和JWT处理 (644)
│   │   └── dependencies.py               # 依赖注入 (644)
│   ├── api/                              # API路由 (755)
│   │   ├── __init__.py                   # (644)
│   │   └── v1/                           # API版本1 (755)
│   │       ├── __init__.py               # (644)
│   │       ├── auth.py                   # 认证相关端点 (644)
│   │       ├── users.py                  # 用户管理端点 (644)
│   │       ├── permissions.py            # 权限管理端点 (644)
│   │       └── health.py                 # 健康检查端点 (644)
│   ├── services/                         # 业务服务层 (755)
│   │   ├── __init__.py                   # (644)
│   │   ├── auth_service.py               # 认证服务 (644)
│   │   ├── user_service.py               # 用户管理服务 (644)
│   │   ├── permission_service.py         # 权限管理服务 (644)
│   │   ├── session_service.py            # 会话管理服务 (644)
│   │   └── security_service.py           # 安全防护服务 (644)
│   ├── models/                           # 数据模型 (755)
│   │   ├── __init__.py                   # (644)
│   │   ├── requests.py                   # 请求模型 (644)
│   │   ├── responses.py                  # 响应模型 (644)
│   │   └── database.py                   # 数据库模型 (644)
│   ├── middleware/                       # 中间件 (755)
│   │   ├── __init__.py                   # (644)
│   │   ├── rate_limit.py                 # 限流中间件 (644)
│   │   ├── cors.py                       # CORS中间件 (644)
│   │   └── security.py                   # 安全中间件 (644)
│   └── utils/                            # 工具函数 (755)
│       ├── __init__.py                   # (644)
│       ├── password.py                   # 密码处理工具 (644)
│       ├── jwt_handler.py                # JWT处理工具 (644)
│       └── validators.py                 # 数据验证工具 (644)
├── alembic/                              # 数据库迁移 (755)
│   ├── versions/                         # 迁移版本 (755)
│   ├── alembic.ini                       # Alembic配置 (644)
│   └── env.py                            # 迁移环境 (644)
├── requirements.txt                      # Python依赖 (644)
├── Dockerfile                           # 容器化配置 (644)
└── .env                                 # 环境变量 (600)
```

---

## 🗄️ 数据库表结构 (PostgreSQL)

### 用户表 (users)
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,     -- 用户邮箱(登录名)
    username VARCHAR(100) UNIQUE,           -- 用户名(可选)
    password_hash VARCHAR(255) NOT NULL,    -- 密码哈希
    full_name VARCHAR(200),                 -- 全名
    avatar_url TEXT,                        -- 头像URL
    plan VARCHAR(50) DEFAULT 'free',        -- 套餐: free/standard/professional/enterprise
    status VARCHAR(20) DEFAULT 'active',    -- 状态: active/inactive/suspended/banned
    email_verified BOOLEAN DEFAULT false,   -- 邮箱验证状态
    phone VARCHAR(20),                      -- 手机号码
    phone_verified BOOLEAN DEFAULT false,   -- 手机验证状态
    last_login_at TIMESTAMP,                -- 最后登录时间
    login_count INTEGER DEFAULT 0,          -- 登录次数
    failed_login_attempts INTEGER DEFAULT 0, -- 连续失败登录次数
    locked_until TIMESTAMP,                 -- 账户锁定到期时间
    preferences JSONB DEFAULT '{}',         -- 用户偏好设置
    metadata JSONB DEFAULT '{}',            -- 扩展元数据
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    -- 约束
    CONSTRAINT chk_plan CHECK (plan IN ('free', 'standard', 'professional', 'enterprise')),
    CONSTRAINT chk_status CHECK (status IN ('active', 'inactive', 'suspended', 'banned'))
);

-- 索引
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_status ON users(status);
CREATE INDEX idx_users_plan ON users(plan);
CREATE INDEX idx_users_last_login ON users(last_login_at);
```

### 用户会话表 (user_sessions)
```sql
CREATE TABLE user_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    session_token VARCHAR(255) UNIQUE NOT NULL, -- 会话令牌
    refresh_token VARCHAR(255) UNIQUE NOT NULL,  -- 刷新令牌
    device_info JSONB,                          -- 设备信息
    ip_address INET,                            -- IP地址
    user_agent TEXT,                            -- 浏览器信息
    location JSONB,                             -- 地理位置
    status VARCHAR(20) DEFAULT 'active',        -- 状态: active/expired/revoked
    expires_at TIMESTAMP NOT NULL,              -- 过期时间
    last_activity_at TIMESTAMP DEFAULT NOW(),   -- 最后活动时间
    created_at TIMESTAMP DEFAULT NOW(),

    -- 约束
    CONSTRAINT chk_session_status CHECK (status IN ('active', 'expired', 'revoked'))
);

-- 索引
CREATE INDEX idx_sessions_user_id ON user_sessions(user_id);
CREATE INDEX idx_sessions_token ON user_sessions(session_token);
CREATE INDEX idx_sessions_status ON user_sessions(status);
CREATE INDEX idx_sessions_expires_at ON user_sessions(expires_at);
```

### 权限定义表 (permissions)
```sql
CREATE TABLE permissions (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,       -- 权限名称
    description TEXT,                        -- 权限描述
    resource VARCHAR(100) NOT NULL,          -- 资源类型
    action VARCHAR(50) NOT NULL,             -- 操作类型
    conditions JSONB DEFAULT '{}',           -- 权限条件
    is_system BOOLEAN DEFAULT false,         -- 是否系统权限
    created_at TIMESTAMP DEFAULT NOW(),

    -- 约束
    UNIQUE(resource, action)
);

-- 预设权限数据
INSERT INTO permissions (name, description, resource, action, is_system) VALUES
('stock.search', '股票搜索权限', 'stock', 'search', true),
('stock.analysis', '股票分析权限', 'stock', 'analysis', true),
('ai.chat', 'AI聊天权限', 'ai', 'chat', true),
('data.export', '数据导出权限', 'data', 'export', false),
('user.manage', '用户管理权限', 'user', 'manage', false);
```

### 角色权限表 (role_permissions)
```sql
CREATE TABLE role_permissions (
    id SERIAL PRIMARY KEY,
    plan VARCHAR(50) NOT NULL,               -- 套餐类型
    permission_id INTEGER NOT NULL REFERENCES permissions(id),
    quota_limit INTEGER,                     -- 配额限制
    rate_limit INTEGER,                      -- 频率限制 (每分钟)
    created_at TIMESTAMP DEFAULT NOW(),

    -- 约束
    UNIQUE(plan, permission_id)
);

-- 预设角色权限数据
INSERT INTO role_permissions (plan, permission_id, quota_limit, rate_limit) VALUES
('free', 1, 10, 5),          -- 免费用户: 搜索10次/天, 5次/分钟
('free', 3, 5, 2),           -- 免费用户: AI聊天5次/天, 2次/分钟
('standard', 1, 100, 20),    -- 标准用户: 搜索100次/天, 20次/分钟
('standard', 2, 20, 5),      -- 标准用户: 分析20次/天
('standard', 3, 50, 10),     -- 标准用户: AI聊天50次/天
('professional', 1, -1, 50), -- 专业用户: 无限搜索, 50次/分钟
('professional', 2, -1, 20), -- 专业用户: 无限分析
('professional', 3, -1, 30), -- 专业用户: 无限AI聊天
('professional', 4, 10, 5);  -- 专业用户: 数据导出权限
```

### 用户配额使用表 (user_quota_usage)
```sql
CREATE TABLE user_quota_usage (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES permissions(id),
    usage_date DATE NOT NULL DEFAULT CURRENT_DATE,
    usage_count INTEGER DEFAULT 0,          -- 当日使用次数
    last_used_at TIMESTAMP DEFAULT NOW(),   -- 最后使用时间

    -- 约束
    UNIQUE(user_id, permission_id, usage_date)
);

-- 索引
CREATE INDEX idx_quota_usage_user_date ON user_quota_usage(user_id, usage_date);
CREATE INDEX idx_quota_usage_permission ON user_quota_usage(permission_id);
```

### 安全日志表 (security_logs)
```sql
CREATE TABLE security_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),      -- 用户ID (可为空)
    event_type VARCHAR(50) NOT NULL,        -- 事件类型
    event_action VARCHAR(100) NOT NULL,     -- 具体操作
    ip_address INET,                        -- IP地址
    user_agent TEXT,                        -- 浏览器信息
    request_data JSONB,                     -- 请求数据
    response_status INTEGER,                -- 响应状态码
    success BOOLEAN,                        -- 是否成功
    error_message TEXT,                     -- 错误信息
    metadata JSONB DEFAULT '{}',            -- 扩展数据
    created_at TIMESTAMP DEFAULT NOW(),

    -- 索引
    INDEX idx_security_logs_user_id (user_id),
    INDEX idx_security_logs_event_type (event_type),
    INDEX idx_security_logs_created_at (created_at),
    INDEX idx_security_logs_ip (ip_address)
);
```

---

## 🔌 API接口定义 (严格按照外部设计)

### 基础配置
```python
# JWT配置
JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'your-secret-key')
JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'HS256')
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv('ACCESS_TOKEN_EXPIRE_MINUTES', '30'))
REFRESH_TOKEN_EXPIRE_DAYS = int(os.getenv('REFRESH_TOKEN_EXPIRE_DAYS', '7'))

# 安全配置
MAX_LOGIN_ATTEMPTS = int(os.getenv('MAX_LOGIN_ATTEMPTS', '5'))
ACCOUNT_LOCKOUT_DURATION = int(os.getenv('ACCOUNT_LOCKOUT_DURATION', '1800'))  # 30分钟
PASSWORD_MIN_LENGTH = int(os.getenv('PASSWORD_MIN_LENGTH', '8'))
```

### API1: 用户注册 (对接外部设计接口)
- **URL**: `POST /api/auth/register`
- **输入参数**: 严格按照外部设计的用户注册请求
  ```python
  class UserRegisterRequest(BaseModel):
      email: EmailStr                       # 邮箱地址
      password: str                         # 密码 (最少8位)
      full_name: Optional[str] = None       # 全名
      plan: str = "free"                   # 套餐类型
      phone: Optional[str] = None          # 手机号码
      referral_code: Optional[str] = None  # 推荐码

      # 密码复杂度验证
      @validator('password')
      def validate_password(cls, v):
          if len(v) < 8:
              raise ValueError('密码长度不能少于8位')
          if not re.search(r'[A-Za-z]', v):
              raise ValueError('密码必须包含字母')
          if not re.search(r'\d', v):
              raise ValueError('密码必须包含数字')
          return v
  ```
- **输出结果**: 外部设计的注册响应
  ```python
  class UserRegisterResponse(BaseModel):
      user_id: str                         # 用户唯一ID
      email: str                           # 邮箱地址
      status: str                          # 注册状态
      message: str                         # 状态消息
      email_verification_required: bool    # 是否需要邮箱验证
  ```
- **资源**: users表、邮件服务
- **逻辑**: 验证邮箱唯一性，检查密码复杂度，创建用户记录，发送验证邮件，记录注册安全日志，返回用户基本信息和验证状态

### API2: 用户登录 (对接外部设计接口)
- **URL**: `POST /api/auth/login`
- **输入参数**: 外部设计的登录请求
  ```python
  class UserLoginRequest(BaseModel):
      username: str                        # 邮箱或用户名
      password: str                        # 密码
      remember_me: bool = False            # 是否记住登录
      device_info: Optional[Dict[str, Any]] = None  # 设备信息
  ```
- **输出结果**: 外部设计的LoginResponse
  ```python
  class LoginResponse(BaseModel):
      access_token: str                    # JWT访问令牌
      refresh_token: str                   # 刷新令牌
      token_type: str = "bearer"           # 令牌类型
      expires_in: int                      # 过期时间(秒)
      user_info: UserInfo                  # 用户信息

  class UserInfo(BaseModel):
      user_id: str
      email: str
      plan: str                           # free/standard/professional/enterprise
      permissions: List[str]               # 权限列表
      created_at: datetime
  ```
- **资源**: users表、user_sessions表、Redis缓存
- **逻辑**: 验证用户凭据，检查账户状态和锁定情况，生成JWT令牌，创建会话记录，更新登录统计，返回令牌和用户权限信息

### API3: 用户信息获取 (需要认证)
- **URL**: `GET /api/auth/profile`
- **输入参数**: JWT Bearer令牌认证
  ```python
  Headers: {
      "Authorization": "Bearer <access_token>"
  }
  ```
- **输出结果**: 完整用户信息
  ```python
  class UserProfileResponse(BaseModel):
      user_id: str
      email: str
      username: Optional[str]
      full_name: Optional[str]
      avatar_url: Optional[str]
      plan: str
      status: str
      email_verified: bool
      phone_verified: bool
      preferences: Dict[str, Any]
      permissions: List[str]
      quota_usage: Dict[str, Any]        # 当前配额使用情况
      created_at: datetime
      last_login_at: Optional[datetime]
  ```
- **资源**: users表、权限系统、配额统计
- **逻辑**: 验证JWT令牌有效性，获取用户基本信息，计算当前权限列表，统计配额使用情况，返回完整的用户档案信息

### API4: 令牌刷新
- **URL**: `POST /api/auth/refresh`
- **输入参数**: 刷新令牌请求
  ```python
  class TokenRefreshRequest(BaseModel):
      refresh_token: str                   # 刷新令牌
  ```
- **输出结果**: 新的令牌对
  ```python
  class TokenRefreshResponse(BaseModel):
      access_token: str                    # 新的访问令牌
      refresh_token: str                   # 新的刷新令牌
      expires_in: int                      # 过期时间
  ```
- **资源**: user_sessions表、JWT服务
- **逻辑**: 验证刷新令牌有效性，检查会话状态，生成新的令牌对，更新会话记录，撤销旧令牌，返回新的认证凭据

### API5: 权限检查 (内部服务调用)
- **URL**: `POST /api/auth/check-permission`
- **输入参数**: 权限检查请求
  ```python
  class PermissionCheckRequest(BaseModel):
      user_id: str                         # 用户ID
      resource: str                        # 资源类型
      action: str                          # 操作类型
      context: Optional[Dict[str, Any]] = None  # 上下文信息
  ```
- **输出结果**: 权限检查结果
  ```python
  class PermissionCheckResponse(BaseModel):
      allowed: bool                        # 是否允许
      remaining_quota: Optional[int]       # 剩余配额
      rate_limit_reset: Optional[datetime] # 频率限制重置时间
      reason: Optional[str]                # 拒绝原因
  ```
- **资源**: 权限系统、配额管理、Redis限流
- **逻辑**: 检查用户套餐权限，验证配额限制，检查频率限制，记录使用情况，返回权限检查结果和配额状态

---

## 🔧 核心服务实现

### 1. AuthService (认证服务)
- **文件**: `app/services/auth_service.py`
- **功能**: 用户认证和令牌管理
- **输入**: 用户凭据和认证请求
- **输出**: JWT令牌和认证状态
- **资源**: 密码验证、JWT生成、会话管理
- **逻辑**: 验证用户身份，生成安全令牌，管理登录会话，处理登录失败和账户锁定，维护认证状态缓存

### 2. UserService (用户管理服务)
- **文件**: `app/services/user_service.py`
- **功能**: 用户生命周期管理
- **输入**: 用户信息和操作请求
- **输出**: 用户数据和操作结果
- **逻辑**: 处理用户注册、信息更新、状态变更，管理用户偏好设置，处理邮箱和手机号码验证，维护用户档案完整性

### 3. PermissionService (权限管理服务)
- **文件**: `app/services/permission_service.py`
- **功能**: 权限控制和配额管理
- **输入**: 权限检查请求和配额查询
- **输出**: 权限决策和配额状态
- **逻辑**: 实现基于角色的权限控制，管理用户配额和使用统计，处理权限升级和降级，提供细粒度的权限检查

### 4. SessionService (会话管理服务)
- **文件**: `app/services/session_service.py`
- **功能**: 用户会话生命周期管理
- **输入**: 会话令牌和操作请求
- **输出**: 会话状态和管理结果
- **逻辑**: 创建和维护用户会话，处理多设备登录，管理会话过期和清理，提供会话安全监控和异常检测

### 5. SecurityService (安全防护服务)
- **文件**: `app/services/security_service.py`
- **功能**: 安全防护和威胁检测
- **输入**: 请求信息和安全事件
- **输出**: 安全决策和防护措施
- **逻辑**: 实现防暴力破解保护，检测异常登录行为，管理IP黑白名单，记录和分析安全日志，提供实时威胁响应

---

## 🛡️ 安全防护机制

### 密码安全策略
```python
# 密码复杂度要求
PASSWORD_POLICY = {
    'min_length': 8,
    'require_uppercase': True,
    'require_lowercase': True,
    'require_digits': True,
    'require_special_chars': False,
    'forbidden_passwords': ['12345678', 'password', 'qwerty']
}

# 密码加密配置
BCRYPT_ROUNDS = 12                      # bcrypt加密轮数
PASSWORD_PEPPER = os.getenv('PASSWORD_PEPPER')  # 密码胡椒值
```

### 登录安全防护
```python
# 账户锁定策略
LOCKOUT_POLICY = {
    'max_attempts': 5,                  # 最大失败次数
    'lockout_duration': 1800,           # 锁定时间(秒)
    'progressive_lockout': True,        # 渐进式锁定
    'ip_based_lockout': True           # 基于IP的锁定
}

# 限流配置
RATE_LIMIT_CONFIG = {
    'login_attempts': '5/minute',       # 登录频率限制
    'api_requests': '100/minute',       # API请求限制
    'password_reset': '3/hour'          # 密码重置限制
}
```

---

## ⚡ 性能优化策略

### 令牌管理优化
- **JWT缓存**: Redis缓存活跃令牌，避免重复解析
- **令牌池化**: 预生成令牌池，减少生成延迟
- **异步验证**: 异步执行令牌验证，提高响应速度
- **分层验证**: 本地验证 + 远程确认的分层策略

### 数据库优化
- **连接池**: 数据库连接池管理，提高并发性能
- **索引优化**: 关键查询字段建立复合索引
- **分区策略**: 按时间分区存储日志数据
- **缓存策略**: 用户信息和权限信息缓存30分钟

---

## 🔒 环境配置

### 环境变量 (.env)
```bash
# 服务配置
AUTH_SERVICE_PORT=8004
DEBUG=false

# 数据库配置
DATABASE_URL=postgresql://user:pass@localhost:5432/prism2_auth
REDIS_URL=redis://localhost:6379/4

# JWT配置
JWT_SECRET_KEY=your-super-secret-jwt-key
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# 密码安全配置
PASSWORD_PEPPER=your-secret-pepper
BCRYPT_ROUNDS=12
PASSWORD_MIN_LENGTH=8

# 限流配置
MAX_LOGIN_ATTEMPTS=5
ACCOUNT_LOCKOUT_DURATION=1800
RATE_LIMIT_REDIS_URL=redis://localhost:6379/5

# 邮件服务配置
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_VERIFICATION_EXPIRE_HOURS=24

# 安全配置
CORS_ORIGINS=["http://localhost:3000"]
ALLOWED_HOSTS=["localhost", "127.0.0.1"]
TRUST_PROXY_HEADERS=true

# 监控配置
SENTRY_DSN=
LOG_LEVEL=INFO
SECURITY_LOG_RETENTION_DAYS=90
```

### 依赖配置 (requirements.txt)
```txt
fastapi==0.104.1
uvicorn==0.24.0
sqlalchemy==2.0.23
alembic==1.12.1
psycopg2-binary==2.9.7
redis==5.0.1
pydantic==2.5.0
pydantic[email]==2.5.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.6
slowapi==0.1.9
cryptography==41.0.7
email-validator==2.1.0
```

---

## 📊 监控和审计

### 关键安全指标
- **登录成功率**: 成功登录 / 总登录尝试
- **账户锁定率**: 被锁定账户数 / 活跃账户数
- **异常登录**: 异地登录、异常时间登录检测
- **令牌泄露**: 异常令牌使用模式检测

### 审计日志类型
```python
AUDIT_EVENT_TYPES = {
    'user.register': '用户注册',
    'user.login': '用户登录',
    'user.logout': '用户登出',
    'user.password_change': '密码修改',
    'user.email_verify': '邮箱验证',
    'user.account_lock': '账户锁定',
    'permission.check': '权限检查',
    'session.create': '会话创建',
    'session.revoke': '会话撤销',
    'security.suspicious_activity': '可疑活动'
}
```

---

*文档更新时间: 2025-09-16*
*严格遵循外部设计规范，确保接口一致性*