"""
Configuration Settings for Mainframe Copilot
Manages application configuration from environment and config files
"""

import os
import yaml
import json
from typing import Dict, Any, Optional
from pathlib import Path
from pydantic import BaseModel, Field, validator
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class MainframeConfig(BaseModel):
    """Mainframe connection configuration"""
    host: str = Field(default="localhost", description="Mainframe host address")
    port: int = Field(default=3270, description="3270 port")
    codepage: str = Field(default="cp037", description="EBCDIC codepage")
    timeout: int = Field(default=30, description="Connection timeout in seconds")
    screen_size: tuple = Field(default=(24, 80), description="Screen dimensions (rows, cols)")


class CredentialsConfig(BaseModel):
    """TSO credentials configuration"""
    username: Optional[str] = Field(default=None, description="TSO username")
    password: Optional[str] = Field(default=None, description="TSO password")
    procedure: str = Field(default="LOGONPROC", description="Logon procedure")
    account: Optional[str] = Field(default=None, description="Account information")

    @validator('username', 'password')
    def load_from_env(cls, v, field):
        """Load from environment if not set"""
        if v is None:
            env_key = f"TSO_{field.name.upper()}"
            return os.getenv(env_key)
        return v


class AIConfig(BaseModel):
    """AI/LLM configuration"""
    provider: str = Field(default="anthropic", description="LLM provider (anthropic/openai)")
    model: str = Field(default="claude-3-sonnet-20240229", description="Model name")
    api_key: Optional[str] = Field(default=None, description="API key")
    max_tokens: int = Field(default=2000, description="Maximum response tokens")
    temperature: float = Field(default=0.7, description="Response temperature")

    @validator('api_key')
    def load_api_key(cls, v, values):
        """Load API key from environment"""
        if v is None:
            provider = values.get('provider', 'anthropic')
            if provider == 'anthropic':
                return os.getenv('ANTHROPIC_API_KEY')
            elif provider == 'openai':
                return os.getenv('OPENAI_API_KEY')
        return v


class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: str = Field(default="INFO", description="Log level")
    file: Optional[str] = Field(default="mainframe_copilot.log", description="Log file path")
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    console: bool = Field(default=True, description="Enable console logging")


class Settings(BaseModel):
    """Application settings"""
    mainframe: MainframeConfig = Field(default_factory=MainframeConfig)
    credentials: CredentialsConfig = Field(default_factory=CredentialsConfig)
    ai: AIConfig = Field(default_factory=AIConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @classmethod
    def load(cls, config_file: Optional[str] = None) -> "Settings":
        """
        Load settings from file and environment

        Args:
            config_file: Path to configuration file

        Returns:
            Settings: Loaded settings
        """
        settings_dict = {}

        # Load from config file if provided
        if config_file:
            config_path = Path(config_file)
            if config_path.exists():
                with open(config_path, 'r') as f:
                    if config_path.suffix == '.yaml' or config_path.suffix == '.yml':
                        settings_dict = yaml.safe_load(f)
                    elif config_path.suffix == '.json':
                        settings_dict = json.load(f)

        # Override with environment variables
        settings_dict = cls._merge_env_vars(settings_dict)

        return cls(**settings_dict)

    @staticmethod
    def _merge_env_vars(settings_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge environment variables into settings

        Args:
            settings_dict: Existing settings

        Returns:
            Dict[str, Any]: Merged settings
        """
        # Check for mainframe settings
        if os.getenv('MAINFRAME_HOST'):
            settings_dict.setdefault('mainframe', {})['host'] = os.getenv('MAINFRAME_HOST')
        if os.getenv('MAINFRAME_PORT'):
            settings_dict.setdefault('mainframe', {})['port'] = int(os.getenv('MAINFRAME_PORT'))

        # Check for credentials
        if os.getenv('TSO_USERNAME'):
            settings_dict.setdefault('credentials', {})['username'] = os.getenv('TSO_USERNAME')
        if os.getenv('TSO_PASSWORD'):
            settings_dict.setdefault('credentials', {})['password'] = os.getenv('TSO_PASSWORD')

        # Check for AI settings
        if os.getenv('AI_PROVIDER'):
            settings_dict.setdefault('ai', {})['provider'] = os.getenv('AI_PROVIDER')
        if os.getenv('AI_MODEL'):
            settings_dict.setdefault('ai', {})['model'] = os.getenv('AI_MODEL')

        return settings_dict

    def save(self, config_file: str):
        """
        Save settings to file

        Args:
            config_file: Path to save configuration
        """
        config_path = Path(config_file)
        settings_dict = self.dict(exclude_none=True)

        # Don't save sensitive information
        if 'credentials' in settings_dict:
            if 'password' in settings_dict['credentials']:
                settings_dict['credentials']['password'] = '***REDACTED***'
        if 'ai' in settings_dict:
            if 'api_key' in settings_dict['ai']:
                settings_dict['ai']['api_key'] = '***REDACTED***'

        with open(config_path, 'w') as f:
            if config_path.suffix == '.yaml' or config_path.suffix == '.yml':
                yaml.safe_dump(settings_dict, f, default_flow_style=False)
            elif config_path.suffix == '.json':
                json.dump(settings_dict, f, indent=2)


# Default configuration instance
default_settings = Settings()


def get_settings(config_file: Optional[str] = None) -> Settings:
    """
    Get application settings

    Args:
        config_file: Optional config file path

    Returns:
        Settings: Application settings
    """
    # Check for default config files
    if not config_file:
        for filename in ['config.yaml', 'config.yml', 'config.json', '.mainframe_copilot']:
            if Path(filename).exists():
                config_file = filename
                break

    return Settings.load(config_file)