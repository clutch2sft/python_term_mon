import json, re, time, logging
from getpass import getpass
from netmiko import ConnectHandler
from concurrent.futures import ThreadPoolExecutor

# Create a custom logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)  # Set minimum level for logger

# Create handlers
console_handler = logging.StreamHandler()
file_handler = logging.FileHandler('debug.log')

# Set logging level for each handler
console_handler.setLevel(logging.INFO)  # Adjust as needed
file_handler.setLevel(logging.DEBUG)    # Adjust as needed

# Create formatters and add it to handlers
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)

# Add handlers to the logger
logger.addHandler(console_handler)
logger.addHandler(file_handler)

# Global flag for running threads
running = True

def log_to_both(message, level=logging.INFO):
    """Log to both console and file."""
    if level == logging.DEBUG:
        logger.debug(message)
    elif level == logging.INFO:
        logger.info(message)
    elif level == logging.WARNING:
        logger.warning(message)
    elif level == logging.ERROR:
        logger.error(message)
    elif level == logging.CRITICAL:
        logger.critical(message)

def log_to_file_only(message, level=logging.INFO):
    """Log to file only."""
    # Temporarily disable console handler
    console_handler.setLevel(logging.CRITICAL)
    if level == logging.DEBUG:
        logger.debug(message)
    elif level == logging.INFO:
        logger.info(message)
    elif level == logging.WARNING:
        logger.warning(message)
    elif level == logging.ERROR:
        logger.error(message)
    elif level == logging.CRITICAL:
        logger.critical(message)
    # Re-enable console handler
    console_handler.setLevel(logging.INFO)


def connect_and_monitor(device):
    global running
    try:
        if 'password' not in device or device['password'] == "":
            device['password'] = getpass(f"Enter password for {device['ip']}: ")
        if 'secret' not in device or device['secret'] == "":
            device['secret'] = getpass(f"Enter enable password for {device['ip']}: ")

        with ConnectHandler(**device) as net_connect:
            net_connect.enable()
            output = net_connect.send_command('terminal monitor')
            log_to_both(f"Connected to {device['ip']} - {output}")
            output = net_connect.send_command('debug wgb uplink event')
            log_to_both(f"Debug set on {device['ip']} - {output}")
            while running:
                output = net_connect.read_channel()
                lines = output.split('\n')  # Split output into individual lines
                for line in lines:
                    if line.strip():  # Check if line is not empty or whitespace
                        if "parent_rssi:" in line:
                            log_to_file_only(f"Unfiltered output from {device['ip']}:\n{line}")
                        else:
                            log_to_both(f"Filtered output from {device['ip']}:\n{line}")
                output = ""
    except KeyboardInterrupt:
        log_to_both(f"Stopping monitoring on {device['ip']} due to KeyboardInterrupt.")
    except Exception as e:
        log_to_both(f"An error occurred with {device['ip']}: {e}")
    finally:
        if 'net_connect' in locals():
            net_connect.send_command('u all')

def main():
    global running
    try:
        with open('devices.json', 'r') as file:
            devices = json.load(file)
        
        executor = ThreadPoolExecutor(max_workers=len(devices))
        futures = [executor.submit(connect_and_monitor, device) for device in devices]

        for future in futures:
            try:
                future.result()
            except Exception as e:
                logging.error(f"A thread raised an exception: {e}")

    except KeyboardInterrupt:
        log_to_both("Received keyboard interrupt, shutting down threads.")
        running = False
    finally:
        executor.shutdown(wait=True)
        log_to_both("All threads have been cleanly shutdown.")

if __name__ == "__main__":
    main()


if __name__ == "__main__":
    main()
