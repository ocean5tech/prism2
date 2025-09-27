#!/usr/bin/env python3
"""
Shared configuration management for 4MCP architecture
"""

import os
from dataclasses import dataclass
from typing import Dict, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

@dataclass
class DatabaseConfig:
    """Database connection configuration"""
    postgresql_host: str = "localhost"
    postgresql_port: int = 5432
    postgresql_db: str = "prism2_db"
    postgresql_user: str = "prism2_user"
    postgresql_password: str = ""

    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None

    chromadb_host: str = "localhost"
    chromadb_port: int = 8003

@dataclass
class MCPServerConfig:
    """MCP server configuration"""
    realtime_data_port: int = 8006
    structured_data_port: int = 8007
    rag_mcp_port: int = 8008
    coordination_mcp_port: int = 8009
    claude_integration_port: int = 9000

    # Timeouts and retries
    request_timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0

@dataclass
class ExternalAPIConfig:
    """External API configuration"""
    enhanced_dashboard_url: str = "http://localhost:8081"
    rag_service_url: str = "http://localhost:8003"
    akshare_timeout: int = 10

    # Claude API configuration
    anthropic_api_key: str = ""
    claude_model: str = "claude-3-5-sonnet-20241022"

@dataclass
class Prism2Config:
    """Complete Prism2 configuration"""
    database: DatabaseConfig
    mcp_servers: MCPServerConfig
    external_apis: ExternalAPIConfig

    # System settings
    environment: str = "development"
    log_level: str = "INFO"
    debug_mode: bool = True

def load_config() -> Prism2Config:
    """Load configuration from environment variables"""

    database_config = DatabaseConfig(
        postgresql_host=os.getenv("POSTGRESQL_HOST", "localhost"),
        postgresql_port=int(os.getenv("POSTGRESQL_PORT", "5432")),
        postgresql_db=os.getenv("POSTGRESQL_DB", "prism2_db"),
        postgresql_user=os.getenv("POSTGRESQL_USER", "prism2_user"),
        postgresql_password=os.getenv("POSTGRESQL_PASSWORD", ""),

        redis_host=os.getenv("REDIS_HOST", "localhost"),
        redis_port=int(os.getenv("REDIS_PORT", "6379")),
        redis_db=int(os.getenv("REDIS_DB", "0")),
        redis_password=os.getenv("REDIS_PASSWORD"),

        chromadb_host=os.getenv("CHROMADB_HOST", "localhost"),
        chromadb_port=int(os.getenv("CHROMADB_PORT", "8003"))
    )

    mcp_server_config = MCPServerConfig(
        realtime_data_port=int(os.getenv("REALTIME_DATA_PORT", "8006")),
        structured_data_port=int(os.getenv("STRUCTURED_DATA_PORT", "8007")),
        rag_mcp_port=int(os.getenv("RAG_MCP_PORT", "8008")),
        coordination_mcp_port=int(os.getenv("COORDINATION_MCP_PORT", "8009")),
        claude_integration_port=int(os.getenv("CLAUDE_INTEGRATION_PORT", "9000")),

        request_timeout=int(os.getenv("REQUEST_TIMEOUT", "30")),
        max_retries=int(os.getenv("MAX_RETRIES", "3")),
        retry_delay=float(os.getenv("RETRY_DELAY", "1.0"))
    )

    external_api_config = ExternalAPIConfig(
        enhanced_dashboard_url=os.getenv("ENHANCED_DASHBOARD_URL", "http://localhost:8081"),
        rag_service_url=os.getenv("RAG_SERVICE_URL", "http://localhost:8003"),
        akshare_timeout=int(os.getenv("AKSHARE_TIMEOUT", "10")),

        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
        claude_model=os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022")
    )

    return Prism2Config(
        database=database_config,
        mcp_servers=mcp_server_config,
        external_apis=external_api_config,

        environment=os.getenv("ENVIRONMENT", "development"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        debug_mode=os.getenv("DEBUG_MODE", "true").lower() == "true"
    )

# Global configuration instance
config = load_config()