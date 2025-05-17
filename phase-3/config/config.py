# config.py
import os
import tomli
from pydantic import BaseModel, Field
from typing import Optional


class APIConfig(BaseModel):
    api_key: str = Field(default="changeme123")
    ncbi_api_key: Optional[str] = Field(default=None)


class StorageConfig(BaseModel):
    backend: str = Field(default="duckdb")
    db_path: str = Field(default="data/figurex.db")


class IngestionConfig(BaseModel):
    watch_folder: str = Field(default="data/watch")
    batch_size: int = Field(default=10)
    source: str = Field(default="PMC")


class GeneralConfig(BaseModel):
    data_source: str = Field(default="PMC")
    log_level: str = Field(default="INFO")
    output_dir: str = Field(default="data/output")


class Config(BaseModel):
    general: GeneralConfig = Field(default_factory=GeneralConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)
    api: APIConfig = Field(default_factory=APIConfig)
    ingestion: IngestionConfig = Field(default_factory=IngestionConfig)


def load_config(config_path: str = "settings.toml") -> Config:
    """
    Load configuration from TOML file with environment variable overrides.
    """
    if not os.path.exists(config_path):
        return Config()

    with open(config_path, "rb") as f:
        try:
            config_dict = tomli.load(f)

            # Check for environment variable overrides
            if os.environ.get("NCBI_API_KEY"):
                if "api" not in config_dict:
                    config_dict["api"] = {}
                config_dict["api"]["ncbi_api_key"] = os.environ.get("NCBI_API_KEY")

            # Similar overrides can be added for other settings

            return Config(**config_dict)
        except Exception as e:
            print(f"Error loading config: {e}")
            return Config()


# Singleton-like config instance
_config_instance = None


def get_config() -> Config:
    """
    Get the global configuration instance.
    """
    global _config_instance
    if _config_instance is None:
        _config_instance = load_config()
    return _config_instance