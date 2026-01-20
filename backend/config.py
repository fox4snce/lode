"""
Application configuration management.

Stores settings like server port in a simple JSON config file.
"""

import json
from pathlib import Path
from typing import Optional
from backend.db import get_data_dir


CONFIG_FILE = "lode_config.json"
DEFAULT_PORT = 8000


def get_config_path() -> Path:
    """Get path to config file in data directory."""
    return get_data_dir() / CONFIG_FILE


def load_config() -> dict:
    """Load configuration from file, or return defaults."""
    config_path = get_config_path()
    if config_path.exists():
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            # If config file is corrupted, return defaults
            pass
    return {}


def save_config(config: dict) -> None:
    """Save configuration to file."""
    config_path = get_config_path()
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2)


def get_port() -> int:
    """Get configured server port, or default."""
    config = load_config()
    return config.get('server_port', DEFAULT_PORT)


def set_port(port: int) -> None:
    """Set server port in config."""
    config = load_config()
    config['server_port'] = port
    save_config(config)


def get_config() -> dict:
    """Get full configuration."""
    return load_config()
