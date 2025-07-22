"""
Configuration management for CodeBased.
"""

import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings


@dataclass
class ParsingConfig:
    """Configuration for code parsing."""
    file_extensions: List[str] = field(default_factory=lambda: ['.py'])
    exclude_patterns: List[str] = field(default_factory=lambda: [
        '__pycache__',
        '*.pyc',
        '.git',
        'node_modules',
        '.env',
        'venv',
        'env'
    ])
    include_docstrings: bool = True
    max_file_size: int = 1024 * 1024  # 1MB
    follow_symlinks: bool = False


@dataclass
class DatabaseConfig:
    """Configuration for database operations."""
    path: str = ".codebased/data/graph.kuzu"
    query_timeout: int = 30  # seconds
    batch_size: int = 1000
    auto_backup: bool = True
    backup_retention_days: int = 7


@dataclass
class APIConfig:
    """Configuration for API server."""
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = False
    reload: bool = False
    cors_origins: List[str] = field(default_factory=lambda: ["*"])
    max_query_time: int = 30  # seconds
    enable_docs: bool = True


@dataclass
class WebConfig:
    """Configuration for web frontend."""
    static_path: str = ".codebased/web"
    template_path: str = ".codebased/web/templates"
    max_nodes: int = 1000
    max_edges: int = 5000
    default_layout: str = "force"


