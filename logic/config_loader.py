import yaml
import os

class ConfigLoader:
    def __init__(self, config_path="domain_rules.yaml"):
        self.config_path = config_path
        self.rules = self._load_config()

    def _load_config(self):
        # Try multiple possible locations for the config file
        possible_paths = [
            self.config_path,  # Current directory
            os.path.join(os.path.dirname(os.path.dirname(__file__)), self.config_path),  # Project root from logic/
            os.path.join(os.path.dirname(__file__), '..', self.config_path),  # Alternative path
            os.path.join('/var/task', self.config_path),  # Vercel serverless path
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                self.config_path = path
                break
        else:
            raise FileNotFoundError(f"Config file not found. Tried: {possible_paths}")

        with open(self.config_path, 'r') as f:
            return yaml.safe_load(f)

    def get_platform(self, platform_id):
        # Normalize platform_id to lowercase
        pid = platform_id.lower()
        if pid in ['attractwell', 'aw']:
            return self.rules['platforms']['attractwell']
        if pid in ['getoiling', 'get oiling', 'go']:
            return self.rules['platforms']['getoiling']
        raise ValueError(f"Unknown platform: {platform_id}")

    def get_email_rules(self):
        return self.rules['email_rules']

    def get_decision_rules(self):
        return self.rules['decision_rules']
    
    def get_delegate_access_rules(self):
        return self.rules['delegate_access']

    def get_delegate_access_link(self, registrar_key):
        return self.rules['delegate_access_links'].get(registrar_key)

    def get_warning(self, warning_key):
        return self.rules['warnings'].get(warning_key)
