# config.py
import os
import yaml
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from pathlib import Path


class NCBIConfig(BaseModel):
    """NCBI-specific configuration"""
    api_key: Optional[str] = Field(default=None)
    pmc_base_url: str = Field(default="https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi")
    pubtator_base_url: str = Field(default="https://www.ncbi.nlm.nih.gov/research/pubtator3-api/publications/export/pubtator")
    request_timeout: int = Field(default=30)
    retry_attempts: int = Field(default=3)
    retry_delay: int = Field(default=1)


class StorageConfig(BaseModel):
    """Storage configuration"""
    backend: str = Field(default="duckdb")
    db_path: str = Field(default="data/figurex.db")
    cache_enabled: bool = Field(default=True)
    cache_ttl: int = Field(default=86400)  # 24 hours in seconds
    auto_update_schema: bool = Field(default=True)


class ProcessingConfig(BaseModel):
    """Processing configuration"""
    max_entities_per_figure: int = Field(default=50)
    min_entity_confidence: float = Field(default=0.5)
    entity_types: list = Field(default=["Gene", "Disease", "Chemical", "Species", "Mutation"])
    caption_cleanup_enabled: bool = Field(default=True)
    parallel_processing: bool = Field(default=False)
    batch_size: int = Field(default=10)


class OutputConfig(BaseModel):
    """Output configuration"""
    formats: list = Field(default=["json", "csv"])
    max_entities_in_csv: int = Field(default=5)
    output_dir: str = Field(default="data/output")
    include_summary: bool = Field(default=True)
    pretty_print_json: bool = Field(default=True)
    csv_delimiter: str = Field(default=",")


class LoggingConfig(BaseModel):
    """Logging configuration"""
    level: str = Field(default="INFO")
    file_path: Optional[str] = Field(default="logs/figurex.log")
    format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    rotate_logs: bool = Field(default=True)
    max_log_size: int = Field(default=10485760)  # 10MB
    backup_count: int = Field(default=5)


class Config(BaseModel):
    """Main configuration class"""
    ncbi: NCBIConfig = Field(default_factory=NCBIConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)

    @classmethod
    def from_yaml(cls, yaml_path: str) -> 'Config':
        """Load configuration from YAML file"""
        if not os.path.exists(yaml_path):
            return cls()

        with open(yaml_path, 'r') as f:
            try:
                config_dict = yaml.safe_load(f)
                return cls(**config_dict)
            except Exception as e:
                print(f"Error loading config from {yaml_path}: {e}")
                return cls()

    def update_from_env(self) -> None:
        """Update configuration from environment variables"""
        env_mapping = {
            'NCBI_API_KEY': ('ncbi', 'api_key'),
            'LOG_LEVEL': ('logging', 'level'),
            'DB_PATH': ('storage', 'db_path'),
            'OUTPUT_DIR': ('output', 'output_dir'),
            'BATCH_SIZE': ('processing', 'batch_size'),
        }

        for env_var, (section, key) in env_mapping.items():
            if env_var in os.environ:
                value = os.environ[env_var]
                # Convert string to appropriate type based on the field's type
                field_type = type(getattr(getattr(self, section), key))
                if field_type == bool:
                    value = value.lower() in ('true', '1', 'yes')
                elif field_type == int:
                    value = int(value)
                elif field_type == float:
                    value = float(value)
                setattr(getattr(self, section), key, value)


# Global configuration instance
_config_instance = None


def get_config(config_path: str = "settings.yaml", reload: bool = False) -> Config:
    """
    Get the global configuration instance.
    
    Args:
        config_path: Path to the YAML configuration file
        reload: Whether to force reload the configuration
    
    Returns:
        Config: The configuration instance
    """
    global _config_instance
    if _config_instance is None or reload:
        _config_instance = Config.from_yaml(config_path)
        _config_instance.update_from_env()
        
        # Ensure required directories exist
        os.makedirs(os.path.dirname(_config_instance.storage.db_path), exist_ok=True)
        os.makedirs(_config_instance.output.output_dir, exist_ok=True)
        if _config_instance.logging.file_path:
            os.makedirs(os.path.dirname(_config_instance.logging.file_path), exist_ok=True)

    return _config_instance