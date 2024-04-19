from threading import Event
from concurrent.futures import ThreadPoolExecutor
from getpass import getpass
from netmiko import ConnectHandler

import json, time, logging

shutdown_event = Event()

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

def log_to_both(logger, message, level=logging.INFO):
    """Log to both the specific device logger and the console."""
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
    # Optionally log to global console at a different level or based on conditions
    logging.getLogger().info(message)  # This uses the root logger which has console handler


def connect_and_monitor(device):
    try:
        ip = device['ip']
        device_logger = setup_device_logger(ip)
        if 'password' not in device or device['password'] == "":
            device['password'] = getpass(f"Enter password for {device['ip']}: ")
        if 'secret' not in device or device['secret'] == "":
            device['secret'] = getpass(f"Enter enable password for {device['ip']}: ")

        with ConnectHandler(**device) as net_connect:
            net_connect.enable()
            output = net_connect.send_command('terminal monitor')
            logging.info(f"Connected to {device['ip']} - {output}")
            output = net_connect.send_command('debug wgb uplink event')
            logging.info(f"Debug set on {device['ip']} - {output}")

            # Monitoring loop
            while not shutdown_event.is_set():
                output = net_connect.read_channel()
                if output:
                    log_to_both(device_logger, f"Messages from {device['ip']}")
                    lines = output.split('\n')
                    for line in lines:
                        if line.strip():
                            if "[DOT11_UPLINK_CONNECTED]" in line:
                                log_to_both(device_logger, f"{line}\n")
                            elif "Aux roam switch radio role" in line:
                                log_to_both(device_logger, f"{line}\n")
                            elif "[DOT11_UPLINK_FT_AUTHENTICATING]" in line:
                                log_to_both(device_logger, f"{line}\n")
                            elif "target channel" in line:
                                log_to_both(device_logger, f"{line}\n")
                            elif "DOT11-UPLINK_ESTABLISHED" in line:
                                log_to_both(device_logger, f"{line}\n")
                            elif "Peer assoc event received from driver" in line:
                                device_logger.debug(f"{line}\n")
                                stats = net_connect.send_command('show wgb statistic roaming')
                                log_to_both(device_logger, f"This is probably not so useful because it was not designed for dual radio:")
                                log_to_both(device_logger, f"{stats}\n")
                            else:
                                device_logger.debug(device_logger, f"{line}\n")
                time.sleep(1)

    except Exception as e:
        log_to_both(f"An error occurred with {device['ip']}: {e}")
    finally:
        if 'net_connect' in locals():
            net_connect.send_command('u all')  # Cleanup command on shutdown

def main():
    try:
        with open('devices.json', 'r') as file:
            devices = json.load(file)
        
        executor = ThreadPoolExecutor(max_workers=len(devices))
        futures = [executor.submit(connect_and_monitor, device) for device in devices]

        try:
            for future in futures:
                future.result()
        except KeyboardInterrupt:
            logging.getLogger().info("Received keyboard interrupt, initiating shutdown.")
            shutdown_event.set()
            raise

    finally:
        executor.shutdown(wait=True)
        logging.getLogger().info("All threads have been cleanly shutdown.")

if __name__ == "__main__":
    main()