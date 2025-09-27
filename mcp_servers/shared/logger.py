#!/usr/bin/env python3
"""
Shared logging configuration for 4MCP architecture
"""

import sys
import os
from loguru import logger
from typing import Optional
from config import config

def setup_logger(
    service_name: str,
    log_level: Optional[str] = None,
    log_file: Optional[str] = None
) -> None:
    """
    Setup structured logging for MCP services

    Args:
        service_name: Name of the MCP service (e.g., 'realtime_data_mcp')
        log_level: Override default log level
        log_file: Optional log file path
    """

    # Remove default logger
    logger.remove()

    # Determine log level
    level = log_level or config.log_level

    # Console logging format
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{extra[service]}</cyan> | "
        "<level>{message}</level>"
    )

    # Add console handler
    logger.add(
        sys.stdout,
        format=console_format,
        level=level,
        colorize=True
    )

    # Add file handler if specified
    if log_file:
        file_format = (
            "{time:YYYY-MM-DD HH:mm:ss} | "
            "{level: <8} | "
            "{extra[service]} | "
            "{message}"
        )

        logger.add(
            log_file,
            format=file_format,
            level=level,
            rotation="10 MB",
            retention="7 days",
            compression="zip"
        )

    # Bind service name to all log messages
    logger.configure(extra={"service": service_name})

def get_logger(service_name: str) -> "logger":
    """
    Get a logger instance for a specific service

    Args:
        service_name: Name of the MCP service

    Returns:
        Configured logger instance
    """
    # Setup logger if not already configured
    if not logger._core.handlers:
        setup_logger(service_name)

    return logger.bind(service=service_name)

# MCP Service specific loggers
def get_realtime_data_logger():
    """Get logger for realtime data MCP service"""
    return get_logger("RealTime-MCP")

def get_structured_data_logger():
    """Get logger for structured data MCP service"""
    return get_logger("Structured-MCP")

def get_rag_logger():
    """Get logger for RAG MCP service"""
    return get_logger("RAG-MCP")

def get_coordination_logger():
    """Get logger for coordination MCP service"""
    return get_logger("Coordination-MCP")

def get_claude_integration_logger():
    """Get logger for Claude integration service"""
    return get_logger("Claude-Integration")

# Error handling utilities
def log_exception(logger_instance, exc_info=True, message="An error occurred"):
    """
    Log exceptions with full stack trace

    Args:
        logger_instance: Logger to use
        exc_info: Include exception info
        message: Custom error message
    """
    if exc_info:
        logger_instance.exception(message)
    else:
        logger_instance.error(message)

def log_mcp_call(logger_instance, tool_name: str, args: dict, result: dict = None, error: str = None):
    """
    Log MCP tool calls with structured information

    Args:
        logger_instance: Logger to use
        tool_name: Name of the MCP tool being called
        args: Arguments passed to the tool
        result: Result returned by the tool (optional)
        error: Error message if call failed (optional)
    """

    if error:
        logger_instance.error(
            f"MCP Tool Call Failed | Tool: {tool_name} | Args: {args} | Error: {error}"
        )
    elif result:
        logger_instance.info(
            f"MCP Tool Call Success | Tool: {tool_name} | Args: {args} | Result: {len(str(result))} chars"
        )
    else:
        logger_instance.info(
            f"MCP Tool Call Started | Tool: {tool_name} | Args: {args}"
        )