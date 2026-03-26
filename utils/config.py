import json
import os
from pathlib import Path
from typing import Dict, Any

class ConfigLoader:
    def __init__(self, config_dir: str = "config"):
        self.config_dir = Path(config_dir)
        self._api_config = None
        self._game_config = None
    
    def load_api_config(self) -> Dict[str, Any]:
        if self._api_config is None:
            config_path = self.config_dir / "api_config.json"
            if not config_path.exists():
                # Fallback to example config
                config_path = self.config_dir / "api_config.json.example"
            if config_path.exists():
                with open(config_path, 'r', encoding='utf-8') as f:
                    self._api_config = json.load(f)
            else:
                self._api_config = {"api": {"base_url": "", "api_key": "", "model": ""}}
        return self._api_config
    
    def load_game_config(self) -> Dict[str, Any]:
        if self._game_config is None:
            config_path = self.config_dir / "game_config.json"
            with open(config_path, 'r', encoding='utf-8') as f:
                self._game_config = json.load(f)
        return self._game_config
    
    def get_api_config(self) -> Dict[str, Any]:
        return self.load_api_config().get('api', {})
    
    def get_game_config(self) -> Dict[str, Any]:
        return self.load_game_config()
    
    def get_ai_config(self) -> Dict[str, Any]:
        return self.load_game_config().get('ai', {})
    
    def get_world_config(self) -> Dict[str, Any]:
        return self.load_game_config().get('world', {})
    
    def get_ui_config(self) -> Dict[str, Any]:
        return self.load_game_config().get('ui', {})

config = ConfigLoader()