#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
批处理系统配置管理器
"""
import os
import yaml
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class BatchConfig:
    """批处理配置管理类"""

    def __init__(self, config_dir: Optional[str] = None):
        self.config_dir = Path(config_dir) if config_dir else Path(__file__).parent
        self._config = {}
        self._load_configs()

    def _load_configs(self):
        """加载所有配置文件"""
        try:
            # 加载主配置
            batch_config_path = self.config_dir / "batch_config.yaml"
            if batch_config_path.exists():
                with open(batch_config_path, 'r', encoding='utf-8') as f:
                    self._config['batch'] = yaml.safe_load(f)

            # 加载调度配置
            schedule_config_path = self.config_dir / "schedules.yaml"
            if schedule_config_path.exists():
                with open(schedule_config_path, 'r', encoding='utf-8') as f:
                    self._config['schedules'] = yaml.safe_load(f)

            # 环境变量覆盖
            self._apply_env_overrides()

            logger.info("批处理配置加载成功")

        except Exception as e:
            logger.error(f"配置加载失败: {e}")
            raise

    def _apply_env_overrides(self):
        """应用环境变量覆盖"""
        env_mappings = {
            'DATABASE_URL': ['batch', 'data_sources', 'postgresql', 'url'],
            'REDIS_URL': ['batch', 'data_sources', 'redis', 'url'],
            'CHROMADB_URL': ['batch', 'data_sources', 'chromadb', 'url'],
            'BATCH_LOG_LEVEL': ['batch', 'monitoring', 'log_level'],
            'BATCH_MAX_CONCURRENT': ['batch', 'batch_settings', 'max_concurrent_jobs'],
        }

        for env_var, config_path in env_mappings.items():
            env_value = os.getenv(env_var)
            if env_value:
                self._set_nested_config(config_path, env_value)

    def _set_nested_config(self, path: list, value):
        """设置嵌套配置值"""
        config = self._config
        for key in path[:-1]:
            if key not in config:
                config[key] = {}
            config = config[key]
        config[path[-1]] = value

    def get(self, key_path: str, default: Any = None) -> Any:
        """
        获取配置值
        Args:
            key_path: 配置路径，用.分隔，如 'batch.batch_settings.max_concurrent_jobs'
            default: 默认值
        """
        keys = key_path.split('.')
        config = self._config

        try:
            for key in keys:
                config = config[key]
            return config
        except (KeyError, TypeError):
            return default

    def set(self, key_path: str, value: Any):
        """
        设置配置值
        Args:
            key_path: 配置路径
            value: 配置值
        """
        keys = key_path.split('.')
        self._set_nested_config(keys, value)

    @property
    def database_config(self) -> Dict[str, Any]:
        """获取数据库配置"""
        pg_config = self.get('batch.data_sources.postgresql', {})

        # 如果有完整的URL，解析它
        if 'url' in pg_config:
            return {'url': pg_config['url']}

        # 否则使用单独的配置项
        return {
            'host': pg_config.get('host', 'localhost'),
            'port': pg_config.get('port', 5432),
            'database': pg_config.get('database', 'prism2'),
            'user': pg_config.get('user', 'prism2'),
            'password': pg_config.get('password', 'prism2_secure_password')
        }

    @property
    def redis_config(self) -> Dict[str, Any]:
        """获取Redis配置"""
        redis_config = self.get('batch.data_sources.redis', {})

        if 'url' in redis_config:
            return {'url': redis_config['url']}

        return {
            'host': redis_config.get('host', 'localhost'),
            'port': redis_config.get('port', 6379),
            'db': redis_config.get('db', 1)
        }

    @property
    def chromadb_config(self) -> Dict[str, Any]:
        """获取ChromaDB配置"""
        chroma_config = self.get('batch.data_sources.chromadb', {})

        if 'url' in chroma_config:
            return {'url': chroma_config['url']}

        return {
            'host': chroma_config.get('host', 'localhost'),
            'port': chroma_config.get('port', 8000),
            'collection_prefix': chroma_config.get('collection_prefix', 'prism2_batch')
        }

    @property
    def batch_settings(self) -> Dict[str, Any]:
        """获取批处理设置"""
        return self.get('batch.batch_settings', {})

    @property
    def rag_settings(self) -> Dict[str, Any]:
        """获取RAG设置"""
        return self.get('batch.rag_settings', {})

    @property
    def schedule_config(self) -> Dict[str, Any]:
        """获取调度配置"""
        return self.get('schedules', {})

    @property
    def monitoring_config(self) -> Dict[str, Any]:
        """获取监控配置"""
        return self.get('batch.monitoring', {})

    @property
    def stock_pools(self) -> Dict[str, Any]:
        """获取股票池配置"""
        return self.get('batch.stock_pools', {})

    def reload(self):
        """重新加载配置"""
        self._config = {}
        self._load_configs()
        logger.info("配置重新加载完成")

    def to_dict(self) -> Dict[str, Any]:
        """返回完整配置字典"""
        return self._config.copy()

# 全局配置实例
config = BatchConfig()