@dataclass
class CodeBasedConfig:
    """Main configuration class for CodeBased."""
    project_root: str = "."
    parsing: ParsingConfig = field(default_factory=ParsingConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    api: APIConfig = field(default_factory=APIConfig)
    web: WebConfig = field(default_factory=WebConfig)
    log_level: str = "INFO"
    
    @classmethod
    def find_config_file(cls, start_path: str = ".") -> Optional[Path]:
        """
        Find the .codebased.yml config file by walking up the directory tree.
        
        Args:
            start_path: Directory to start searching from
            
        Returns:
            Path to config file or None if not found
        """
        current_path = Path(start_path).resolve()
        
        while True:
            config_file = current_path / ".codebased.yml"
            if config_file.exists():
                return config_file
            
            # Check if we've reached the root
            parent = current_path.parent
            if parent == current_path:
                break
            current_path = parent
        
        return None
    
    @classmethod
    def load_from_project_root(cls, start_path: str = ".") -> 'CodeBasedConfig':
        """
        Load configuration by finding .codebased.yml from the current or parent directories.
        
        Args:
            start_path: Directory to start searching from
            
        Returns:
            CodeBasedConfig instance
        """
        config_file = cls.find_config_file(start_path)
        if config_file:
            return cls.from_file(str(config_file))
        else:
            # Return default config with current directory as project root
            config = cls()
            config.project_root = str(Path(start_path).resolve())
            return config
    
    @classmethod
    def from_file(cls, config_path: str) -> 'CodeBasedConfig':
        """
        Load configuration from YAML file.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            CodeBasedConfig instance
        """
        config_path = Path(config_path)
        
        if not config_path.exists():
            return cls()
        
        try:
            # Get the directory containing the config file to resolve relative paths
            config_dir = config_path.parent.resolve()
            
            with open(config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            
            # Create config with nested dataclasses
            config = cls()
            
            # Resolve project_root relative to config file location
            if 'project_root' in data:
                project_root = Path(data['project_root'])
                if not project_root.is_absolute():
                    project_root = (config_dir / project_root).resolve()
                config.project_root = str(project_root)
            else:
                # Default to the directory containing the config file
                config.project_root = str(config_dir)
            
            if 'log_level' in data:
                config.log_level = data['log_level']
            
            if 'parsing' in data:
                parsing_data = data['parsing']
                config.parsing = ParsingConfig(
                    file_extensions=parsing_data.get('file_extensions', config.parsing.file_extensions),
                    exclude_patterns=parsing_data.get('exclude_patterns', config.parsing.exclude_patterns),
                    include_docstrings=parsing_data.get('include_docstrings', config.parsing.include_docstrings),
                    max_file_size=parsing_data.get('max_file_size', config.parsing.max_file_size),
                    follow_symlinks=parsing_data.get('follow_symlinks', config.parsing.follow_symlinks)
                )
            
            if 'database' in data:
                db_data = data['database']
                
                # Resolve database path relative to project root
                db_path = db_data.get('path', config.database.path)
                if db_path and not Path(db_path).is_absolute():
                    db_path = str((Path(config.project_root) / db_path).resolve())
                
                config.database = DatabaseConfig(
                    path=db_path,
                    query_timeout=db_data.get('query_timeout', config.database.query_timeout),
                    batch_size=db_data.get('batch_size', config.database.batch_size),
                    auto_backup=db_data.get('auto_backup', config.database.auto_backup),
                    backup_retention_days=db_data.get('backup_retention_days', config.database.backup_retention_days)
                )
            
            if 'api' in data:
                api_data = data['api']
                config.api = APIConfig(
                    host=api_data.get('host', config.api.host),
                    port=api_data.get('port', config.api.port),
                    debug=api_data.get('debug', config.api.debug),
                    reload=api_data.get('reload', config.api.reload),
                    cors_origins=api_data.get('cors_origins', config.api.cors_origins),
                    max_query_time=api_data.get('max_query_time', config.api.max_query_time),
                    enable_docs=api_data.get('enable_docs', config.api.enable_docs)
                )
            
            if 'web' in data:
                web_data = data['web']
                
                # Resolve web paths relative to project root
                static_path = web_data.get('static_path', config.web.static_path)
                template_path = web_data.get('template_path', config.web.template_path)
                
                if static_path and not Path(static_path).is_absolute():
                    static_path = str((Path(config.project_root) / static_path).resolve())
                if template_path and not Path(template_path).is_absolute():
                    template_path = str((Path(config.project_root) / template_path).resolve())
                
                config.web = WebConfig(
                    static_path=static_path,
                    template_path=template_path,
                    max_nodes=web_data.get('max_nodes', config.web.max_nodes),
                    max_edges=web_data.get('max_edges', config.web.max_edges),
                    default_layout=web_data.get('default_layout', config.web.default_layout)
                )
            
            return config
            
        except Exception as e:
            raise ValueError(f"Failed to load configuration from {config_path}: {e}")
    
    def to_file(self, config_path: str) -> None:
        """
        Save configuration to YAML file.
        
        Args:
            config_path: Path to save configuration file
        """
        config_path = Path(config_path)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Convert dataclasses to dictionaries
        data = {
            'project_root': self.project_root,
            'log_level': self.log_level,
            'parsing': {
                'file_extensions': self.parsing.file_extensions,
                'exclude_patterns': self.parsing.exclude_patterns,
                'include_docstrings': self.parsing.include_docstrings,
                'max_file_size': self.parsing.max_file_size,
                'follow_symlinks': self.parsing.follow_symlinks
            },
            'database': {
                'path': self.database.path,
                'query_timeout': self.database.query_timeout,
                'batch_size': self.database.batch_size,
                'auto_backup': self.database.auto_backup,
                'backup_retention_days': self.database.backup_retention_days
            },
            'api': {
                'host': self.api.host,
                'port': self.api.port,
                'debug': self.api.debug,
                'reload': self.api.reload,
                'cors_origins': self.api.cors_origins,
                'max_query_time': self.api.max_query_time,
                'enable_docs': self.api.enable_docs
            },
            'web': {
                'static_path': self.web.static_path,
                'template_path': self.web.template_path,
                'max_nodes': self.web.max_nodes,
                'max_edges': self.web.max_edges,
                'default_layout': self.web.default_layout
            }
        }
        
        try:
            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, indent=2)
        except Exception as e:
            raise ValueError(f"Failed to save configuration to {config_path}: {e}")


class EnvironmentSettings(BaseSettings):
    """Environment-based settings that can override configuration."""
    
    codebased_project_root: Optional[str] = None
    codebased_log_level: Optional[str] = None
    codebased_api_host: Optional[str] = None
    codebased_api_port: Optional[int] = None
    codebased_api_debug: Optional[bool] = None
    codebased_database_path: Optional[str] = None
    
    class Config:
        env_prefix = "CODEBASED_"
        case_sensitive = False


def load_config(config_path: str = ".codebased.yml") -> CodeBasedConfig:
    """
    Load configuration from file and apply environment overrides.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        CodeBasedConfig instance with environment overrides applied
    """
    # Load base configuration from file
    config = CodeBasedConfig.from_file(config_path)
    
    # Apply environment variable overrides
    env_settings = EnvironmentSettings()
    
    if env_settings.codebased_project_root:
        config.project_root = env_settings.codebased_project_root
    
    if env_settings.codebased_log_level:
        config.log_level = env_settings.codebased_log_level
    
    if env_settings.codebased_api_host:
        config.api.host = env_settings.codebased_api_host
    
    if env_settings.codebased_api_port:
        config.api.port = env_settings.codebased_api_port
    
    if env_settings.codebased_api_debug is not None:
        config.api.debug = env_settings.codebased_api_debug
    
    if env_settings.codebased_database_path:
        config.database.path = env_settings.codebased_database_path
    
    return config


def create_default_config(config_path: str = ".codebased.yml") -> CodeBasedConfig:
    """
    Create and save a default configuration file.
    
    Args:
        config_path: Path where to save the configuration file
        
    Returns:
        Default CodeBasedConfig instance
    """
    config = CodeBasedConfig()
    config.to_file(config_path)
    return config


# Global configuration instance
_config: Optional[CodeBasedConfig] = None


def get_config(config_path: str = ".codebased.yml") -> CodeBasedConfig:
    """
    Get or create the global configuration instance.
    
    Args:
        config_path: Configuration file path (only used on first call)
        
    Returns:
        CodeBasedConfig instance
    """
    global _config
    
    if _config is None:
        _config = load_config(config_path)
    
    return _config