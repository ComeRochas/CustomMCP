"""Application configuration management."""

import os
from typing import Literal
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Application configuration with validation."""
    
    # Server settings
    HOST: str = os.getenv("HOST", "localhost")
    PORT: int = int(os.getenv("PORT", "8050"))
    
    # Transport configuration
    TRANSPORT: Literal["stdio", "sse", "streamable-http"] = os.getenv("TRANSPORT", "sse")
    
    # Client settings
    MODEL: str = os.getenv("MODEL", "qwen3:8b")
    
    # API settings
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    
    # Development settings
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def validate(cls) -> None:
        """Validate all configuration values."""
        errors = []
        
        if cls.TRANSPORT not in ["stdio", "sse", "streamable-http"]:
            errors.append(f"Invalid transport: {cls.TRANSPORT}")
        
        if not (1024 <= cls.PORT <= 65535):
            errors.append(f"Port must be between 1024-65535, got: {cls.PORT}")
        
        if cls.REQUEST_TIMEOUT <= 0:
            errors.append(f"Request timeout must be positive, got: {cls.REQUEST_TIMEOUT}")
        
        if not cls.MODEL.strip():
            errors.append("MODEL cannot be empty")
        
        if errors:
            raise ValueError("Configuration errors: " + "; ".join(errors))
    
    @classmethod
    def display_config(cls) -> str:
        """Return a safe string representation of configuration."""
        return f"""
CustomMCP Configuration:
  Host: {cls.HOST}
  Port: {cls.PORT}  
  Transport: {cls.TRANSPORT}
  Client model: {cls.MODEL}
  Debug: {cls.DEBUG}
  Log Level: {cls.LOG_LEVEL}
"""

config = Config()