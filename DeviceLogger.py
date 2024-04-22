import logging
import os
from datetime import datetime
from threading import Lock

class DeviceLogger:
    _loggers = {}
    _lock = Lock()

    @staticmethod
    def get_logger(ip_address, output_dir="./logs", console_level=None, format = None):
        """
        Returns a logger for the given IP address. If the logger does not already exist,
        it creates a new one with the specified settings, including an optional console logger.
        This method ensures that there is only one logger per device IP in a thread-safe manner.
        """
        with DeviceLogger._lock:
            if ip_address not in DeviceLogger._loggers:
                DeviceLogger._setup_device_logger(ip_address, output_dir, console_level, format)
        return DeviceLogger._loggers[ip_address]

    @staticmethod
    def _setup_device_logger(ip_address, output_dir, console_level, format):
        """
        Set up a logger for each device with a unique file including a timestamp,
        and optionally, a console handler based on the console_level.
        """
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{output_dir}/device_monitor_debug_{ip_address}_{timestamp}.log"
        logger = logging.getLogger(f"device_{ip_address}")
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

        # File handler setup
        file_handler = logging.FileHandler(filename)
        if format is not None:
            formatter = logging.Formatter(format)
        else:
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

        # Optional console handler setup
        if console_level is not None:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(console_level)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)

        DeviceLogger._loggers[ip_address] = logger
