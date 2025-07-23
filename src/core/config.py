"""
Configuration management for miszen project.
Abstracts all configuration details to avoid hardcoding.
"""
import os
from typing import Dict, Any, Optional
from pathlib import Path
from dataclasses import dataclass, field
import json


@dataclass
class MCPConfig:
    """MCP connection configuration"""
    host: str = field(default_factory=lambda: os.getenv('MCP_HOST', 'localhost'))
    port: int = field(default_factory=lambda: int(os.getenv('MCP_PORT', '8765')))
    timeout: float = field(default_factory=lambda: float(os.getenv('MCP_TIMEOUT', '30.0')))
    retry_count: int = field(default_factory=lambda: int(os.getenv('MCP_RETRY_COUNT', '3')))
    retry_delay: float = field(default_factory=lambda: float(os.getenv('MCP_RETRY_DELAY', '1.0')))


@dataclass
class ZenMCPConfig:
    """Zen-MCP specific configuration"""
    command_timeout: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        # Load command-specific timeouts from environment or config file
        timeout_config = os.getenv('ZEN_MCP_TIMEOUTS', '{}')
        try:
            self.command_timeout = json.loads(timeout_config)
        except json.JSONDecodeError:
            # Default timeouts for each command
            self.command_timeout = {
                'chat': 60.0,
                'thinkdeep': 300.0,
                'challenge': 120.0,
                'planner': 180.0,
                'consensus': 240.0,
                'codereview': 180.0,
                'precommit': 120.0,
                'debug': 180.0,
                'analyze': 150.0,
                'refactor': 180.0,
                'tracer': 120.0,
                'testgen': 180.0,
                'secaudit': 240.0,
                'docgen': 150.0,
                'listmodels': 30.0,
                'version': 10.0
            }


@dataclass
class MISConfig:
    """MIS integration configuration"""
    api_base_url: str = field(default_factory=lambda: os.getenv('MIS_API_URL', 'http://localhost:8080'))
    event_queue_name: str = field(default_factory=lambda: os.getenv('MIS_EVENT_QUEUE', 'mis_events'))
    knowledge_graph_endpoint: str = field(default_factory=lambda: os.getenv('MIS_KG_ENDPOINT', '/api/kg'))
    memory_bank_endpoint: str = field(default_factory=lambda: os.getenv('MIS_MB_ENDPOINT', '/api/memory'))


@dataclass
class EventMappingConfig:
    """Event mapping configuration - loaded from external config file"""
    mappings: Dict[str, list] = field(default_factory=dict)
    
    def __post_init__(self):
        config_path = Path(os.getenv('EVENT_MAPPING_CONFIG', 'config/event_mappings.json'))
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                self.mappings = json.load(f)
        else:
            # Default mappings if config file not found
            self.mappings = {
                "file_created": {
                    "conditions": {"extensions": [".py", ".js", ".ts"]},
                    "commands": ["analyze", "docgen"]
                },
                "error_detected": {
                    "conditions": {"severity": ["error", "critical"]},
                    "commands": ["debug", "tracer"]
                },
                "code_changed": {
                    "conditions": {"min_lines": 10},
                    "commands": ["codereview", "refactor"]
                },
                "test_failed": {
                    "conditions": {},
                    "commands": ["testgen", "debug"]
                }
            }


class Config:
    """Main configuration class that aggregates all configs"""
    
    def __init__(self):
        self.mcp = MCPConfig()
        self.zen_mcp = ZenMCPConfig()
        self.mis = MISConfig()
        self.event_mapping = EventMappingConfig()
        
        # Load any additional config from environment
        self.debug = os.getenv('DEBUG', 'false').lower() == 'true'
        self.log_level = os.getenv('LOG_LEVEL', 'INFO')
        self.data_dir = Path(os.getenv('DATA_DIR', './data'))
        self.cache_dir = Path(os.getenv('CACHE_DIR', './cache'))
        
        # Ensure directories exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def get_zen_command_timeout(self, command: str) -> float:
        """Get timeout for specific zen-MCP command"""
        return self.zen_mcp.command_timeout.get(command, 60.0)
    
    def get_event_commands(self, event_type: str) -> list:
        """Get zen-MCP commands for specific event type"""
        mapping = self.event_mapping.mappings.get(event_type, {})
        return mapping.get('commands', [])
    
    def get_event_conditions(self, event_type: str) -> Dict[str, Any]:
        """Get conditions for event mapping"""
        mapping = self.event_mapping.mappings.get(event_type, {})
        return mapping.get('conditions', {})


# Singleton instance
config = Config()