import requests
import json
from loguru import logger


class APIUsage:
    def __init__(self, config_path="./configs/configs.json"):
        self.url = None
        self.headers1_save_data = None
        self.headers1_save_data = None
        self.load_config(config_path)

    def load_config(self, config_path):
        """Load configuration from JSON file."""
        try:
            with open(config_path, 'r') as config_file:
                my_config = json.load(config_file)
        except IOError:
            logger.error("Specify the correct config path.")
            return

        self.url = my_config['api']
        self.headers1_save_data = my_config['headers1_save_data']
        self.headers2_save_data = my_config['headers2_save_data']

    def post_request(self, data:json):
        headers = {
            "x-clientid": self.headers1_save_data,
            "Content-Type": self.headers2_save_data
        }
        response = requests.post(self.url, headers=headers, json=data)
        return response.json()