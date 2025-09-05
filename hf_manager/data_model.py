import json
import os

class DataModel:
    def __init__(self, config_file="hf_config.json"):
        self.config_file = config_file
        self.data = {
            "tags": {},
            "schemes": {},
            "settings": {
                "root_download_dir": "./downloads"
            }
        }
        self.load()

    def load(self, file_path=None):
        path = file_path if file_path else self.config_file
        if os.path.exists(path):
            with open(path, 'r') as f:
                self.data = json.load(f)
        else:
            # If a specific file_path is given and doesn't exist, it's an error.
            # If the default config doesn't exist, we just start fresh.
            if file_path:
                return False
        return True


    def save(self, file_path=None):
        path = file_path if file_path else self.config_file
        with open(path, 'w') as f:
            json.dump(self.data, f, indent=4)

    def get_tags(self):
        return self.data.get("tags", {})

    def get_schemes(self):
        return self.data.get("schemes", {})
