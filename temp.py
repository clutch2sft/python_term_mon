import logging

# Global logger setup for console
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[logging.StreamHandler()])

def setup_device_logger(ip_address):
    """Set up a logger for each device with a unique file."""
    device_logger = logging.getLogger(f"device_{ip_address}")
    device_logger.setLevel(logging.DEBUG)  # Capture all logs for the device
    device_logger.propagate = False  # Stop logs from propagating to the root logger

    # File handler for device-specific logs
    file_handler = logging.FileHandler(f'debug_{ip_address}.log')
    file_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)

    device_logger.addHandler(file_handler)
    return device_logger

# Usage within a function
def connect_and_monitor(device):
    ip = device['ip']
    device_logger = setup_device_logger(ip)
    device_logger.debug("Device-specific debug message")  # Only to device's log file
    device_logger.info("Device-specific info message")    # Only to device's log file
    logging.info("General info message")                  # To console (and any configured global file handlers)

# Example device setup
device_info = {'ip': '192.168.1.100'}
connect_and_monitor(device_info)
