"""
LobbyShift - Configuration Management
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Optional
import yaml


CONFIG_FILE = Path("/etc/lobbyshift/config.yaml")

# Default CoD matchmaking IP ranges
DEFAULT_ALLOWED_IPS = ["185.34.0.0/16"]


@dataclass
class Config:
    """Application configuration"""
    
    # Network
    interface: str = "eth0"
    server_ip: str = "192.168.1.1"
    
    # CoD IPs to route through VPN
    allowed_ips: List[str] = field(default_factory=lambda: DEFAULT_ALLOWED_IPS.copy())
    
    # Web interface
    web_port: int = 8080
    web_host: str = "0.0.0.0"
    
    # Auto-start
    autostart: bool = False
    autostart_config: str = ""
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "/var/log/lobbyshift/lobbyshift.log"


def load_config() -> Config:
    """Load configuration from file"""
    config = Config()
    
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = yaml.safe_load(f) or {}
            
            # Update config with file values
            for key, value in data.items():
                if hasattr(config, key):
                    setattr(config, key, value)
        except Exception as e:
            print(f"Warning: Could not load config file: {e}")
    
    # Auto-detect server IP if not set
    if config.server_ip == "192.168.1.1":
        try:
            import socket
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            config.server_ip = s.getsockname()[0]
            s.close()
        except:
            pass
    
    return config


def save_config(config: Config) -> None:
    """Save configuration to file"""
    data = {
        "interface": config.interface,
        "server_ip": config.server_ip,
        "allowed_ips": config.allowed_ips,
        "web_port": config.web_port,
        "web_host": config.web_host,
        "autostart": config.autostart,
        "autostart_config": config.autostart_config,
        "log_level": config.log_level,
        "log_file": config.log_file,
    }
    
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    with open(CONFIG_FILE, 'w') as f:
        yaml.dump(data, f, default_flow_style=False)
