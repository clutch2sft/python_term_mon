import json
import os

class ConfigLoader:
    _instance = None  # Class attribute to store the singleton instance

    def __new__(cls, filepath='config.json'):
        """ Override the __new__ method to ensure only one instance exists. """
        if cls._instance is None:
            cls._instance = super(ConfigLoader, cls).__new__(cls)
            cls._instance.filepath = filepath
            cls._instance.config = cls._instance.load_config()
        return cls._instance

    def load_config(self):
        """ Load the JSON config file and clean it. """
        try:
            with open(self.filepath, 'r') as file:
                config = json.load(file)
            # Clean out any comments from the configuration
            self.remove_comments(config)
            return config
        except FileNotFoundError:
            raise Exception(f"The configuration file {self.filepath} was not found.")
        except json.JSONDecodeError:
            raise Exception("Error decoding the configuration file. Ensure it is valid JSON.")

    def remove_comments(self, config):
        """ Recursively remove __comments__ keys from the configuration dictionary. """
        if isinstance(config, dict):
            config.pop('__comments__', None)
            for key, value in list(config.items()):
                config[key] = self.remove_comments(value)
        elif isinstance(config, list):
            return [self.remove_comments(item) for item in config]
        return config

    def get_devices(self):
        """ Retrieve the list of devices from the configuration. """
        return self.config.get('devices', [])

    def get_configuration(self):
        """ Retrieve the general configuration. """
        return self.config.get('configuration', {})
