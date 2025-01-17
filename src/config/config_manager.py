import yaml
from pathlib import Path
from typing import Dict, Any

class ConfigManager:
    def __init__(self):
        self.config_dir = Path(__file__).parent.parent.parent / 'config'
        self.configs: Dict[str, Any] = {}
        
    def load_config(self, config_name: str) -> Dict[str, Any]:
        if config_name not in self.configs:
            config_path = self.config_dir / f"{config_name}_config.yaml"
            with open(config_path) as f:
                self.configs[config_name] = yaml.safe_load(f)
        return self.configs[config_name]
        
    def get_scraper_config(self) -> Dict[str, Any]:
        return self.load_config('scraper')
        
    def get_monitoring_config(self) -> Dict[str, Any]:
        return self.load_config('monitoring') 